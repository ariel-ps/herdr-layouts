#!/usr/bin/env python3
"""Open Neovim or Herdr Board once in a matching idle, single-pane tab."""
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time


def herdr(*args):
    output = subprocess.check_output([os.environ.get('HERDR_BIN_PATH') or 'herdr', *args], text=True)
    response = json.loads(output) if output.strip() else {}
    if 'error' in response:
        raise ValueError(response['error'])
    return response.get('result', {})


def main():
    event = json.loads(os.environ.get('HERDR_PLUGIN_EVENT_JSON', '{}'))
    event = event.get('data', event)
    tab = event.get('tab', event)
    name = (tab.get('label') or '').casefold()
    if name not in ('code', 'board'):
        return
    tab_id = tab.get('tab_id', '')
    if not re.fullmatch(r'[A-Za-z0-9_:-]+', tab_id):
        raise ValueError('Named tab event has no valid tab ID')
    token = f'herdr-{name}-tab'
    state = Path(os.environ['HERDR_PLUGIN_STATE_DIR'])
    state.mkdir(parents=True, exist_ok=True)
    # ponytail: serialize these rare events; per-tab locks if contention matters.
    with (state / 'named-tabs.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (herdr('tab', 'get', tab_id)['tab'].get('label') or '').casefold() != name:
            return
        panes = [p for p in herdr('pane', 'list')['panes'] if p['tab_id'] == tab_id]
        if len(panes) != 1 or token in panes[0].get('tokens', {}):
            return
        pane = panes[0]
        if pane.get('agent'):
            return
        deadline = time.monotonic() + (8 if event.get('type') == 'tab_created' else 0)
        while True:
            info = herdr('pane', 'process-info', '--pane', pane['pane_id'])['process_info']
            processes = info.get('foreground_processes', [])
            if (len(processes) == 1 and processes[0].get('pid') == info.get('shell_pid')
                    and Path(processes[0].get('name', '')).name.lstrip('-') in ('bash', 'zsh', 'sh', 'fish', 'dash')):
                break
            if time.monotonic() >= deadline:
                return
            time.sleep(0.1)
        if (herdr('tab', 'get', tab_id)['tab'].get('label') or '').casefold() != name:
            return
        if name == 'code':
            executable = shutil.which('nvim')
            if not executable:
                raise ValueError('Install Neovim to automatically open code tabs')
            command = f'{shlex.quote(executable)} .'
        else:
            plugin = next((p for p in herdr('plugin', 'list', '--json')['plugins']
                           if p['plugin_id'] == 'herdr-board' and p.get('enabled')), None)
            if not plugin:
                raise ValueError('Install and enable the herdr-board plugin to open board tabs')
            executable = Path(plugin['plugin_root']) / 'target/release/board'
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError('Herdr Board executable is missing; reinstall the herdr-board plugin')
            command = f'{shlex.quote(str(executable))} tui'
        herdr('pane', 'run', pane['pane_id'], command)
        herdr('pane', 'report-metadata', pane['pane_id'], '--source', token, '--token', f'{token}=started')



if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'herdr-layouts: {error}', file=sys.stderr)
        sys.exit(1)
