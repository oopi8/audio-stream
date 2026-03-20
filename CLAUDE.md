# AudioStream

局域网音频串流工具，将台式机系统音频实时传输到笔记本播放。

## 重要约束

- **仅支持 Windows**，不要引入跨平台兼容代码，除非明确要做跨平台
- 音频捕获依赖 `pyaudiowpatch`（WASAPI Loopback），不要换成其他库
- 注册表自启动（`autostart.py`）已用 `sys.platform` 守卫，Mac 下是空操作

## 项目结构

| 文件 | 职责 |
|------|------|
| `main.py` | 入口，首次运行检测 + 启动托盘 |
| `server.py` | `AudioServer` 类，捕获音频 + UDP 发送 |
| `client.py` | `AudioClient` 类，接收音频 + 播放，自动重连 |
| `tray.py` | pystray 托盘，线程安全架构（queue 通信） |
| `settings.py` | tkinter 设置弹窗 |
| `config.py` | JSON 配置读写，存于 `%APPDATA%\AudioStream\` |
| `autostart.py` | winreg 开机自启 |
| `icon_assets.py` | Pillow 动态生成托盘图标 |

## 关键参数

- `CHUNK = 512`，`BUFFER_MAXSIZE = 8`，延迟约 85ms
- 心跳超时 5s，重连间隔 3s
- 协议：UDP，默认端口 5000

## 线程模型

- pystray 在独立 daemon 线程运行（`threading.Thread(target=icon.run)`）
- tkinter 在主线程运行
- pystray 回调 → 主线程通信通过 `queue.Queue` + `root.after()` 轮询

## 遗留问题

- 开机自启在直接运行 `.py` 时不完整，需打包 `.exe` 后才完整可用
- 跨平台支持尚未实现

## GitHub

`https://github.com/oopi8/audio-stream`
