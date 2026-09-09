# 🦜 VieNeu-TTS Desktop Studio

Ứng dụng Desktop chuyên nghiệp cho mô hình chuyển đổi văn bản thành giọng nói tiếng Việt **VieNeu-TTS v3 Turbo (48 kHz)**, xây dựng bằng **CustomTkinter** với kiến trúc phân tầng chuẩn, điều hướng thanh bên trái (Left Nav Rail) và 5 không gian làm việc chuyên biệt.

---

## 🌟 Cấu trúc Giao diện & Tính năng

### 1. Thanh điều hướng chính (Left Primary Nav Rail)
Nằm ở cạnh trái ngoài cùng với 5 phân hệ chính:
- 🎙️ **Giọng có sẵn (Preset Voices)**: Trải nghiệm TTS với 23 giọng đọc Việt ngữ tiêu chuẩn.
- 🧬 **Clone Voice (Voice Cloning Studio)**: Nhân bản giọng nói từ audio 3–6s, hỗ trợ khử nhiễu & lọc vang trong trẻo.
- ⚡ **Đọc Realtime (Streaming Reader)**: Tự động đọc tức thì khi bạn bôi đen và bấm Copy (`Ctrl + C`) từ trình duyệt, sách, báo.
- 🎵 **Các giọng đã tạo (History Library)**: Quản lý thư viện bản thu với thanh trượt YouTube Scrubber.
- ⚙️ **Cài đặt & Phần cứng (Settings & Diagnostics)**: Kiểm tra CPU/GPU, cài đặt PyTorch CUDA tự động, benchmark tốc độ.

---

### 2. Chi tiết 5 Phân hệ (Views)

#### 🎙️ Phân hệ 1: Giọng có sẵn (Preset Voices)
- **Bộ lọc 23 giọng đọc**: Lọc nhanh theo Tất cả, Nam, Nữ, miền Bắc, miền Nam.
- **Thẻ thông tin chi tiết**: Hiển thị phong cách (Tự nhiên, Tin tức, Kể chuyện).
- **Soạn thảo & Chèn cảm xúc**: Gắn nhanh các nhãn `[cười]`, `[thở dài]`, `[hắng giọng]`, `[ngập ngừng]`.
- **Trình phát âm thanh tích hợp**: Play, Pause, Stop, Volume, Timeline slider, đo RTF thời gian thực.

#### 🧬 Phân hệ 2: Clone Voice (Nhân bản giọng nói)
- **File âm thanh mẫu**: Chọn file mẫu 3–6s (.wav, .mp3, .flac, .m4a).
- **Trình nghe thử mẫu**: Nghe lại clip mẫu để kiểm tra độ rõ ràng trước khi clone.
- **Tùy chọn Khử nhiễu (Denoise)**: Tự động lọc tạp âm nền trước khi trích xuất.
- **Ưu tiên trong trẻo (Clean Timbre)**: Loại bỏ tiếng vang dội phòng (reverb/boxiness) từ clip mẫu, tạo giọng đọc trong trẻo chuẩn studio 48kHz.

#### ⚡ Phân hệ 3: Đọc Realtime (Streaming Clipboard Reader)
- **Clipboard Trigger**: Tự động phát hiện văn bản mới khi bạn bôi đen và nhấn `Ctrl + C` trên trình duyệt, tài liệu PDF, Word.
- **Âm thanh theo luồng (`infer_stream`)**: Phản hồi siêu tốc, âm thanh cất lên chỉ sau ~500ms (RTF ~0.6).
- **Nút Dừng khẩn cấp**: Cắt âm thanh ngay lập tức trong `< 20ms`.
- **Thanh Quick History Preview**: Bố cục bên phải siêu gọn gàng, lưu nhanh các đoạn vừa copy kèm nút `▶ Nghe` mini và nút `📋 Copy` lại.

