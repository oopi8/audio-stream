"""
server.py - 服务端：捕获系统音频（WASAPI Loopback）并通过 UDP 发送给客户端
AudioServer 类，支持 start() / stop()
"""

import socket
import threading
import time
import struct
from typing import Callable, Optional

import pyaudiowpatch as pyaudio

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000
CHUNK = 512
HEARTBEAT_TIMEOUT = 5  # 客户端心跳超时（秒）


def _find_loopback_device(pa: pyaudio.PyAudio):
    try:
        return pa.get_default_wasapi_loopback()
    except OSError:
        pass

    wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    for i in range(wasapi_info["deviceCount"]):
        device = pa.get_device_info_by_host_api_device_index(wasapi_info["index"], i)
        if device.get("isLoopbackDevice", False):
            return device

    raise RuntimeError("未找到 WASAPI Loopback 设备，请确认系统有音频输出设备")


class AudioServer:
    def __init__(self, port: int, on_status_change: Optional[Callable[[str], None]] = None):
        self.port = port
        self.on_status_change = on_status_change
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _notify(self, status: str):
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass

    def _run(self):
        self._notify("connecting")
        pa = pyaudio.PyAudio()
        sock = None
        stream = None

        try:
            device = _find_loopback_device(pa)
            device_index = device["index"]
            actual_rate = int(device["defaultSampleRate"])
            actual_channels = min(int(device["maxInputChannels"]), 2)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", self.port))
            sock.settimeout(0.5)

            client_addr = None
            client_lock = threading.Lock()
            last_heartbeat = [0.0]

            def heartbeat_listener():
                nonlocal client_addr
                while not self._stop_event.is_set():
                    try:
                        data, addr = sock.recvfrom(64)
                        if data == b"PING":
                            with client_lock:
                                client_addr = addr
                                last_heartbeat[0] = time.time()
                            sock.sendto(b"PONG", addr)
                            self._notify("connected")
                    except socket.timeout:
                        continue
                    except OSError:
                        break

            hb_thread = threading.Thread(target=heartbeat_listener, daemon=True)
            hb_thread.start()

            stream = pa.open(
                format=FORMAT,
                channels=actual_channels,
                rate=actual_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK,
            )

            config_sent_to: set = set()

            self._notify("connecting")  # 等待客户端连入

            while not self._stop_event.is_set():
                data = stream.read(CHUNK, exception_on_overflow=False)

                with client_lock:
                    addr = client_addr
                    hb_time = last_heartbeat[0]

                if addr is None:
                    continue

                if time.time() - hb_time > HEARTBEAT_TIMEOUT:
                    with client_lock:
                        if client_addr == addr:
                            client_addr = None
                            config_sent_to.discard(addr)
                    self._notify("connecting")
                    continue

                if addr not in config_sent_to:
                    config = struct.pack("!II", actual_rate, actual_channels)
                    sock.sendto(b"CFG" + config, addr)
                    config_sent_to.add(addr)

                try:
                    sock.sendto(data, addr)
                except OSError:
                    pass

        except Exception:
            self._notify("error")
        finally:
            self._notify("stopped")
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
