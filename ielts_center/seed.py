"""Tao du lieu mau de chay thu he thong.

Chay:  python seed.py
Lenh nay se XOA sach du lieu cu roi tao lai tu dau.
"""
from datetime import date, datetime, timedelta

from app import create_app
from extensions import db
from models import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ClassRoom,
    Course,
    Enrollment,
    PasswordResetRequest,
    Schedule,
    ScoreLog,
    ScoreRecord,
    StudentProfile,
    TeacherProfile,
    User,
)

DEFAULT_PASSWORD = "123456"


def make_user(username, full_name, role, email=None, phone=None):
    user = User(
        username=username,
        full_name=full_name,
        role=role,
        email=email or f"{username}@ielts-center.vn",
        phone=phone,
    )
    user.set_password(DEFAULT_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---------------------------------------------------- tai khoan quan tri
        make_user("admin", "Nguyễn Quản Trị", ROLE_ADMIN, phone="0901000001")

        # ---------------------------------------------------- giao vien
        teacher_data = [
            ("gv.mai", "Trần Thị Mai", "Cử nhân Sư phạm Anh, TESOL", 8.0, "Writing, Speaking", "0912000001"),
            ("gv.hung", "Lê Quang Hùng", "Thạc sĩ Ngôn ngữ Anh", 8.5, "Reading, Listening", "0912000002"),
            ("gv.lan", "Phạm Ngọc Lan", "Cử nhân Ngôn ngữ Anh, CELTA", 7.5, "Speaking, Listening", "0912000003"),
        ]
        teachers = {}
        for username, name, degree, band, skills, phone in teacher_data:
            user = make_user(username, name, ROLE_TEACHER, phone=phone)
            profile = TeacherProfile(
                user_id=user.id, degree=degree, ielts_band=band, skills=skills
            )
            db.session.add(profile)
            db.session.flush()
            teachers[username] = profile

        # ---------------------------------------------------- khoa hoc
        courses = {
            "found": Course(
                code="IELTS-FOUND", name="IELTS Foundation 3.0 lên 4.5",
                entry_band=3.0, target_band=4.5, sessions=30, tuition=5500000,
                description="Dành cho học viên mất gốc, xây nền ngữ pháp và từ vựng học thuật.",
            ),
            "inter": Course(
                code="IELTS-5065", name="IELTS 5.0 lên 6.5",
                entry_band=5.0, target_band=6.5, sessions=36, tuition=8000000,
                description="Luyện đủ 4 kỹ năng theo format đề thi, có bài kiểm tra giữa và cuối khóa.",
            ),
            "adv": Course(
                code="IELTS-6575", name="IELTS 6.5 lên 7.5+",
                entry_band=6.5, target_band=7.5, sessions=24, tuition=11000000,
                description="Lớp nâng cao, tập trung Writing Task 2 và Speaking Part 3.",
            ),
        }
        for course in courses.values():
            db.session.add(course)
        db.session.flush()

        # ---------------------------------------------------- lop hoc
        today = date.today()
        classes = {
            "a1": ClassRoom(
                code="IELTS-A1", course_id=courses["inter"].id,
                teacher_id=teachers["gv.mai"].id, room="P.201",
                start_date=today - timedelta(days=30), max_size=18, status="teaching",
            ),
            "a2": ClassRoom(
                code="IELTS-A2", course_id=courses["inter"].id,
                teacher_id=teachers["gv.hung"].id, room="P.202",
                start_date=today - timedelta(days=10), max_size=16, status="teaching",
            ),
            "f1": ClassRoom(
                code="IELTS-F1", course_id=courses["found"].id,
                teacher_id=teachers["gv.lan"].id, room="P.101",
                start_date=today + timedelta(days=7), max_size=20, status="open",
            ),
            "b1": ClassRoom(
                code="IELTS-B1", course_id=courses["adv"].id,
                teacher_id=None, room="P.301",
                start_date=today + timedelta(days=14), max_size=12, status="open",
            ),
        }
        for classroom in classes.values():
            db.session.add(classroom)
        db.session.flush()

        # ---------------------------------------------------- thoi khoa bieu
        schedule_data = [
            ("a1", 0, "18:00", "20:00"), ("a1", 2, "18:00", "20:00"), ("a1", 4, "18:00", "20:00"),
            ("a2", 1, "18:00", "20:00"), ("a2", 3, "18:00", "20:00"),
            ("f1", 5, "08:00", "10:00"), ("f1", 6, "08:00", "10:00"),
            ("b1", 1, "20:00", "21:30"),
        ]
        for key, weekday, start, end in schedule_data:
            db.session.add(
                Schedule(class_id=classes[key].id, weekday=weekday, start_time=start, end_time=end)
            )

        # ---------------------------------------------------- hoc vien
        student_data = [
            ("hv.an", "Nguyễn Văn An", "HV001", 5.0, "0987000001", date(2004, 5, 12)),
            ("hv.binh", "Trần Thị Bình", "HV002", 5.5, "0987000002", date(2003, 8, 3)),
            ("hv.cuong", "Lê Mạnh Cường", "HV003", 5.0, "0987000003", date(2005, 1, 20)),
            ("hv.dung", "Phạm Thùy Dung", "HV004", 6.0, "0987000004", date(2002, 11, 9)),
            ("hv.giang", "Đỗ Hương Giang", "HV005", 5.5, "0987000005", date(2004, 2, 27)),
            ("hv.hoa", "Vũ Thanh Hòa", "HV006", 3.5, "0987000006", date(2006, 6, 15)),
            ("hv.khanh", "Bùi Gia Khánh", "HV007", 3.0, "0987000007", date(2006, 9, 1)),
            ("hv.linh", "Ngô Khánh Linh", "HV008", 6.5, "0987000008", date(2001, 4, 18)),
        ]
        students = {}
        for username, name, code, band, phone, dob in student_data:
            user = make_user(username, name, ROLE_STUDENT, phone=phone)
            profile = StudentProfile(
                user_id=user.id, code=code, entry_band=band, dob=dob,
                address="TP. Hồ Chí Minh",
            )
            db.session.add(profile)
            db.session.flush()
            students[username] = profile

        # ---------------------------------------------------- ghi danh
        enroll_map = {
            "a1": ["hv.an", "hv.binh", "hv.cuong", "hv.giang"],
            "a2": ["hv.dung", "hv.linh"],
            "f1": ["hv.hoa", "hv.khanh"],
        }
        enrollments = {}
        for class_key, usernames in enroll_map.items():
            for username in usernames:
                enrollment = Enrollment(
                    student_id=students[username].id,
                    class_id=classes[class_key].id,
                    enrolled_at=datetime.now() - timedelta(days=20),
                )
                db.session.add(enrollment)
                db.session.flush()
                enrollments[(class_key, username)] = enrollment

        # ---------------------------------------------------- ket qua hoc tap
        # Lop A1: da co diem giua khoa (da cong bo) va dang nhap diem cuoi khoa
        mid_scores = {
            "hv.an": (5.5, 6.0, 5.0, 5.5, "Listening tiến bộ tốt, Writing cần cải thiện Task 2."),
            "hv.binh": (6.0, 6.5, 5.5, 6.0, "Đọc tốt, cần luyện thêm phát âm khi nói."),
            "hv.cuong": (5.0, 5.5, 5.0, 5.0, "Cần tăng vốn từ vựng học thuật."),
            "hv.giang": (6.0, 6.0, 5.5, 6.5, "Speaking rất tự nhiên, giữ nhịp độ này."),
        }
        for username, (listening, reading, writing, speaking, comment) in mid_scores.items():
            enrollment = enrollments[("a1", username)]
            record = ScoreRecord(
                enrollment_id=enrollment.id, term="Giữa khóa",
                listening=listening, reading=reading, writing=writing, speaking=speaking,
                comment=comment, is_published=True,
                updated_at=datetime.now() - timedelta(days=20),
            )
            record.compute_overall()
            db.session.add(record)
            db.session.flush()
            db.session.add(
                ScoreLog(
                    score_id=record.id, changed_by=teachers["gv.mai"].user_id,
                    old_value="(chưa có)", new_value=record.summary,
                    action="Chốt và công bố kết quả",
                )
            )

        # Lop A1: them ket qua cuoi khoa da cong bo de thay ro tien bo
        final_scores = {
            "hv.an": (6.0, 6.5, 5.5, 6.0, "Đã đạt mục tiêu Listening, tiếp tục giữ nhịp."),
            "hv.binh": (6.5, 7.0, 6.0, 6.5, "Tiến bộ đều ở cả 4 kỹ năng."),
            "hv.cuong": (5.5, 6.0, 5.5, 5.5, "Có tiến bộ nhưng cần luyện Writing nhiều hơn."),
            "hv.giang": (6.5, 6.5, 6.0, 7.0, "Kết quả tốt, đủ điều kiện lên lớp nâng cao."),
        }
        for username, (listening, reading, writing, speaking, comment) in final_scores.items():
            enrollment = enrollments[("a1", username)]
            record = ScoreRecord(
                enrollment_id=enrollment.id, term="Cuối khóa",
                listening=listening, reading=reading, writing=writing, speaking=speaking,
                comment=comment, is_published=True,
                updated_at=datetime.now(),
            )
            record.compute_overall()
            db.session.add(record)
            db.session.flush()
            db.session.add(
                ScoreLog(
                    score_id=record.id, changed_by=teachers["gv.mai"].user_id,
                    old_value="(chưa có)", new_value=record.summary,
                    action="Chốt và công bố kết quả",
                )
            )

        # Lop A2: diem dang nhap do (chua cong bo)
        draft_scores = {
            "hv.dung": (6.5, 6.0, 5.5, 6.0),
            "hv.linh": (7.0, 7.5, 6.5, 7.0),
        }
        for username, (listening, reading, writing, speaking) in draft_scores.items():
            enrollment = enrollments[("a2", username)]
            record = ScoreRecord(
                enrollment_id=enrollment.id, term="Giữa khóa",
                listening=listening, reading=reading, writing=writing, speaking=speaking,
                is_published=False,
            )
            record.compute_overall()
            db.session.add(record)

        # ---------------------------------------------------- yeu cau quen mat khau mau
        db.session.add(PasswordResetRequest(user_id=students["hv.khanh"].user_id))

        db.session.commit()

        print("Đã tạo dữ liệu mẫu thành công.")
        print("---------------------------------------------")
        print("Quản trị viên : admin    / 123456")
        print("Giáo viên     : gv.mai   / 123456  (lớp IELTS-A1)")
        print("                gv.hung  / 123456  (lớp IELTS-A2)")
        print("                gv.lan   / 123456  (lớp IELTS-F1)")
        print("Học viên      : hv.an    / 123456  (đã có điểm giữa khóa)")
        print("                hv.linh  / 123456  (điểm chưa công bố)")
        print("---------------------------------------------")


if __name__ == "__main__":
    seed()
