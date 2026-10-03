"""Build, then run: sh scripts/build/install.sh && python3 tests/test_named_tabs.py."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def check():
    manifest = tomllib.loads((ROOT / 'herdr-plugin.toml').read_text())
    assert manifest['build'] == [{'command': ['sh', './scripts/build/install.sh']}]
    assert manifest['events'] == [
        {'on': event, 'command': ['./libexec/herdr-named-tab']}
        for event in ('tab.created', 'tab.renamed')]
    with tempfile.TemporaryDirectory(prefix="named tabs ' ") as temporary:
        root = Path(temporary).resolve()
        binary = root / 'relocated plugin/libexec/herdr-named-tab'
        binary.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'libexec/herdr-named-tab', binary)
        tools = root / 'tools with spaces'
        tools.mkdir()
        nvim = tools / 'nvim'
        nvim.write_text('#!/bin/sh\nexit 0\n')
        nvim.chmod(0o755)
        board = root / 'board plugin/target/release/board'
        board.parent.mkdir(parents=True)
        shutil.copy2(nvim, board)
        stub = tools / 'herdr'
        stub.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
from pathlib import Path
path = Path(os.environ['TEST_STATE'])
state = json.loads(path.read_text())
a = sys.argv[1:]
state['calls'].append(a)
case, name = state['case'], state['name']
result = {}
if case == 'api-error':
    print(json.dumps({'error': 'API failed'}))
    sys.exit(0)
if case == 'bad-response':
    print('not json')
    sys.exit(0)
if a[:2] == ['tab', 'get']:
    state['gets'] += 1
    away = case == 'renamed-away' or (case == 'renamed-during-startup' and state['gets'] > 1)
    result = {'tab': {'label': 'terminal' if away else name.title()}}
elif a[:2] == ['plugin', 'list']:
    result = {'plugins': [] if case == 'missing-plugin' else [{
        'plugin_id': 'herdr-board', 'enabled': case != 'disabled-plugin',
        'plugin_root': os.environ['TEST_BOARD_ROOT']}]}
elif a[:2] == ['pane', 'list']:
    pane = {'pane_id': 'w1:p1', 'tab_id': 'w1:t1', 'tokens': state['tokens']}
    if case == 'agent':
        pane['agent'] = 'codex'
    result = {'panes': [pane, {**pane, 'pane_id': 'w1:p2'}] if case == 'multiple' else [pane]}
elif a[:2] == ['pane', 'process-info']:
    state['probes'] += 1
    busy = case == 'busy' or (case in ('startup', 'renamed-during-startup') and state['probes'] == 1)
    result = {'process_info': {'shell_pid': 42, 'foreground_processes': [
        {'pid': 43 if busy else 42, 'name': 'sleep' if busy else '/bin/-zsh'}]}}
    if case == 'unknown-process':
        result = {'process_info': {'foreground_processes': [{'name': 'zsh'}]}}
elif a[:2] == ['pane', 'run']:
    if case == 'failed-run':
        path.write_text(json.dumps(state))
        print('launch failed', file=sys.stderr)
        sys.exit(7)
elif a[:2] == ['pane', 'report-metadata']:
    state['tokens'][f'herdr-{name}-tab'] = 'started'
else:
    sys.exit(2)
path.write_text(json.dumps(state))
# Successful pane mutations can return no output.
if a[:2] not in [['pane', 'run'], ['pane', 'report-metadata']]:
    print(json.dumps({'result': result}))
''')
        stub.chmod(0o755)
        for name in ('code', 'board'):
            cases = ['created', 'renamed', 'other', 'unnamed', 'busy', 'multiple', 'agent',
                     'startup', 'renamed-away', 'renamed-during-startup', 'failed-run',
                     'invalid-id', 'malformed-event', 'unknown-process', 'api-error',
                     'bad-response', 'concurrent']
            cases += ['missing-nvim'] if name == 'code' else ['missing-plugin', 'disabled-plugin', 'missing-binary']
            for case in cases:
                state_path = root / 'state.json'
                state_path.write_text(json.dumps({'case': case, 'name': name, 'tokens': {},
                                                  'calls': [], 'probes': 0, 'gets': 0}))
                tab = {'tab_id': 'w1:t1/invalid' if case == 'invalid-id' else 'w1:t1',
                       'label': 'terminal' if case == 'other' else None if case == 'unnamed' else name.upper()}
                created = case in ('created', 'startup', 'renamed-during-startup', 'concurrent')
                event = {'type': 'tab_created', 'tab': tab} if created else {'type': 'tab_renamed', **tab}
                env = {**os.environ, 'HERDR_PLUGIN_STATE_DIR': str(root / 'plugin state'),
                       'HERDR_BIN_PATH': str(stub), 'PATH': str(tools),
                       'TEST_STATE': str(state_path), 'TEST_BOARD_ROOT': str(board.parents[2]),
                       'HERDR_PLUGIN_EVENT_JSON': '{' if case == 'malformed-event' else json.dumps(
                           event if case == 'created' else {'data': event})}
                if case == 'missing-nvim':
                    nvim.chmod(0o644)
                if case == 'missing-binary':
                    board.unlink()
                failures = ('failed-run', 'missing-plugin', 'disabled-plugin', 'missing-binary',
                            'missing-nvim', 'invalid-id', 'malformed-event', 'api-error', 'bad-response')
                if case == 'concurrent':
                    processes = [subprocess.Popen([str(binary)], env=env, cwd=root,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
                    for process in processes:
                        _, error = process.communicate(timeout=15)
                        assert process.returncode == 0, error
                else:
                    for _ in range(2):
                        result = subprocess.run([str(binary)], env=env, cwd=root,
                                                capture_output=True, text=True, timeout=15)
                        assert (result.returncode != 0) == (case in failures), (case, result.stderr)
                        if case in failures:
                            assert 'herdr-layouts:' in result.stderr
                state = json.loads(state_path.read_text())
                launches = [a for a in state['calls'] if a[:2] == ['pane', 'run']]
                launched = case in ('created', 'renamed', 'startup', 'concurrent')
                expected_launches = 2 if case == 'failed-run' else int(launched)
                assert len(launches) == expected_launches, (name, case, state)
                if launched:
                    expected = f'{shlex.quote(str(nvim))} .' if name == 'code' else f'{shlex.quote(str(board))} tui'
                    assert launches[0][3] == expected, launches
                    assert state['tokens'] == {f'herdr-{name}-tab': 'started'}
                else:
                    assert not state['tokens'], state
                if case in ('other', 'unnamed', 'invalid-id', 'malformed-event'):
                    assert not state['calls'], state
                nvim.chmod(0o755)
            print(f'PASS: Rust {name} hook, startup, concurrency, busy-pane protection and errors')


if __name__ == '__main__':
    check()
