"""
Configuration and constants for VieNeu-TTS Desktop Studio.
"""
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List

# Thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / "history.db"

# Cấu hình giao diện
APP_TITLE = "🦜 VieNeu-TTS Studio - Desktop Edition"
APP_GEOMETRY = "1280x780"
APP_MINSIZE = (1050, 680)

# Cấu hình hồ sơ mẫu (Presets / Profiles) dựa trên VieNeu-TTS README & SDK
PROFILES: Dict[str, Dict[str, Any]] = {
    "v3_turbo_cpu_fp32": {
        "name": "Tiêu chuẩn - CPU (v3 Turbo fp32)",
        "mode": "v3turbo",
        "backend": "onnx",
        "precision": "fp32",
        "device": "cpu",
        "sample_rate": 48000,
        "description": "Chất lượng âm thanh 48kHz cao nhất, chạy mượt trên mọi CPU với ONNX Runtime (Torch-free)."
    },
    "v3_turbo_cpu_int8": {
        "name": "Tăng tốc - CPU (v3 Turbo int8)",
        "mode": "v3turbo",
        "backend": "onnx",
        "precision": "int8",
        "device": "cpu",
        "sample_rate": 48000,
        "description": "Nhanh hơn ~1.6x, model nhẹ hơn 4x (Khuyên dùng cho CPU Intel/AMD có tập lệnh AVX-VNNI)."
    },
    "v3_nano_cpu": {
        "name": "Siêu nhẹ - CPU (v3 Nano 24kHz)",
        "mode": "v3nano",
        "backend": "onnx",
        "precision": "fp32",
        "device": "cpu",
        "sample_rate": 24000,
        "description": "Mô hình Flow 48M siêu nhẹ cho máy tính cấu hình yếu hoặc cần phản hồi tức thì (24kHz)."
    },
    "v3_turbo_gpu_cuda": {
        "name": "GPU NVIDIA - PyTorch (CUDA)",
        "mode": "v3turbo",
        "backend": "pytorch",
        "precision": "auto",
        "device": "cuda",
        "sample_rate": 48000,
        "description": "Dành cho máy có card đồ họa NVIDIA CUDA, tự động batching tối ưu cho văn bản dài."
    }
}

DEFAULT_PROFILE_KEY = "v3_turbo_cpu_fp32"

