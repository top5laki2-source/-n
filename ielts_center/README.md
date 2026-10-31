# Hệ thống quản lý trung tâm IELTS

Đề án website quản lý đào tạo cho trung tâm IELTS.
Backend **Python + Flask**, cơ sở dữ liệu **SQLite**, giao diện **HTML + CSS + JavaScript + Bootstrap 5**.

Toàn bộ chức năng được xây đúng theo sơ đồ use case đã thiết kế (3 tác nhân: Quản trị viên, Giáo viên, Học viên).

---

## 1. Cài đặt và chạy

Yêu cầu: Python 3.10 trở lên.

```bash
# 1. Cài thư viện
pip install -r requirements.txt

# 2. Tạo cơ sở dữ liệu và dữ liệu mẫu (chỉ chạy lần đầu)
python seed.py

# 3. Chạy website
python app.py
```

Mở trình duyệt vào **http://127.0.0.1:5000**

Trên Windows có thể nhấn đúp file `run.bat`, trên macOS/Linux chạy `bash run.sh`.

> Bootstrap, Bootstrap Icons và Chart.js đã được đóng gói sẵn trong `static/vendor/`
> nên website chạy được cả khi máy không có Internet.

### Tài khoản dùng thử

| Vai trò | Tên đăng nhập | Mật khẩu | Ghi chú |
|---|---|---|---|
| Quản trị viên | `admin` | `123456` | Toàn quyền |
| Giáo viên | `gv.mai` | `123456` | Phụ trách lớp IELTS-A1 (đã có điểm) |
| Giáo viên | `gv.hung` | `123456` | Phụ trách lớp IELTS-A2 |
| Giáo viên | `gv.lan` | `123456` | Phụ trách lớp IELTS-F1 |
| Học viên | `hv.an` | `123456` | Đã có điểm giữa khóa và cuối khóa |
| Học viên | `hv.linh` | `123456` | Điểm chưa được công bố |

---

## 2. Chức năng theo từng vai trò

### Quản trị viên

| Use case | Chức năng trong web |
|---|---|
| Quản lý khóa học | Tạo, sửa, ngừng/mở tuyển sinh, tra cứu khóa học |
| Quản lý lớp học | Mở lớp thuộc khóa học, phân công giáo viên, xếp thời khóa biểu, đóng/hủy lớp, xóa lớp chưa có học viên ghi danh, xóa học viên khỏi lớp (giữ lịch sử điểm) |
| Quản lý giáo viên | Thêm hồ sơ (kèm tạo tài khoản), cập nhật, ngừng hoạt động, tra cứu |
| Quản lý học viên | Thêm hồ sơ (kèm tạo tài khoản), ghi danh, xếp lớp, bảo lưu/ngừng học |
| Quản lý tài khoản | Tạo tài khoản, gán vai trò, khóa/mở, đặt lại mật khẩu, duyệt yêu cầu quên mật khẩu |
| Mở khóa sửa điểm | Luồng phụ `<<extend>>`: gỡ khóa bảng điểm đã chốt để giáo viên sửa lại |

### Giáo viên

| Use case | Chức năng trong web |
|---|---|
| Xem lớp giảng dạy | Chỉ thấy các lớp mình được phân công |
| Xem danh sách học viên | Kèm band đầu vào, Overall giữa/cuối khóa và mức tiến bộ; nhấn tên để xem điểm chi tiết theo từng giai đoạn |
| Xem tiến độ cả lớp | Band trung bình từng kỹ năng và Overall của lớp |
| Nhập điểm 4 kỹ năng | Listening / Reading / Writing / Speaking, tự tính Overall |
| Chốt và công bố kết quả | Sau khi chốt, điểm bị khóa; học viên mới nhìn thấy |
| Xuất bảng điểm lớp | Tải file CSV mở được bằng Excel |
| Xem lịch dạy cá nhân | Thời khóa biểu tuần tổng hợp từ các lớp phụ trách |

### Học viên

| Use case | Chức năng trong web |
|---|---|
| Xem khóa học đang mở | Band đầu vào, band mục tiêu, số buổi, học phí |
| Xem chi tiết lớp đang học | Giáo viên, phòng học, thời khóa biểu |
| Xem điểm từng kỹ năng | Chỉ hiển thị kỳ đã được giáo viên công bố |
| Xem biểu đồ tiến bộ | Đường band điểm 4 kỹ năng + Overall qua các kỳ (Chart.js) |
| Xem nhận xét của giáo viên | Kèm theo từng kỳ đánh giá |
| Tải bảng điểm cá nhân | File CSV |

### Dùng chung

Đăng nhập, đăng xuất, đổi mật khẩu, quên mật khẩu (gửi yêu cầu cho quản trị viên).

---

## 3. Ràng buộc nghiệp vụ đã cài đặt

