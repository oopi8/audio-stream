# AudioStream

局域网音频串流工具 —— 将台式机系统音频实时传输到笔记本播放。

常驻系统托盘，开机自启，自动重连，无需命令行操作。

## 效果

- 台式机播放的任何声音（游戏、视频、音乐）实时出现在笔记本扬声器
- 延迟约 100ms 以内
- 断线后自动重连

## 环境要求

- Windows 10 / 11
- Python 3.10+
- 两台电脑在同一局域网

## 安装

```bat
pip install -r requirements.txt
```

## 使用

两台电脑都运行：

```bat
python main.py
```

**首次运行**会弹出设置窗口：
- 台式机选 **服务端**，填写端口（默认 5000）
- 笔记本选 **客户端**，填写台式机的 IP 地址和端口
- 勾选「开机自启动」后重启生效

之后程序常驻系统托盘，图标颜色表示状态：

| 颜色 | 含义 |
|------|------|
| 绿色 | 已连接 |
| 黄色 | 连接中 |
| 灰色 | 已停止 |
| 红色 | 错误 |

右键托盘图标可打开设置或退出。

## 防火墙

首次使用需在台式机 Windows 防火墙中放行 UDP 端口（默认 5000）：

```
控制面板 → Windows Defender 防火墙 → 高级设置 → 入站规则 → 新建规则
→ 端口 → UDP → 5000 → 允许连接
```

## 注意事项

- 仅支持 Windows（依赖 WASAPI Loopback 音频捕获）
- 开机自启在打包为 `.exe` 后才完整可用，直接运行 Python 脚本时注册表路径指向 `python.exe`

## 依赖

- [pyaudiowpatch](https://github.com/s0d3s/PyAudioWPatch) — WASAPI Loopback 音频捕获
- [sounddevice](https://python-sounddevice.readthedocs.io/) — 音频播放
- [pystray](https://github.com/moses-palmer/pystray) — 系统托盘
- [Pillow](https://pillow.readthedocs.io/) — 图标生成
