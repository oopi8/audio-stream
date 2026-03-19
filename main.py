"""
main.py - 入口：首次运行检测 + 启动系统托盘
"""

import sys

from config import AppConfig


def main():
    config = AppConfig.load()

    if config.first_run:
        from settings import show_settings_dialog
        result = show_settings_dialog(config, is_first_run=True)
        if result is None:
            sys.exit(0)
        config = result

    from tray import TrayApp
    TrayApp(config).run()


if __name__ == "__main__":
    main()
