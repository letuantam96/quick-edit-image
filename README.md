# quick-edit-image

Quick edit image tool for Thanh Hang — paste ảnh, tự resize, đóng logo watermark, đặt tên rồi xuất PNG.

## Cách dùng

1. Điền **chiều rộng** (px). Mọi ảnh sẽ được resize về đúng chiều rộng này (phóng to nếu ảnh nhỏ hơn), chiều cao giữ tỉ lệ.
2. Bấm **Đổi…** để chọn watermark (file PNG, nên nền trong suốt). Watermark dùng chung cho tất cả ảnh.
3. Copy ảnh (từ web, Zalo, Photoshop, hoặc copy file trong Explorer) rồi nhấn **Ctrl+V** trong app. Ảnh được thêm vào danh sách và có watermark ngay.
4. Kéo watermark để đổi vị trí, kéo 4 góc để phóng to / thu nhỏ. Ảnh paste tiếp theo sẽ dùng vị trí và cỡ watermark của lần chỉnh gần nhất.
5. Gõ **tên file** cho từng ảnh (chọn ảnh ở danh sách bên trái). Phím Delete hoặc nút **Xóa ảnh** để bỏ ảnh.
6. Chọn thư mục ở thanh dưới, bấm **Xuất tất cả**. Ảnh chưa đặt tên, trùng tên hoặc tên có ký tự không hợp lệ sẽ nháy đỏ và không xuất cho đến khi sửa.

App nhớ chiều rộng, watermark, thư mục xuất và vị trí watermark cho lần mở sau (`~/.quick_edit_image.json`).

## Chạy

Cần Python 3.10+ (khi cài nhớ tick "Add python.exe to PATH").

Cách dễ nhất: bấm đúp **`QuickEditImage.bat`**. Lần đầu nó tự cài Pillow, sau đó mở app (không hiện cửa sổ đen). Có thể chuột phải → Send to → Desktop (create shortcut) để mở từ Desktop.

Hoặc chạy bằng terminal trong thư mục dự án:

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

Không chạy trực tiếp `quick_edit_image/app.py` — file này dùng import nội bộ nên sẽ báo lỗi.

## Đóng gói thành file .exe

```bash
pip install pyinstaller
```

```bash
pyinstaller --onefile --windowed --name QuickEditImage run.py
```

File chạy nằm ở `dist/QuickEditImage.exe`.

## Cấu trúc

- `quick_edit_image/core.py` — resize, ghép watermark, đọc clipboard, kiểm tra tên, xuất file.
- `quick_edit_image/app.py` — giao diện Tkinter.
- `run.py` — điểm khởi chạy.
- `QuickEditImage.bat` — bấm đúp để mở app.
