# JokamQuimedit

JOKAM Quick Image Edit for Thanh Hằng — paste ảnh, tự resize, đóng logo watermark, đặt tên rồi xuất JPG nén theo dung lượng chọn trước (mặc định 100KB).

## Cách dùng

1. Điền **chiều rộng** (px, mặc định 700). Mọi ảnh sẽ được resize về đúng chiều rộng này (phóng to nếu ảnh nhỏ hơn), chiều cao giữ tỉ lệ.
2. Điền **dung lượng tối ưu** (KB, mặc định 100): mỗi ảnh JPG xuất ra sẽ được nén để không vượt quá mức này.
3. Bấm **Đổi…** để chọn watermark (file PNG, nên nền trong suốt). Watermark dùng chung cho tất cả ảnh. Ảnh preview nhỏ của watermark hiện ngay cạnh tên file.
4. Copy ảnh (từ web, Zalo, Photoshop, hoặc copy file trong Explorer) rồi bấm nút **Paste ảnh từ bộ nhớ** (hoặc nhấn **Ctrl+V**) trong app. Ảnh được thêm vào danh sách và có watermark ngay. Nút **Xoá tất cả ảnh** phía trên danh sách xoá hết ảnh (có hỏi lại trước).
5. Kéo watermark để đổi vị trí, kéo 4 góc để phóng to / thu nhỏ. Thumbnail ở danh sách bên trái cập nhật theo ngay. Ảnh paste tiếp theo sẽ dùng vị trí và cỡ watermark của lần chỉnh gần nhất.
6. Gõ **tên file** cho từng ảnh (chọn ảnh ở danh sách bên trái). Tên tự chuyển sang dạng `day-la-ten-file` ngay khi gõ / paste: tiếng Việt bỏ dấu, chữ thường, dấu cách và ký tự đặc biệt thành `-`. Bấm icon **thùng rác** ở mỗi dòng (hoặc phím Delete) để bỏ ảnh. Số thứ tự (vd. `2/7`) nằm ngay dưới thùng rác.
7. Ảnh xuất ra là **JPG**, app tự chọn chất lượng cao nhất mà file vẫn không vượt dung lượng tối ưu (phần trong suốt thành nền trắng). Ảnh quá chi tiết không nén xuống được sẽ được báo ở thanh trạng thái. Sau khi xuất, mỗi dòng ở danh sách hiện dung lượng file (xanh nếu đạt, đỏ nếu vượt); chỉnh lại ảnh thì dòng này ẩn đi cho tới lần xuất sau. Chọn thư mục ở thanh dưới, bấm **Xuất vào thư mục** ngay cạnh nút Chọn thư mục. Ảnh chưa đặt tên, hoặc trùng tên sẽ nháy đỏ và không xuất cho đến khi sửa.
8. Hoặc bấm **Xuất tự động** (góc dưới bên phải): app xuất vào `Desktop/JokamQuimedit/<NămThángNgày-GiờPhútGiây>` (thời điểm mở app, hoặc lúc bấm **Xoá tất cả ảnh** — coi như phiên mới), xoá sạch file cũ trong thư mục đó trước khi xuất, xuất xong tự mở thư mục. Các thư mục tự động cũ hơn 2 tuần được tự xoá khi mở app.

App nhớ chiều rộng, dung lượng tối ưu, watermark, thư mục xuất, vị trí watermark và vị trí / kích thước cửa sổ (kể cả đang phóng to toàn màn hình) cho lần mở sau (`~/.quick_edit_image.json`). Lần đầu chạy trên máy mới: chiều rộng 700, dung lượng 100KB, chưa có watermark, cửa sổ nằm giữa màn hình (cũng nằm giữa nếu vị trí cũ thuộc màn hình phụ đã rút ra).

## Chạy

Cần Python 3.10+ (khi cài nhớ tick "Add python.exe to PATH").

Cách dễ nhất: bấm đúp **`JokamQuimedit.bat`**. Lần đầu nó tự cài Pillow, sau đó mở app (không hiện cửa sổ đen). Có thể chuột phải → Send to → Desktop (create shortcut) để mở từ Desktop.

Hoặc chạy bằng terminal trong thư mục dự án:

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

Không chạy trực tiếp `quick_edit_image/app.py` — file này dùng import nội bộ nên sẽ báo lỗi.

## Đóng gói để gửi sang máy khác

Bấm đúp **`build.bat`** (lần đầu tự cài PyInstaller). Đầu tiên nó hiện phiên bản hiện tại (góc phải toolbar, vd. `v1.0.0`) và hỏi có lên phiên bản mới không:

1. Giữ nguyên
2. Sửa lỗi nhỏ: `1.0.0` → `1.0.1`
3. Thêm tính năng: `1.0.0` → `1.1.0`
4. Thay đổi lớn: `1.0.0` → `2.0.0`

Kết quả:

- `dist/JokamQuimedit/` — thư mục app, chạy bằng `JokamQuimedit.exe` bên trong.
- `dist/JokamQuimedit-<phiên bản>.zip` (vd. `JokamQuimedit-1.0.1.zip`) — bản nén của thư mục trên, dùng để gửi đi.

Nếu đã lên phiên bản mới, nhớ commit file `quick_edit_image/__init__.py` (nơi lưu số phiên bản).

Build dạng thư mục (không phải 1 file .exe) để app mở nhanh mỗi lần, không phải tự giải nén.

Trên máy nhận: Windows 10/11 64-bit, không cần cài Python. Giải nén `.zip`, mở `JokamQuimedit.exe` (chuột phải → Send to → Desktop để tạo shortcut). Lần đầu Windows SmartScreen có thể cảnh báo vì app chưa ký số: bấm *More info* → *Run anyway*.

## Cấu trúc

- `quick_edit_image/core.py` — resize, ghép watermark, đọc clipboard, kiểm tra tên, xuất file.
- `quick_edit_image/app.py` — giao diện Tkinter.
- `quick_edit_image/assets/` — icon app (`icon.ico`, `icon.png`).
- `run.py` — điểm khởi chạy.
- `JokamQuimedit.bat` — bấm đúp để mở app.
- `build.bat` — hỏi lên phiên bản rồi đóng gói ra `dist/JokamQuimedit-<phiên bản>.zip`.
- `bump_version.py` — đọc / tăng số phiên bản, `build.bat` dùng.
