"""
autostart.py - Windows 注册表开机自启读写
Mac/Linux 下为空操作（stub）
"""

import sys

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "AudioStream"


def set_autostart(enabled: bool, exe_path: str = ""):
    if sys.platform != "win32":
        return
    import winreg
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE
    )
    try:
        if enabled and exe_path:
            winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, REG_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, REG_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
