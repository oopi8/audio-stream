"""
tray.py - pystray 系统托盘 + 菜单 + 引擎生命周期管理
"""

import queue
import sys
import threading
from typing import Optional

import pystray

from config import AppConfig
from icon_assets import make_icon
from autostart import is_autostart_enabled, set_autostart

# 用于从 pystray 线程向主线程发送指令
_main_queue: queue.Queue = queue.Queue()

CMD_OPEN_SETTINGS = "open_settings"
CMD_EXIT = "exit"


class TrayApp:
    def __init__(self, config: AppConfig):
        self._config = config
        self._engine = None          # AudioServer 或 AudioClient 实例
        self._status = "stopped"
        self._status_lock = threading.Lock()

        self._icon = pystray.Icon(
            "AudioStream",
            icon=make_icon("stopped"),
            title="AudioStream",
            menu=self._build_menu(),
        )

    # ------------------------------------------------------------------ #
    #  公开接口                                                             #
    # ------------------------------------------------------------------ #

    def run(self):
        """启动托盘；pystray 在后台线程运行，主线程保留给 tkinter"""
        tray_thread = threading.Thread(target=self._icon.run, daemon=True)
        tray_thread.start()
        self._start_engine()
        self._main_loop()

    # ------------------------------------------------------------------ #
    #  引擎管理                                                             #
    # ------------------------------------------------------------------ #

    def _start_engine(self):
        self._stop_engine()
        cfg = self._config
        if cfg.mode == "server":
            from server import AudioServer
            self._engine = AudioServer(
                port=cfg.port,
                on_status_change=self._on_status_change,
            )
        else:
            from client import AudioClient
            self._engine = AudioClient(
                server_ip=cfg.server_ip,
                port=cfg.port,
                on_status_change=self._on_status_change,
            )
        self._engine.start()

    def _stop_engine(self):
        if self._engine is not None:
            self._engine.stop()
            self._engine = None

    def _on_status_change(self, status: str):
        with self._status_lock:
            self._status = status
        self._icon.icon = make_icon(status)
        mode_label = "服务端" if self._config.mode == "server" else "客户端"
        self._icon.title = f"AudioStream [{mode_label}] — {status}"
        self._icon.update_menu()

    # ------------------------------------------------------------------ #
    #  主线程循环（处理跨线程 tkinter 调用）                                  #
    # ------------------------------------------------------------------ #

    def _main_loop(self):
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # 隐藏根窗口

        def poll():
            try:
                while True:
                    cmd = _main_queue.get_nowait()
                    if cmd == CMD_OPEN_SETTINGS:
                        self._do_open_settings(root)
                    elif cmd == CMD_EXIT:
                        self._do_exit(root)
                        return
            except queue.Empty:
                pass
            root.after(100, poll)

        root.after(100, poll)
        root.mainloop()

    # ------------------------------------------------------------------ #
    #  设置对话框（在主线程执行）                                             #
    # ------------------------------------------------------------------ #

    def _do_open_settings(self, root):
        from settings import show_settings_dialog

        self._stop_engine()

        # 在已有 Tk 根窗口下打开 Toplevel
        top = _SettingsWindow(root, self._config, self._on_settings_saved)
        root.wait_window(top.window)

    def _on_settings_saved(self, new_config: AppConfig):
        self._config = new_config
        self._icon.update_menu()
        self._start_engine()

    def _do_exit(self, root):
        self._stop_engine()
        self._icon.stop()
        root.quit()

    # ------------------------------------------------------------------ #
    #  菜单构建                                                             #
    # ------------------------------------------------------------------ #

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda item: self._status_label(),
                action=None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda item: self._mode_label(),
                action=None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("设置…", self._menu_open_settings),
            pystray.MenuItem(
                "开机自启动",
                self._menu_toggle_autostart,
                checked=lambda item: is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._menu_exit),
        )

    def _status_label(self) -> str:
        labels = {
            "connected": "● 已连接",
            "connecting": "○ 连接中…",
            "stopped": "■ 已停止",
            "error": "✕ 错误",
        }
        with self._status_lock:
            return labels.get(self._status, self._status)

    def _mode_label(self) -> str:
        mode = "服务端" if self._config.mode == "server" else "客户端"
        return f"模式：{mode}  端口：{self._config.port}"

    # ------------------------------------------------------------------ #
    #  菜单回调（在 pystray 线程执行，只能向主线程发指令）                      #
    # ------------------------------------------------------------------ #

    def _menu_open_settings(self, icon, item):
        _main_queue.put(CMD_OPEN_SETTINGS)

    def _menu_toggle_autostart(self, icon, item):
        enabled = not is_autostart_enabled()
        set_autostart(enabled, sys.executable)
        self._config.autostart = enabled
        self._config.save()

    def _menu_exit(self, icon, item):
        _main_queue.put(CMD_EXIT)


# ------------------------------------------------------------------ #
#  内嵌设置窗口（Toplevel，避免 Tk() 多实例问题）                          #
# ------------------------------------------------------------------ #

class _SettingsWindow:
    def __init__(self, root, config: AppConfig, on_save):
        import tkinter as tk
        from tkinter import ttk, messagebox
        from autostart import is_autostart_enabled, set_autostart

        self.on_save = on_save
        self.result = None
        self.window = tk.Toplevel(root)
        self.window.title("AudioStream 设置")
        self.window.resizable(False, False)
        self.window.attributes("-topmost", True)

        mode_var = tk.StringVar(value=config.mode)
        ip_var = tk.StringVar(value=config.server_ip)
        port_var = tk.StringVar(value=str(config.port))
        autostart_var = tk.BooleanVar(value=is_autostart_enabled())

        frame = ttk.Frame(self.window, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="运行模式：").grid(row=0, column=0, sticky="w", pady=4)
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(mode_frame, text="服务端（台式机）", variable=mode_var, value="server",
                        command=lambda: _toggle()).pack(side="left")
        ttk.Radiobutton(mode_frame, text="客户端（笔记本）", variable=mode_var, value="client",
                        command=lambda: _toggle()).pack(side="left", padx=8)

        ttk.Label(frame, text="服务端 IP：").grid(row=1, column=0, sticky="w", pady=4)
        ip_entry = ttk.Entry(frame, textvariable=ip_var, width=20)
        ip_entry.grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="端口：").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=port_var, width=8).grid(row=2, column=1, sticky="w")

        ttk.Checkbutton(frame, text="开机自启动", variable=autostart_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=6
        )

        def _toggle():
            state = "disabled" if mode_var.get() == "server" else "normal"
            ip_entry.configure(state=state)

        _toggle()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(12, 0))

        def _save():
            try:
                port = int(port_var.get())
                assert 1 <= port <= 65535
            except (ValueError, AssertionError):
                messagebox.showerror("错误", "端口号必须是 1–65535 之间的整数", parent=self.window)
                return

            new_config = AppConfig(
                mode=mode_var.get(),
                server_ip=ip_var.get().strip(),
                port=port,
                autostart=autostart_var.get(),
                first_run=False,
            )
            new_config.save()
            set_autostart(autostart_var.get(), sys.executable)
            self.on_save(new_config)
            self.window.destroy()

        ttk.Button(btn_frame, text="保存", command=_save, width=10).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="取消", command=self.window.destroy, width=10).pack(side="left", padx=4)
