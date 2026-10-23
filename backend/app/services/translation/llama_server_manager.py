import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


class LlamaServerManager:
    """
    Quản lý vòng đời tiến trình độc lập Standalone llama.cpp Server (Managed Subprocess).

    Quy tắc & Rào chắn phần cứng v3.3:
    1. Tách biệt tiến trình serving: Chạy llama.cpp server trong subprocess riêng,
       không gộp chung in-process vào FastAPI để tránh nghẽn GIL/EventLoop.
    2. Model mặc định: gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf (~2.62 GB).
    3. Tối ưu CPU Intel Core i5-13500H: Cấu hình chính xác 4 P-cores (-t 4 -tb 4).
    4. Trần cứng bộ nhớ: RAM <= 8.0 GB (Thực tế ~4.2 GB ở 16K context).
    5. Cửa sổ ngữ cảnh 16K (16384 tokens) / tùy chọn 8K (8192 tokens).
    6. Thu hồi sạch 100% tài nguyên (stop_server / terminate subprocess).
    """

    _instance: "LlamaServerManager | None" = None
    _lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        model_path: Path | str | None = None,
        host: str | None = None,
        port: int | None = None,
        n_ctx: int | None = None,
        n_threads: int | None = None,
        n_gpu_layers: int | None = None,
    ):
        target_ctx = n_ctx or settings.LLM_LOCAL_N_CTX
        if target_ctx > settings.LLM_LOCAL_MAX_N_CTX:
            raise ValueError(
                f"Kích thước ngữ cảnh n_ctx={target_ctx} vượt quá giới hạn trần cứng "
                f"cho phép ({settings.LLM_LOCAL_MAX_N_CTX} tokens / <= 8.0GB RAM)."
            )

        self.model_path = Path(model_path or settings.llm_model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Không tìm thấy tệp mô hình GGUF tại: {self.model_path}. "
                f"Vui lòng đặt mô hình Gemma-4-E2B ({settings.LLM_MODEL_NAME}) vào {settings.models_dir}."
            )

        self.host = host or settings.LLM_SERVER_HOST
        self.port = port or settings.LLM_SERVER_PORT
        self.n_ctx = target_ctx
        self.n_threads = n_threads or settings.LLM_LOCAL_THREADS  # 4 P-cores trên i5-13500H
        self.n_threads_batch = self.n_threads
        self.n_batch = settings.LLM_LOCAL_N_BATCH
        self.n_gpu_layers = settings.LLM_LOCAL_N_GPU_LAYERS if n_gpu_layers is None else n_gpu_layers
        self.base_url = f"http://{self.host}:{self.port}"

        self._process: subprocess.Popen[Any] | None = None

    @classmethod
    def get_instance(
        cls,
        model_path: Path | str | None = None,
        host: str | None = None,
        port: int | None = None,
        n_ctx: int | None = None,
        n_threads: int | None = None,
        n_gpu_layers: int | None = None,
    ) -> "LlamaServerManager":
        """Lấy thể hiện Singleton duy nhất của LlamaServerManager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    model_path=model_path,
                    host=host,
                    port=port,
                    n_ctx=n_ctx,
                    n_threads=n_threads,
                    n_gpu_layers=n_gpu_layers,
                )
            return cls._instance

    @property
    def is_running(self) -> bool:
        """Kiểm tra tiến trình server con có còn đang chạy hay không."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def is_healthy(self, timeout: float = 1.0) -> bool:
        """Gửi HTTP GET kiểm tra trạng thái sống của standalone server."""
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(f"{self.base_url}/docs")
                return resp.status_code == 200
        except Exception:
            return False

    async def is_healthy_async(self, timeout: float = 1.0) -> bool:
        """Gửi async HTTP GET kiểm tra trạng thái sống của standalone server."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self.base_url}/docs")
                return resp.status_code == 200
        except Exception:
            return False

    def start_server(self, wait_timeout: float = 30.0) -> None:
        """
        Khởi chạy tiến trình llama.cpp server độc lập qua python -m llama_cpp.server.
        Cấu hình tối ưu cho Intel Core i5-13500H (4 P-cores, 16K/8K ctx, trần 8GB RAM).
        """
        with self._lock:
            if self.is_running and self.is_healthy():
                logger.info(f"Standalone llama.cpp server đã đang chạy tại {self.base_url}.")
                return

            if not self.model_path.is_file():
                raise FileNotFoundError(
                    f"Không tìm thấy tệp mô hình GGUF tại: {self.model_path}."
                )

            python_exe = sys.executable
            cmd = [
                python_exe,
                "-m",
                "llama_cpp.server",
                "--model",
                str(self.model_path),
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--n_ctx",
                str(self.n_ctx),
                "--n_threads",
                str(self.n_threads),
                "--n_threads_batch",
                str(self.n_threads_batch),
                "--n_batch",
                str(self.n_batch),
                "--n_gpu_layers",
                str(self.n_gpu_layers),
                "--verbose",
                "False",
            ]

            logger.info(
                f"Bắt đầu khởi chạy Standalone llama.cpp Server subprocess: "
                f"model={self.model_path.name}, port={self.port}, 4 P-cores (threads={self.n_threads}), "
                f"n_ctx={self.n_ctx}, n_gpu_layers={self.n_gpu_layers}..."
            )

            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            self._process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Chờ server khởi động thành công
            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                if not self.is_running:
                    exit_code = self._process.poll()
                    raise RuntimeError(
                        f"Tiến trình llama.cpp server bị dừng đột ngột với mã lỗi {exit_code}."
                    )
                if self.is_healthy():
                    logger.info(f"Standalone llama.cpp server đã sẵn sàng hoạt động tại {self.base_url}!")
                    return
                time.sleep(0.5)

            # Quá thời gian chờ
            self.stop_server()
            raise TimeoutError(f"Quá thời gian ({wait_timeout}s) chờ Standalone llama.cpp server khởi động.")

    async def ensure_server_running(self, wait_timeout: float = 30.0) -> None:
        """Đảm bảo server đang chạy (chạy bất đồng bộ để tránh block FastAPI loop)."""
        if self.is_running and await self.is_healthy_async():
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.start_server(wait_timeout=wait_timeout))

    def stop_server(self) -> None:
        """Dừng tiến trình server độc lập và thu hồi sạch 100% tài nguyên RAM/CPU."""
        with self._lock:
            if self._process is not None:
                try:
                    logger.info(f"Đang dừng tiến trình Standalone llama.cpp server (PID: {self._process.pid})...")
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait(timeout=2.0)
                    logger.info("Đã dừng thành công Standalone llama.cpp server và thu hồi sạch tài nguyên.")
                except Exception as e:
                    logger.warning(f"Lỗi khi dừng tiến trình server: {e}")
                finally:
                    self._process = None

    @classmethod
    def reset(cls) -> None:
        """Dọn dẹp và reset instance cho testing/shutdown."""
        if cls._instance is not None:
            cls._instance.stop_server()
        cls._instance = None