# 23 giọng đọc dựng sẵn của VieNeu-TTS v3 Turbo
PRESET_VOICES = [
    {"name": "Minh Quân", "gender": "Nam", "region": "Bắc", "style": "Tự nhiên", "desc": "Nam · Bắc · Phong cách tự nhiên (Mặc định)"},
    {"name": "Ngọc Lan", "gender": "Nữ", "region": "Bắc", "style": "Tự nhiên", "desc": "Nữ · Bắc · Phong cách tự nhiên"},
    {"name": "Phạm Tuyên", "gender": "Nam", "region": "Bắc", "style": "Tự nhiên", "desc": "Nam · Bắc · Phong cách tự nhiên"},
    {"name": "Minh Đức", "gender": "Nam", "region": "Bắc", "style": "Tin tức", "desc": "Nam · Bắc · Phong cách tin tức"},
    {"name": "Thái Sơn", "gender": "Nam", "region": "Nam", "style": "Kể chuyện", "desc": "Nam · Nam · Phong cách kể chuyện"},
    {"name": "Xuân Vĩnh", "gender": "Nam", "region": "Bắc", "style": "Tự nhiên", "desc": "Nam · Bắc · Phong cách tự nhiên"},
    {"name": "Thanh Bình", "gender": "Nam", "region": "Bắc", "style": "Kể chuyện", "desc": "Nam · Bắc · Phong cách kể chuyện"},
    {"name": "Trúc Ly", "gender": "Nữ", "region": "Bắc", "style": "Tự nhiên", "desc": "Nữ · Bắc · Phong cách tự nhiên"},
    {"name": "Ngọc Linh", "gender": "Nữ", "region": "Bắc", "style": "Kể chuyện", "desc": "Nữ · Bắc · Phong cách kể chuyện"},
    {"name": "Đoan Trang", "gender": "Nữ", "region": "Bắc", "style": "Tự nhiên", "desc": "Nữ · Bắc · Phong cách tự nhiên"},
    {"name": "Mai Anh", "gender": "Nữ", "region": "Bắc", "style": "Tin tức", "desc": "Nữ · Bắc · Phong cách tin tức"},
    {"name": "Thục Đoan", "gender": "Nữ", "region": "Nam", "style": "Tự nhiên", "desc": "Nữ · Nam · Phong cách tự nhiên"},
    {"name": "Minh Triết", "gender": "Nam", "region": "Nam", "style": "Tự nhiên", "desc": "Nam · Nam · Phong cách tự nhiên"},
    {"name": "Thùy Dung", "gender": "Nữ", "region": "Bắc", "style": "Tự nhiên", "desc": "Nữ · Bắc · Phong cách tự nhiên"},
    {"name": "Quang Sơn", "gender": "Nam", "region": "Bắc", "style": "Tự nhiên", "desc": "Nam · Bắc · Phong cách tự nhiên"},
    {"name": "Ngọc Trân", "gender": "Nữ", "region": "Nam", "style": "Kể chuyện", "desc": "Nữ · Nam · Phong cách kể chuyện"},
    {"name": "Mỹ Duyên", "gender": "Nữ", "region": "Nam", "style": "Tự nhiên", "desc": "Nữ · Nam · Phong cách tự nhiên"},
    {"name": "Quỳnh Anh", "gender": "Nữ", "region": "Bắc", "style": "Tự nhiên", "desc": "Nữ · Bắc · Phong cách tự nhiên"},
    {"name": "Đức Trí", "gender": "Nam", "region": "Nam", "style": "Tự nhiên", "desc": "Nam · Nam · Phong cách tự nhiên"},
    {"name": "Kim Thanh", "gender": "Nữ", "region": "Nam", "style": "Tin tức", "desc": "Nữ · Nam · Phong cách tin tức"},
    {"name": "Ngọc Huyền", "gender": "Nữ", "region": "Bắc", "style": "Tự nhiên", "desc": "Nữ · Bắc · Phong cách tự nhiên"},
    {"name": "Adam", "gender": "Nam", "region": "Song ngữ", "style": "Song ngữ", "desc": "Nam · Song ngữ (Việt - Anh)"},
    {"name": "Mạnh Dũng", "gender": "Nam", "region": "Bắc", "style": "Tự nhiên", "desc": "Nam · Bắc · Phong cách tự nhiên"},
    {"name": "Anh Khôi", "gender": "Nam", "region": "Nam", "style": "Tự nhiên", "desc": "Nam · Nam · Phong cách tự nhiên"},
]

DEFAULT_VOICE = "Minh Quân"
AVAILABLE_VOICES = [v["name"] for v in PRESET_VOICES]

# Thẻ cảm xúc & biểu cảm hỗ trợ trực tiếp trong v3 Turbo
EMOTION_TAGS = [
    {"label": "😄 Cười", "tag": "[cười]"},
    {"label": "😮‍💨 Thở dài", "tag": "[thở dài]"},
    {"label": "🗣️ Hắng giọng", "tag": "[hắng giọng]"},
    {"label": "🤔 Ngập ngừng", "tag": "[ngập ngừng]"},
]

# Văn bản mặc định ban đầu
DEFAULT_SAMPLE_TEXT = (
    "[cười] Chào bạn! Đây là ứng dụng VieNeu-TTS Studio thế hệ mới. "
    "Mô hình v3 Turbo chạy trực tiếp trên máy với chất lượng âm thanh 48kHz mượt mà và tự nhiên. "
    "Bạn có thể thử chèn các biểu cảm như thở dài hay hắng giọng vào câu văn nhé!"
)

