"""
Hardware diagnostic, model cache manager, and benchmarking service.
Integrated with AppLogger and ProgressTracker.
"""
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

import onnxruntime as ort

from .logger import AppLogger
from .progress import ProgressTracker


class HardwareService:
    @staticmethod
    def get_hardware_info() -> Dict[str, Any]:
        """Kiểm tra chi tiết thông tin phần cứng CPU, GPU và thư viện AI."""
        # 1. CPU Info
        cpu_name = platform.processor() or "Unknown CPU"
        cpu_cores = os.cpu_count() or 1

        # 2. GPU Info qua nvidia-smi
        has_nvidia = False
        gpu_name = "Không tìm thấy GPU NVIDIA"
        gpu_vram = ""
        gpu_driver = ""
        try:
            res = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                encoding="utf-8",
                stderr=subprocess.DEVNULL
            ).strip()
            if res:
                parts = [p.strip() for p in res.split(",")]
                if len(parts) >= 3:
                    has_nvidia = True
                    gpu_name = parts[0]
                    gpu_vram = parts[1]
                    gpu_driver = parts[2]
                    AppLogger.info(f"Phát hiện GPU NVIDIA: {gpu_name} ({gpu_vram}) | Driver: {gpu_driver}", source="Hardware")
        except Exception as e:
            AppLogger.info("Không tìm thấy lệnh nvidia-smi hoặc máy không có GPU rời NVIDIA.", source="Hardware")

        # 3. PyTorch & CUDA Readiness
        has_torch = False
        cuda_available = False
        torch_version = ""
        torch_cuda_device = ""
        try:
            import torch
            has_torch = True
            torch_version = torch.__version__
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                torch_cuda_device = torch.cuda.get_device_name(0)
                AppLogger.success(f"PyTorch CUDA sẵn sàng: v{torch_version} ({torch_cuda_device})", source="Hardware")
            else:
                AppLogger.warning(f"PyTorch v{torch_version} đã cài nhưng chưa hỗ trợ CUDA.", source="Hardware")
        except ImportError:
            AppLogger.info("PyTorch chưa được cài đặt trong môi trường này.", source="Hardware")

        # 4. ONNX Runtime info
        ort_version = ort.__version__
        ort_providers = ort.get_available_providers()
        AppLogger.info(f"ONNX Runtime v{ort_version} providers: {ort_providers}", source="Hardware")

        return {
            "cpu_name": cpu_name,
            "cpu_cores": cpu_cores,
            "has_nvidia": has_nvidia,
            "gpu_name": gpu_name,
            "gpu_vram": gpu_vram,
            "gpu_driver": gpu_driver,
            "has_torch": has_torch,
            "cuda_available": cuda_available,
            "torch_version": torch_version,
            "torch_cuda_device": torch_cuda_device,
            "ort_version": ort_version,
            "ort_providers": ort_providers,
        }

    @staticmethod
    def get_model_cache_info() -> Dict[str, Any]:
        """Kiểm tra dung lượng và trạng thái tải của các mô hình trong Hugging Face Hub cache."""
        hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

        models = {
            "v3_turbo": {
                "name": "VieNeu-TTS-v3-Turbo (48kHz)",
                "repo": "pnnbao-ump/VieNeu-TTS-v3-Turbo",
                "folder": hf_cache_dir / "models--pnnbao-ump--VieNeu-TTS-v3-Turbo",
                "is_downloaded": False,
                "size_mb": 0.0,
            },
            "v3_nano": {
                "name": "VieNeu-TTS-v3-Nano (24kHz)",
                "repo": "pnnbao-ump/VieNeu-TTS-v3-Nano",
                "folder": hf_cache_dir / "models--pnnbao-ump--VieNeu-TTS-v3-Nano",
                "is_downloaded": False,
                "size_mb": 0.0,
            },
            "moss_tokenizer": {
                "name": "MOSS-Audio-Tokenizer-Nano",
                "repo": "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
                "folder": hf_cache_dir / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX",
                "is_downloaded": False,
                "size_mb": 0.0,
            }
        }

        total_size_mb = 0.0

        for key, m in models.items():
            folder = m["folder"]
            if folder.exists() and any(folder.iterdir()):
                m["is_downloaded"] = True
                size_bytes = sum(f.stat().st_size for f in folder.glob("**/*") if f.is_file())
                size_mb = size_bytes / (1024 * 1024)
                m["size_mb"] = round(size_mb, 1)
                total_size_mb += size_mb

        return {
            "cache_dir": str(hf_cache_dir),
            "models": models,
            "total_size_mb": round(total_size_mb, 1),
        }

    @staticmethod
    def run_benchmark(
        tts_engine,
        voice: str = "Minh Quân",
        progress_tracker: Optional[ProgressTracker] = None
    ) -> Dict[str, Any]:
        """
        Chạy một bài test benchmark chuẩn hóa với báo cáo tiến trình % và log.
        """
        sample_text = "Chào mừng bạn đến với hệ thống giọng nói nhân tạo VieNeu-TTS Studio."
        if not tts_engine.is_ready():
            err_msg = "Mô hình TTS chưa sẵn sàng. Vui lòng nạp mô hình trước khi chạy benchmark!"
            AppLogger.warning(err_msg, source="Benchmark")
            if progress_tracker:
                progress_tracker.error(err_msg)
            return {
                "success": False,
                "error": err_msg
            }

        try:
            if progress_tracker:
                progress_tracker.update(15.0, message="Chuẩn bị văn bản thử nghiệm chuẩn...", stage="Benchmark")

            AppLogger.info("Bắt đầu bài kiểm tra Benchmark tốc độ...", source="Benchmark")
            start_time = time.time()
            engine_inst = tts_engine._engine

            if progress_tracker:
                progress_tracker.update(45.0, message="Đang suy luận giọng nói chuẩn...", stage="Inference")

            audio = engine_inst.infer(sample_text, voice=voice)
            process_time = time.time() - start_time

            if progress_tracker:
                progress_tracker.update(85.0, message="Đang tính toán chỉ số RTF và đánh giá phần cứng...", stage="Metrics")

            sample_rate = getattr(engine_inst, "sample_rate", 48000)
            duration = len(audio) / sample_rate if sample_rate > 0 else 0.0
            rtf = process_time / duration if duration > 0 else 0.0
            speed_multiplier = duration / process_time if process_time > 0 else 0.0

            rating = "Siêu tốc 🚀" if rtf < 0.3 else ("Mượt mà ⚡" if rtf < 0.7 else "Bình thường ⏱️")

            result = {
                "success": True,
                "text": sample_text,
                "process_time": round(process_time, 2),
                "duration": round(duration, 2),
                "rtf": round(rtf, 3),
                "speed_multiplier": round(speed_multiplier, 1),
                "rating": rating,
                "sample_rate": sample_rate,
                "backend": tts_engine._current_config["name"] if tts_engine._current_config else "Default"
            }

            if progress_tracker:
                progress_tracker.complete(f"Benchmark hoàn tất! RTF: {rtf:.3f} ({rating})")

            AppLogger.success(
                f"Benchmark hoàn tất! RTF: {rtf:.3f} | Tốc độ: {speed_multiplier:.1f}x real-time ({rating})",
                source="Benchmark"
            )
            return result

        except Exception as e:
            AppLogger.exception("Lỗi khi chạy benchmark", exc=e, source="Benchmark")
            if progress_tracker:
                progress_tracker.error(f"Lỗi: {e}")
            return {
                "success": False,
                "error": str(e)
            }
