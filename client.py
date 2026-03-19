"""
client.py - 客户端：接收 UDP 音频数据并通过 sounddevice 播放
AudioClient 类，支持 start() / stop()，自动重连
"""

import socket
import threading
import queue
import time
import struct
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

HEARTBEAT_INTERVAL = 1.5
BUFFER_MAXSIZE = 8
RECV_TIMEOUT = 5.0   # 超过此时间无数据则重连
RETRY_INTERVAL = 3.0  # 重连等待秒数


class AudioClient:
    def __init__(
        self,
        server_ip: str,
        port: int,
        on_status_change: Optional[Callable[[str], None]] = None,
    ):
        self.server_ip = server_ip
        self.port = port
        self.on_status_change = on_status_change
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_with_retry, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=8)
            self._thread = None

    def _notify(self, status: str):
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass

    def _run_with_retry(self):
        while not self._stop_event.is_set():
            self._notify("connecting")
            try:
                self._run_once()
            except Exception:
                pass

            if self._stop_event.is_set():
                break

            self._notify("connecting")
            # 等待重试，每 0.5s 检查 stop_event
            deadline = time.time() + RETRY_INTERVAL
            while time.time() < deadline and not self._stop_event.is_set():
                time.sleep(0.5)

        self._notify("stopped")

    def _run_once(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(RECV_TIMEOUT)
        server_addr = (self.server_ip, self.port)
        audio_queue: queue.Queue = queue.Queue(maxsize=BUFFER_MAXSIZE)
        config_event = threading.Event()
        audio_config: dict = {"rate": None, "channels": None}

        def send_heartbeat():
            while not self._stop_event.is_set() and not config_event.is_set():
                try:
                    sock.sendto(b"PING", server_addr)
                except OSError:
                    return
                time.sleep(HEARTBEAT_INTERVAL)
            # 配置收到后继续心跳
            while not self._stop_event.is_set():
                try:
                    sock.sendto(b"PING", server_addr)
                except OSError:
                    return
                time.sleep(HEARTBEAT_INTERVAL)

        hb_thread = threading.Thread(target=send_heartbeat, daemon=True)
        hb_thread.start()

        # 立即发一次心跳，让服务端尽快感知
        try:
            sock.sendto(b"PING", server_addr)
        except OSError:
            sock.close()
            return

        recv_ok = [True]

        def receive_loop():
            while not self._stop_event.is_set():
                try:
                    data, _ = sock.recvfrom(65535)
                except socket.timeout:
                    recv_ok[0] = False
                    return
                except OSError:
                    recv_ok[0] = False
                    return

                if data == b"PONG":
                    continue

                if data[:3] == b"CFG" and len(data) == 11:
                    rate, channels = struct.unpack("!II", data[3:])
                    audio_config["rate"] = rate
                    audio_config["channels"] = channels
                    config_event.set()
                    self._notify("connected")
                    continue

                if config_event.is_set():
                    try:
                        audio_queue.put_nowait(data)
                    except queue.Full:
                        try:
                            audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            audio_queue.put_nowait(data)
                        except queue.Full:
                            pass

        recv_thread = threading.Thread(target=receive_loop, daemon=True)
        recv_thread.start()

        # 等待服务端配置（最多 RECV_TIMEOUT + 1s）
        if not config_event.wait(timeout=RECV_TIMEOUT + 1):
            sock.close()
            recv_thread.join(timeout=1)
            return

        rate = audio_config["rate"]
        channels = audio_config["channels"]
        chunk_frames = 512
        dtype = np.int16
        silence = np.zeros(chunk_frames * channels, dtype=dtype)

        def audio_callback(outdata, frames, time_info, status):
            try:
                raw = audio_queue.get_nowait()
            except queue.Empty:
                outdata[:] = silence.reshape(frames, channels)
                return

            raw_array = np.frombuffer(raw, dtype=dtype)
            expected_len = frames * channels
            if len(raw_array) >= expected_len:
                outdata[:] = raw_array[:expected_len].reshape(frames, channels)
            else:
                padded = np.zeros(expected_len, dtype=dtype)
                padded[: len(raw_array)] = raw_array
                outdata[:] = padded.reshape(frames, channels)

        try:
            with sd.OutputStream(
                samplerate=rate,
                channels=channels,
                dtype="int16",
                blocksize=chunk_frames,
                callback=audio_callback,
                latency="low",
            ):
                while not self._stop_event.is_set() and recv_ok[0]:
                    time.sleep(0.1)
        except Exception:
            pass
        finally:
            sock.close()
            recv_thread.join(timeout=2)
