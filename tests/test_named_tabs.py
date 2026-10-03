"""Run directly: python3 tests/test_named_tabs.py."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('named_tabs', Path(__file__).resolve().parents[1] / 'hooks/open-named-tab.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def check(name):
    with tempfile.TemporaryDirectory() as state:
        board = Path(state) / 'plugin with spaces/target/release/board'
        board.parent.mkdir(parents=True)
        board.touch()
        board.chmod(0o755)
        cases = ['created', 'renamed', 'other', 'unnamed', 'busy', 'multiple', 'agent', 'startup', 'renamed-away', 'failed-run']
        if name == 'board':
            cases += ['missing-plugin', 'disabled-plugin', 'missing-binary']
        for case in cases:
            if case == 'missing-binary':
                board.unlink()
            pane = {'pane_id': 'w1:p1', 'tab_id': 'w1:t1', 'tokens': {}}
            if case == 'agent':
                pane['agent'] = 'codex'
            panes = [pane, {**pane, 'pane_id': 'w1:p2'}] if case == 'multiple' else [pane]
            calls = []
            probes = 0

            def herdr(*args):
                nonlocal probes
                calls.append(args)
                if args[:2] == ('tab', 'get'):
                    return {'tab': {'label': 'terminal' if case == 'renamed-away' else name.title()}}
                if args[:2] == ('plugin', 'list'):
                    plugins = [{'plugin_id': 'herdr-board', 'enabled': case != 'disabled-plugin', 'plugin_root': str(board.parents[2])}]
                    return {'plugins': [] if case == 'missing-plugin' else plugins}
                if args[:2] == ('pane', 'list'):
                    return {'panes': panes}
                if args[:2] == ('pane', 'process-info'):
                    probes += 1
                    busy = case == 'busy' or (case == 'startup' and probes == 1)
                    return {'process_info': {'shell_pid': 42, 'foreground_processes': [
                        {'pid': 43 if busy else 42, 'name': 'sleep' if busy else 'zsh'}]}}
                if args[:2] == ('pane', 'run'):
                    if case == 'failed-run':
                        raise ValueError('launch failed')
                    expected = "'/tools with spaces/nvim' ." if name == "code" else f"'{board}' tui"
                    assert args[3] == expected, args
                if args[:2] == ('pane', 'report-metadata'):
                    pane['tokens'][f'herdr-{name}-tab'] = 'started'
                return {}

            tab = {'tab_id': 'w1:t1', 'label': 'terminal' if case == 'other' else name.upper()}
            if case == 'unnamed':
                tab['label'] = None
            event = {'type': 'tab_created', 'tab': tab} if case in ('created', 'startup') else {'type': 'tab_renamed', **tab}
            env = {'HERDR_PLUGIN_EVENT_JSON': json.dumps({'data': event}), 'HERDR_PLUGIN_STATE_DIR': state}
            with patch.dict(os.environ, env), patch.object(hook, 'herdr', herdr), patch.object(hook.shutil, 'which', return_value='/tools with spaces/nvim'):
                if case in ('failed-run', 'missing-plugin', 'disabled-plugin', 'missing-binary'):
                    try:
                        hook.main()
                        assert False, 'launch failure was swallowed'
                    except ValueError:
                        assert not pane['tokens']
                        if case != 'failed-run':
                            assert not any(call[:2] == ('pane', 'run') for call in calls)
                    continue
                hook.main()
                hook.main()  # Repeated events must not type a second command.
            launches = [args for args in calls if args[:2] == ('pane', 'run')]
            assert len(launches) == int(case in ('created', 'renamed', 'startup')), (case, calls)
            if case in ('other', 'unnamed'):
                assert not calls
        print(f'PASS: {name} tabs, startup readiness, duplicate events and busy-pane protection')


if __name__ == '__main__':
    check('code')
    check('board')
