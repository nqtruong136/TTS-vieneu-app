# 🦜 VieNeu-TTS Desktop Studio

Ứng dụng Desktop chuyên nghiệp cho mô hình chuyển đổi văn bản thành giọng nói tiếng Việt **VieNeu-TTS v3 Turbo (48 kHz)**, xây dựng bằng **CustomTkinter** với kiến trúc phân tầng chuẩn, điều hướng thanh bên trái (Left Nav Rail) và 4 không gian làm việc chuyên biệt.

---

## 🌟 Cấu trúc Giao diện & Tính năng

### 1. Thanh điều hướng chính (Left Primary Nav Rail)
Nằm ở cạnh trái ngoài cùng với 4 mục chính:
- 🎙️ **Giọng có sẵn (Preset Voices)**: Trải nghiệm TTS với 23 giọng đọc Việt ngữ.
- 🧬 **Clone Voice (Voice Cloning Studio)**: Không gian nhân bản giọng nói từ audio 3–8s.
- ⚙️ **Cài đặt & Phần cứng (Settings & Diagnostics)**: Kiểm tra CPU/GPU, tải model, benchmark tốc độ.
- 📋 **Lịch sử tạo (History)**: Quản lý và nghe lại toàn bộ các bản thu.

---

### 2. Chi tiết 4 Phân hệ (Views)

#### 🎙️ Phân hệ 1: Giọng có sẵn (Preset Voices)
- **Bộ lọc 23 giọng đọc**: Lọc nhanh theo Tất cả, Nam, Nữ, miền Bắc, miền Nam.
- **Thẻ thông tin chi tiết**: Hiển thị phong cách (Tự nhiên, Tin tức, Kể chuyện).
- **Soạn thảo & Chèn cảm xúc**: Gắn nhanh các nhãn `[cười]`, `[thở dài]`, `[hắng giọng]`, `[ngập ngừng]`.
- **Trình phát âm thanh tích hợp**: Play, Pause, Stop, Volume, Timeline slider, đo RTF thời gian thực.

#### 🧬 Phân hệ 2: Clone Voice (Nhân bản giọng nói)
- **File âm thanh mẫu**: Chọn file mẫu 3–8s (.wav, .mp3, .flac, .m4a).
- **Trình nghe thử mẫu**: Nghe lại clip mẫu để kiểm tra độ rõ ràng trước khi clone.
- **Tùy chọn Khử nhiễu**: Công tắc tự động lọc ồn clip mẫu trước khi trích xuất âm sắc.
- **Soạn thảo câu đọc mới**: Tổng hợp câu mới mang đúng âm sắc người thật.

#### ⚙️ Phân hệ 3: Cài đặt hệ thống & Benchmark
- **1. Kiểm tra phần cứng (Hardware Readiness)**:
  - CPU: Tên vi xử lý, số luồng xử lý, ONNX Runtime version.
  - GPU: Tự động phát hiện GPU NVIDIA (ví dụ: `NVIDIA GeForce GTX 1660 Ti`, 6GB VRAM, Driver).
  - Trạng thái PyTorch CUDA: Báo trạng thái sẵn sàng và nút tự động cài đặt PyTorch CUDA 1-click.
- **2. Cấu hình Engine & Thiết bị**:
  - Chọn cấu hình: Tiêu chuẩn CPU (fp32), Tăng tốc CPU (int8 VNNI), Siêu nhẹ (Nano 24kHz), GPU PyTorch (CUDA).
  - Nút áp dụng & reload engine ngầm không treo app.
- **3. Quản lý Cache Mô hình (Model Cache Manager)**:
  - Kiểm tra dung lượng cache Hugging Face trên máy tính.
  - Hiển thị trạng thái các mô hình (v3 Turbo, v3 Nano, Tokenizer).
  - Nút tải trước mô hình và nút mở thư mục cache trong Windows Explorer.
- **4. Kiểm tra Benchmark Tốc độ (Speed Benchmark)**:
  - Sinh câu chuẩn 15 từ, đo lường: Thời gian xử lý, độ dài audio, chỉ số **RTF (Real-Time Factor)**.
  - Đưa ra đánh giá tốc độ thực tế (ví dụ: "Nhanh hơn 5.5x real-time - Siêu tốc 🚀").

#### 🎵 Phân hệ 4: Các giọng đã tạo (Generated Voice Library & YouTube Scrubber)
- **Hệ thống phân trang hoàn chỉnh (Pagination)**:
  - Tùy chọn số lượng bản ghi: `6`, `10`, hoặc `20 bản ghi / trang`.
  - Nút chuyển trang trực quan: `⏮ Đầu`, `◀ Trước`, `Sau ▶`, `Cuối ⏭` kèm nhãn thống kê `Trang X/Y (N bản ghi)`.
- **Bộ lọc & Tìm kiếm**: Lọc theo từ khóa văn bản và lọc theo từng giọng đọc cụ thể.
- **Trình phát âm thanh kiểu YouTube (YouTube-style Audio Scrubber)**:
  - Thanh trượt tua thời gian tương tác (Interactive Scrubber Slider) kéo thả chuột hoặc nhấp để tua ngay lập tức.
  - Phím nhảy nhanh: `⏪ -5s` (lùi 5 giây), `▶ / ⏸` (phát / tạm dừng), `+5s ⏩` (tiến 5 giây), `⏹` (dừng hẳn).
  - Đồng hồ thời gian thực: `00:15 / 01:45`, thanh âm lượng kèm icon `🔊 / 🔉 / 🔇`.

---

### 3. Hệ thống Interface Lập trình Chuyên nghiệp

#### 📜 Global Logging Interface (`AppLogger`)
- Cho phép gọi từ bất kỳ module nào trong dự án:
  ```python
  from src.core.logger import AppLogger
  AppLogger.info("Thông báo thường", source="MyModule")
  AppLogger.success("Xử lý thành công", source="MyModule")
  AppLogger.exception("Bắt trọn vẹn Stack Trace khi có ngoại lệ", exc=e, source="MyModule")
  ```
- **UI Log Console**: Nằm trực tiếp tại Tab Cài đặt (Section 5) và có thể mở thành cửa sổ popup riêng biệt từ nút `📜 Xem Log Console` trên thanh điều hướng. Tích hợp bộ lọc cấp độ (`INFO`, `WARNING`, `ERROR`), nút sao chép (`Clipboard`) và nút xóa log.

#### 📊 Percentage Progress Interface (`ProgressTracker` + `ProgressDisplay`)
- Quản lý và phát sự kiện tiến trình phần trăm (0% – 100%) an toàn đa luồng:
  ```python
  from src.core.progress import ProgressTracker
  tracker = ProgressTracker()
  tracker.update(45.0, message="Đang suy luận âm thanh...", stage="Inference")
  tracker.complete("Hoàn thành!")
  ```
- **ProgressDisplay Component**: Hiển thị thanh tiến trình đồ họa động kèm số `%` cụ thể và nhãn trạng thái đổi màu (`Xanh lá` khi xong, `Đỏ` khi lỗi).
- Tích hợp tại:
  - Quá trình nạp mô hình AI & tổng hợp giọng nói trong `PresetView` và `CloneVoiceView`.
  - Quá trình tự động tải bánh xe PyTorch CUDA.
  - Quá trình tải trước trọng số mô hình từ Hugging Face Hub.
  - Quá trình đo kiểm tốc độ phần cứng (Benchmark).

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

