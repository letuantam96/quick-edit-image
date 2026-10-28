# quick-edit-image

Quick edit image tool for Thanh Hang — paste ảnh, tự resize, đóng logo watermark, đặt tên rồi xuất PNG.

## Cách dùng

1. Điền **chiều rộng** (px). Mọi ảnh sẽ được resize về đúng chiều rộng này (phóng to nếu ảnh nhỏ hơn), chiều cao giữ tỉ lệ.
2. Bấm **Đổi…** để chọn watermark (file PNG, nên nền trong suốt). Watermark dùng chung cho tất cả ảnh. Ảnh preview nhỏ của watermark hiện ngay cạnh tên file.
3. Copy ảnh (từ web, Zalo, Photoshop, hoặc copy file trong Explorer) rồi bấm nút **Paste ảnh từ bộ nhớ** (hoặc nhấn **Ctrl+V**) trong app. Ảnh được thêm vào danh sách và có watermark ngay. Nút **Xoá tất cả ảnh** phía trên danh sách xoá hết ảnh (có hỏi lại trước).
4. Kéo watermark để đổi vị trí, kéo 4 góc để phóng to / thu nhỏ. Thumbnail ở danh sách bên trái cập nhật theo ngay. Ảnh paste tiếp theo sẽ dùng vị trí và cỡ watermark của lần chỉnh gần nhất.
5. Gõ **tên file** cho từng ảnh (chọn ảnh ở danh sách bên trái). Bấm icon **thùng rác** ở mỗi dòng (hoặc phím Delete) để bỏ ảnh. Số thứ tự (vd. `2/7`) nằm ngay dưới thùng rác.
6. Chọn thư mục ở thanh dưới, bấm **Xuất vào thư mục** ngay cạnh nút Chọn thư mục. Ảnh chưa đặt tên, trùng tên hoặc tên có ký tự không hợp lệ sẽ nháy đỏ và không xuất cho đến khi sửa.
7. Hoặc bấm **Xuất tự động** (góc dưới bên phải): app xuất vào `Desktop/QuickEditImage/<NămThángNgày-GiờPhútGiây>` (thời điểm mở app, hoặc lúc bấm **Xoá tất cả ảnh** — coi như phiên mới), xoá sạch file cũ trong thư mục đó trước khi xuất, xuất xong tự mở thư mục. Các thư mục tự động cũ hơn 2 tuần được tự xoá khi mở app.

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
