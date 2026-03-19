"""
settings.py - tkinter 设置对话框
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from config import AppConfig
from autostart import set_autostart, is_autostart_enabled


def show_settings_dialog(
    config: AppConfig,
    on_save: Optional[Callable[[AppConfig], None]] = None,
    is_first_run: bool = False,
) -> Optional[AppConfig]:
    """
    弹出设置对话框。
    返回保存后的 AppConfig，用户取消则返回 None（首次运行时会 sys.exit(0)）。
    """
    root = tk.Tk()
    root.title("AudioStream 设置")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    result: list[Optional[AppConfig]] = [None]

    # --- 变量 ---
    mode_var = tk.StringVar(value=config.mode)
    ip_var = tk.StringVar(value=config.server_ip)
    port_var = tk.StringVar(value=str(config.port))
    autostart_var = tk.BooleanVar(value=is_autostart_enabled())

    # --- 布局 ---
    frame = ttk.Frame(root, padding=16)
    frame.grid(sticky="nsew")

    ttk.Label(frame, text="运行模式：").grid(row=0, column=0, sticky="w", pady=4)
    mode_frame = ttk.Frame(frame)
    mode_frame.grid(row=0, column=1, sticky="w")
    ttk.Radiobutton(mode_frame, text="服务端（台式机）", variable=mode_var, value="server",
                    command=lambda: _toggle_ip()).pack(side="left")
    ttk.Radiobutton(mode_frame, text="客户端（笔记本）", variable=mode_var, value="client",
                    command=lambda: _toggle_ip()).pack(side="left", padx=8)

    ttk.Label(frame, text="服务端 IP：").grid(row=1, column=0, sticky="w", pady=4)
    ip_entry = ttk.Entry(frame, textvariable=ip_var, width=20)
    ip_entry.grid(row=1, column=1, sticky="w")

    ttk.Label(frame, text="端口：").grid(row=2, column=0, sticky="w", pady=4)
    ttk.Entry(frame, textvariable=port_var, width=8).grid(row=2, column=1, sticky="w")

    ttk.Checkbutton(frame, text="开机自启动", variable=autostart_var).grid(
        row=3, column=0, columnspan=2, sticky="w", pady=6
    )

    def _toggle_ip():
        state = "disabled" if mode_var.get() == "server" else "normal"
        ip_entry.configure(state=state)

    _toggle_ip()

    # --- 按钮 ---
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=(12, 0))

    def _save():
        try:
            port = int(port_var.get())
            assert 1 <= port <= 65535
        except (ValueError, AssertionError):
            messagebox.showerror("错误", "端口号必须是 1–65535 之间的整数", parent=root)
            return

        new_config = AppConfig(
            mode=mode_var.get(),
            server_ip=ip_var.get().strip(),
            port=port,
            autostart=autostart_var.get(),
            first_run=False,
        )
        new_config.save()

        # 同步注册表
        exe_path = sys.executable
        set_autostart(autostart_var.get(), exe_path)

        result[0] = new_config
        if on_save:
            on_save(new_config)
        root.destroy()

    def _cancel():
        root.destroy()

    ttk.Button(btn_frame, text="保存", command=_save, width=10).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="取消", command=_cancel, width=10).pack(side="left", padx=4)

    # 首次运行：关闭窗口 = 退出
    if is_first_run:
        root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

    root.mainloop()

    if is_first_run and result[0] is None:
        sys.exit(0)

    return result[0]