Đây là phần thường bị hỏi khi bảo vệ đồ án:

1. **Tính band Overall theo đúng quy tắc IELTS** — trung bình 4 kỹ năng, phần lẻ `< .25` làm tròn xuống, `< .75` về `.5`, còn lại lên 1 band. Ví dụ 6.125 → 6.0; 6.25 → 6.5; 6.75 → 7.0.
2. **Điểm chỉ nhận bội số của 0.5 trong khoảng 0.0 – 9.0.**
3. **Kiểm tra trùng lịch** khi phân công giáo viên và xếp thời khóa biểu: trùng giờ trong cùng lớp, trùng giáo viên giữa hai lớp, trùng phòng học giữa hai lớp.
4. **Kiểm tra khi xếp lớp**: lớp còn chỗ trống, và band đầu vào của học viên phải đạt yêu cầu của khóa học.
5. **Chốt điểm là khóa điểm** — giáo viên không sửa được nữa, chỉ quản trị viên mở khóa; mọi thay đổi đều ghi vào nhật ký (`ScoreLog`).
6. **Phân quyền theo vai trò** — giáo viên chỉ thao tác trên lớp mình phụ trách, học viên chỉ xem dữ liệu của chính mình, truy cập sai khu vực trả về lỗi 403.
7. **Khóa tài khoản sau 5 lần đăng nhập sai** (luồng phụ `<<extend>>` của use case Đăng nhập).
8. **Không xóa vật lý hồ sơ** giáo viên/học viên — dùng "Ngừng hoạt động" và "Bảo lưu/ngừng học" để giữ lịch sử điểm.
9. **Band mục tiêu phải cao hơn band đầu vào** khi tạo khóa học.

---

## 4. Cấu trúc thư mục

```
ielts_center/
├── app.py                  # Khởi tạo ứng dụng (application factory)
├── config.py               # Cấu hình: SECRET_KEY, đường dẫn SQLite
├── extensions.py           # Khởi tạo SQLAlchemy và Flask-Login
├── models.py               # 10 bảng dữ liệu + hàm làm tròn band IELTS
├── utils.py                # Phân quyền, kiểm tra trùng lịch, kiểm tra band
├── seed.py                 # Tạo dữ liệu mẫu
├── tests_smoke.py          # Kiểm thử tự động toàn bộ luồng
├── requirements.txt
├── blueprints/
│   ├── auth.py             # Đăng nhập, đăng xuất, đổi/quên mật khẩu
│   ├── admin.py            # Chức năng của Quản trị viên
│   ├── teacher.py          # Chức năng của Giáo viên
│   └── student.py          # Chức năng của Học viên
├── templates/              # Giao diện Jinja2
│   ├── base.html           # Layout chung, navbar theo vai trò
│   ├── auth/  admin/  teacher/  student/  errors/
├── static/
│   ├── css/style.css       # CSS tự viết
│   ├── js/main.js          # JS tự viết: lọc bảng, tính Overall trực tiếp, xác nhận thao tác
│   └── vendor/             # Bootstrap, Bootstrap Icons, Chart.js (chạy offline)
└── instance/
    └── ielts_center.db     # File SQLite, tự sinh khi chạy seed.py
```

---

## 5. Cơ sở dữ liệu

10 bảng, quan hệ chính:

```
User (tài khoản)
 ├─1:1─ TeacherProfile ──1:N── ClassRoom
 └─1:1─ StudentProfile ──1:N── Enrollment ──1:N── ScoreRecord ──1:N── ScoreLog

Course ──1:N── ClassRoom ──1:N── Schedule
                    └────1:N──── Enrollment
User ──1:N── PasswordResetRequest
```

- `Course` — khóa học (chương trình đào tạo)
- `ClassRoom` — lớp học (một lần khai giảng của khóa học)
- `Schedule` — buổi học cố định trong tuần của lớp
- `Enrollment` — học viên ghi danh vào lớp
- `ScoreRecord` — điểm một kỳ đánh giá, 4 kỹ năng + Overall
- `ScoreLog` — nhật ký mọi thay đổi điểm

---

## 6. Kiểm thử

```bash
python tests_smoke.py
```

Script chạy qua toàn bộ luồng: quy tắc làm tròn band, bảo vệ route khi chưa đăng nhập,
mọi trang của 3 vai trò, các ràng buộc nghiệp vụ, khóa tài khoản, phân quyền và trang lỗi.

---

## 7. Lưu ý khi nộp bài

- Xóa file `instance/ielts_center.db` rồi chạy lại `python seed.py` nếu muốn dữ liệu sạch.
- Đổi `SECRET_KEY` trong `config.py` nếu triển khai thật.
- Mật khẩu được băm bằng `werkzeug.security` (không lưu dạng văn bản thường).