#### 🎵 Phân hệ 4: Các giọng đã tạo (Generated Voice Library & YouTube Scrubber)
- **Hệ thống phân trang hoàn chỉnh (Pagination)**: Tùy chọn `6`, `10`, hoặc `20 bản ghi / trang`.
- **Thanh công cụ trên đầu thẻ (Header Toolbar)**: Nút `▶ Nghe lại`, `📋 Dùng lại text`, `📂 File`, `✕ Xóa` luôn hiển thị ngay đầu thẻ.
- **Rút gọn thông minh**: Tự động thu gọn các bài đọc dài kèm nút `▼ Xem thêm` / `▲ Thu gọn`.
- **Trình phát âm thanh kiểu YouTube (YouTube-style Audio Scrubber)**:
  - Thanh trượt tua thời gian tương tác (Interactive Scrubber Slider).
  - Phím nhảy nhanh: `⏪ -5s`, `▶ / ⏸`, `+5s ⏩`, `⏹`.

#### ⚙️ Phân hệ 5: Cài đặt hệ thống & Benchmark
- **1. Kiểm tra phần cứng (Hardware Readiness)**: Tự động phát hiện GPU NVIDIA (GTX 1660 Ti...), VRAM, Driver, CUDA status.
- **2. Cấu hình Engine & Thiết bị**: Hỗ trợ 4 chế độ: Tiêu chuẩn CPU (fp32), Tăng tốc CPU (int8 VNNI), Siêu nhẹ (Nano 24kHz), GPU PyTorch (CUDA 12.8).
- **3. Tự động hóa GPU**: Cài đặt PyTorch CUDA tự động 1-click vào thư mục chỉ định.
- **4. Kiểm tra Benchmark Tốc độ**: Đo thời gian xử lý, độ dài audio, chỉ số RTF thực tế.

---

### 3. Hệ thống Interface Lập trình Chuyên nghiệp

#### 📜 Global Logging Interface (`AppLogger`)
```python
from src.core.logger import AppLogger
AppLogger.info("Thông báo thường", source="MyModule")
AppLogger.success("Xử lý thành công", source="MyModule")
AppLogger.exception("Bắt trọn vẹn Stack Trace khi có ngoại lệ", exc=e, source="MyModule")
```

#### 📊 Percentage Progress Interface (`ProgressTracker` + `ProgressDisplay`)
```python
from src.core.progress import ProgressTracker
tracker = ProgressTracker()
tracker.update(45.0, message="Đang suy luận âm thanh...", stage="Inference")
tracker.complete("Hoàn thành!")
```

---

## 🚀 Khởi chạy ứng dụng

### Cách 1: 1-Click (Khuyên dùng)
Nhấp đúp chuột vào file:
```
run.bat
```

### Cách 2: Chạy từ dòng lệnh
```powershell
.\.venv\Scripts\python main.py
```

### Cài đặt thư viện:
- Chạy bằng CPU thông thường:
  ```powershell
  pip install -r requirements.txt
  ```
- Chạy tăng tốc GPU NVIDIA (CUDA):
  ```powershell
  pip install -r requirements-gpu.txt
  ```

---

## 🙏 Nguồn & Lời cảm ơn (Credits & Acknowledgements)

Dự án này được phát triển dựa trên mô hình và bộ công cụ mã nguồn mở tuyệt vời của cộng đồng AI Việt Nam:

- **Mô hình & SDK gốc**: [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS) bởi tác giả **Phạm Nguyễn Ngọc Bảo ([@pnnbao97](https://github.com/pnnbao97))**.
- **Nền tảng thương mại & API**: [vieneu.io](https://vieneu.io).
- **Kiến trúc âm thanh**: Sử dụng neural codec **MOSS-Audio-Tokenizer-Nano (48 kHz)**.
- **Giao diện**: Xây dựng trên nền tảng **CustomTkinter** của Tom Schimansky.

Xin chân thành cảm ơn tác giả **Phạm Nguyễn Ngọc Bảo** đã phát triển và chia sẻ một mô hình TTS tiếng Việt mã nguồn mở có chất lượng rất cao cho cộng đồng!
