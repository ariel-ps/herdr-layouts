"""Run directly: python3 tests/test_plugin.py."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def check_runtime(plugin, home):
    tools = home / 'tools'
    tools.mkdir()
    state = home / 'state.json'
    calls = home / 'calls.jsonl'
    rpc = home / 'rpc.json'
    executable = tools / 'herdr'
    executable.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
state = json.loads(Path(os.environ['TEST_STATE']).read_text())
with open(os.environ['TEST_CALLS'], 'a') as log:
    log.write(json.dumps(a) + '\\n')
if a[:2] == ['pane', 'list']:
    result = {'panes': state['panes']}
elif a[:2] == ['pane', 'get']:
    result = {'pane': next(p for p in state['panes'] if p['pane_id'] == a[2])}
elif a[:2] == ['agent', 'list']:
    result = {'agents': []}
elif a[:2] == ['workspace', 'list']:
    result = {'workspaces': [{'label': 'fleet', 'workspace_id': 'w1'}]}
elif a[:2] == ['workspace', 'get']:
    result = {'workspace': {'active_tab_id': 'w1:t1'}}
elif a[:2] == ['tab', 'create']:
    result = {'tab': {'tab_id': 'w1:t1'}, 'root_pane': {'pane_id': 'w1:p1'}}
elif a[:2] == ['pane', 'split']:
    result = {'pane': {'pane_id': 'w1:p2'}}
elif a[:2] == ['agent', 'start']:
    sys.exit(7 if state.get('fail') else 0)
elif a[:2] in [['pane', 'rename'], ['pane', 'report-agent-session']]:
    result = {}
else:
    sys.exit(2)
print(json.dumps({'result': result}))
''')
    executable.chmod(0o755)
    env = {**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / 'config'),
           'PATH': str(tools) + ':' + os.environ['PATH'], 'TEST_STATE': str(state),
           'TEST_CALLS': str(calls), 'TEST_RPC': str(rpc), 'HERDR_AGENT_ARGS': ''}

    def invoke(*args):
        return subprocess.run(['zsh', '-fc', '''source "$1/shell.zsh"; shift
__herdr_layouts_ready() { return 0; }
__herdr_rpc() { cat "$TEST_RPC"; }
"$@"''', 'check', str(plugin), *args], env=env, text=True, capture_output=True)

    panes = [{'pane_id': f'w1:p{i}', 'tab_id': 'w1:t1', 'label': f'agent{i}',
              'cwd': '/same/project', 'agent': kind}
             for i, kind in [(1, 'claude'), (2, 'claude')]]
    state.write_text(json.dumps({'panes': panes}))
    layout = {'workspace_id': 'w1', 'tab_id': 'w1:t1', 'root': {'type': 'pane', 'label': 'agent1'}}
    rpc.write_text(json.dumps({'result': {'layout': layout, 'tab': {'tab_id': 'w1:t1'}}}))
    directory = home / 'config/herdr/layouts'
    directory.mkdir(parents=True)
    sidecar = directory / 'fleet.agents.json'
    sidecar.write_text('{"old": {"session": "stale"}}')
    result = invoke('herdr-layout-save', 'fleet')
    assert result.returncode == 0, result.stderr
    assert json.loads(sidecar.read_text()) == {}, 'Unidentified panes retained guessed sessions'
    panes[1]['agent'] = 'codex'
    for index, pane in enumerate(panes):
        pane['agent_session'] = {'value': f'session-{index}'}
    state.write_text(json.dumps({'panes': panes}))
    result = invoke('herdr-layout-save', 'fleet')
    assert result.returncode == 0, result.stderr
    saved = json.loads(sidecar.read_text())
    assert saved['agent1']['session'] == 'session-0' and saved['agent2']['session'] == 'session-1'
    assert 'fleet.agents' not in invoke('herdr-layout-list').stdout
    for command in ['herdr-layout-save', 'herdr-layout-load', 'herdr-layout-up']:
        for name in ['../escape', '/absolute', '.', 'a/b', 'a\nb', '-option']:
            assert invoke(command, name).returncode == 2, (command, name)
    outside = home / 'outside.json'
    outside.write_text('preserved')
    (directory / 'link.json').symlink_to(outside)
    assert invoke('herdr-layout-save', 'link').returncode == 2
    assert outside.read_text() == 'preserved'

    calls.write_text('')
    result = invoke('herdr-layout-up', 'fleet')
    assert result.returncode == 0, result.stderr
    starts = [a for a in map(json.loads, calls.read_text().splitlines()) if a[:2] == ['agent', 'start']]
    assert starts[0][-3:] == ['--', '--resume', 'session-0'], starts
    assert starts[1][-3:] == ['--', 'resume', 'session-1'], starts
    # Old sidecars contain heuristic guesses; never resume these automatically.
    sidecar.write_text(json.dumps({'agent1': {'kind': 'claude', 'session': 'guess', 'match': 'same prompt'}}))
    calls.write_text('')
    assert invoke('herdr-layout-up', 'fleet').returncode == 0
    starts = [a for a in map(json.loads, calls.read_text().splitlines()) if a[:2] == ['agent', 'start']]
    assert all('--resume' not in a and 'guess' not in a for a in starts), starts
    state.write_text(json.dumps({'panes': panes, 'fail': True}))
    assert invoke('herdr-layout-up', 'fleet').returncode == 1
    assert invoke('herdr-grid-agents', '2', 'claude', 'fleet').returncode == 1
    panes[1]['agent'] = 'claude'
    panes[1]['agent_session'] = panes[0]['agent_session']
    state.write_text(json.dumps({'panes': panes}))
    assert invoke('herdr-layout-save', 'fleet').returncode == 0
    assert json.loads(sidecar.read_text()) == {}, 'Duplicate sessions must not be assigned arbitrarily'

    # Labels are the sidecar keys: reject collisions before saving or launching,
    # including old layouts whose sidecars already lost one of the sessions.
    for pane in panes:
        pane['label'] = 'same'
    panes[1]['agent_session'] = {'value': 'different-session'}
    state.write_text(json.dumps({'panes': panes}))
    layout['root'] = {'type': 'split', 'children': [
        {'type': 'pane', 'label': 'same'}, {'type': 'pane', 'label': 'same'}]}
    rpc.write_text(json.dumps({'result': {'layout': layout}}))
    previous = (directory / 'fleet.json').read_bytes(), sidecar.read_bytes()
    result = invoke('herdr-layout-save', 'fleet')
    assert result.returncode == 1 and 'duplicate pane labels' in result.stderr, result
    assert previous == ((directory / 'fleet.json').read_bytes(), sidecar.read_bytes())
    # Even a label change between export and snapshot must not overwrite a session.
    assert invoke('__herdr_layout_snap_agents', 'fleet', 'w1:t1').returncode == 0
    assert json.loads(sidecar.read_text()) == {}
    (directory / 'fleet.json').write_text(json.dumps(layout))
    sidecar.write_text(json.dumps({'same': {'kind': 'claude', 'session': 'different-session', 'verified': True}}))
    calls.write_text('')
    result = invoke('herdr-layout-up', 'fleet')
    assert result.returncode == 1 and 'duplicate pane labels' in result.stderr, result
    assert not calls.read_text(), 'Ambiguous layouts must fail before touching Herdr'


def check():
    # A relocated standalone plugin must work without the old toolkit or siblings.
    with tempfile.TemporaryDirectory(prefix='plugin user ') as temporary:
        home = Path(temporary)
        plugin = home / 'plugin copy'
        shutil.copytree(ROOT, plugin, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        result = subprocess.run(
            ['zsh', '-fc', 'plugin=$1; source "$plugin/shell.zsh"; herdr-layout-list', 'check', str(plugin)],
            env={**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / 'config'),
                 'XDG_CACHE_HOME': str(home / 'cache')}, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        assert 'no saved layouts' in result.stdout
        check_runtime(plugin, home)

        # Verify bash forwards literal arguments, cwd, and failures to the implementation.
        commands = ["herdr-layout-save","herdr-layout-load","herdr-layout-up","herdr-layout-list","herdr-grid-agents"]
        (plugin / 'shell.zsh').write_text('\n'.join(
            name + '() { printf "%s\\n" "$PWD" "${HERDR_AGENT_ARGS:-}" "$@"; return 7; }'
            for name in commands))
        arguments = ['two words', '$(touch unexpected)', '', '--option']
        for command in commands:
            result = subprocess.run(
                ['bash', '--noprofile', '--norc', '-c',
                 'source "$1/shell.bash"; shift; HERDR_AGENT_ARGS="two flags"; "$@"',
                 'check', str(plugin), command, *arguments], cwd=home,
                env={**os.environ, 'HOME': str(home)}, text=True, capture_output=True)
            assert result.returncode == 7, result.stderr
            assert result.stdout.splitlines() == [str(home.resolve()), 'two flags', *arguments], result.stdout
        assert not (home / 'unexpected').exists()


if __name__ == '__main__':
    check()
