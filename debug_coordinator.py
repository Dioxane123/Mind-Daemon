#!/usr/bin/env python3
"""Debug gesture environment coordinator"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mind_daemon.agent.gesture_environment_coordinator import GestureEnvironmentCoordinator

def main():
    print('Testing GestureEnvironmentCoordinator...')
    config = {
        'gesture_host': '172.20.10.2',
        'gesture_port': 8888,
        'MUSIC_DIR': 'music',
        'WINDOW_PY_PATH': 'src/mind_daemon/peripheral/window.py'
    }

    coordinator = GestureEnvironmentCoordinator(config)
    print('Coordinator created, testing start_monitoring...')

    try:
        result = coordinator.start_monitoring()
        print(f'Start monitoring result: {result}')

        print('Getting status...')
        status = coordinator.get_status()
        print(f'SSH connected: {status.get("ssh_connected", False)}')
        print(f'Is running: {status.get("is_running", False)}')
        print(f'SSH status: {status.get("ssh_status", {})}')

    except Exception as e:
        print(f'Error during testing: {e}')
        import traceback
        traceback.print_exc()
    finally:
        coordinator.stop_monitoring()
        coordinator.cleanup()

if __name__ == "__main__":
    main()