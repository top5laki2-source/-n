"""Cac bang du lieu cua he thong quan ly trung tam IELTS."""
import math
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager

# ---------------------------------------------------------------- hang so

ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"

ROLE_LABELS = {
    ROLE_ADMIN: "Quản trị viên",
    ROLE_TEACHER: "Giáo viên",
    ROLE_STUDENT: "Học viên",
}

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

CLASS_STATUS = {
    "open": "Đang mở",
    "teaching": "Đang dạy",
    "finished": "Đã kết thúc",
    "cancelled": "Đã hủy",
}

ENROLL_STATUS = {
    "studying": "Đang học",
    "reserved": "Bảo lưu",
    "finished": "Hoàn thành",
    "stopped": "Đã nghỉ",
}

SKILLS = [
    ("listening", "Listening"),
    ("reading", "Reading"),
    ("writing", "Writing"),
    ("speaking", "Speaking"),
]


def ielts_round(value):
    """Lam tron diem theo quy tac IELTS: .25 -> .5 ; .75 -> len 1 band."""
    if value is None:
        return None
    whole = math.floor(value)
    frac = value - whole
    if frac < 0.25:
        return float(whole)
    if frac < 0.75:
        return whole + 0.5
    return float(whole + 1)


# ---------------------------------------------------------------- tai khoan


class User(UserMixin, db.Model):
    """Tai khoan dang nhap. Moi tai khoan gan dung mot vai tro."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))

    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    teacher = db.relationship(
        "TeacherProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    student = db.relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # -- mat khau
    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    # -- vai tro
    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_teacher(self):
        return self.role == ROLE_TEACHER

    @property
    def is_student(self):
        return self.role == ROLE_STUDENT

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class PasswordResetRequest(db.Model):
    """Yeu cau quen mat khau, quan tri vien se xu ly thu cong."""

    __tablename__ = "password_reset_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    handled = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User")


# ---------------------------------------------------------------- ho so


class TeacherProfile(db.Model):
    """Ho so nghiep vu cua giao vien."""

    __tablename__ = "teacher_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    degree = db.Column(db.String(150))          # bang cap
    ielts_band = db.Column(db.Float)            # band IELTS cua giao vien
    skills = db.Column(db.String(150))          # ky nang dam nhiem
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    note = db.Column(db.Text)

    user = db.relationship("User", back_populates="teacher")
    classes = db.relationship("ClassRoom", back_populates="teacher")

    @property
    def full_name(self):
        return self.user.full_name


class StudentProfile(db.Model):
    """Ho so nghiep vu cua hoc vien."""

    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    code = db.Column(db.String(20), unique=True)   # ma hoc vien
    dob = db.Column(db.Date)
    address = db.Column(db.String(200))
    entry_band = db.Column(db.Float)               # band kiem tra dau vao
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship("User", back_populates="student")
    enrollments = db.relationship(
        "Enrollment", back_populates="student", cascade="all, delete-orphan"
    )

    @property
    def full_name(self):
        return self.user.full_name


# ---------------------------------------------------------------- dao tao


class Course(db.Model):
    """Khoa hoc = chuong trinh dao tao (vi du IELTS 5.0 len 6.5, 36 buoi)."""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    entry_band = db.Column(db.Float, nullable=False)
    target_band = db.Column(db.Float, nullable=False)
    sessions = db.Column(db.Integer, nullable=False, default=36)
    tuition = db.Column(db.Integer, nullable=False, default=0)   # hoc phi (VND)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text)

    classes = db.relationship("ClassRoom", back_populates="course")

    @property
    def tuition_display(self):
        return f"{self.tuition:,}".replace(",", ".") + " đ"


class ClassRoom(db.Model):
    """Lop hoc = mot lan khai giang cu the cua mot khoa hoc."""

    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher_profiles.id"))

    room = db.Column(db.String(30))
    start_date = db.Column(db.Date)
    max_size = db.Column(db.Integer, default=20, nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)

    course = db.relationship("Course", back_populates="classes")
    teacher = db.relationship("TeacherProfile", back_populates="classes")
    schedules = db.relationship(
        "Schedule", back_populates="classroom", cascade="all, delete-orphan"
    )
    enrollments = db.relationship(
        "Enrollment", back_populates="classroom", cascade="all, delete-orphan"
    )

    @property
    def status_label(self):
        return CLASS_STATUS.get(self.status, self.status)

    @property
    def current_size(self):
        return len([e for e in self.enrollments if e.status in ("studying", "reserved")])

    @property
    def has_score_history(self):
        return any(enrollment.scores for enrollment in self.enrollments)

    @property
    def is_full(self):
        return self.current_size >= self.max_size

    @property
    def schedule_display(self):
        if not self.schedules:
            return "Chưa xếp lịch"
        return " | ".join(
            f"{WEEKDAYS[s.weekday]} {s.start_time}-{s.end_time}" for s in self.schedules
        )


class Schedule(db.Model):
    """Mot buoi hoc co dinh trong tuan cua lop."""

    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    weekday = db.Column(db.Integer, nullable=False)      # 0 = Thu 2
    start_time = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    end_time = db.Column(db.String(5), nullable=False)

    classroom = db.relationship("ClassRoom", back_populates="schedules")

    @property
    def weekday_label(self):
        return WEEKDAYS[self.weekday]


class Enrollment(db.Model):
    """Ghi danh cua mot hoc vien vao mot lop hoc."""

    __tablename__ = "enrollments"
    __table_args__ = (db.UniqueConstraint("student_id", "class_id", name="uq_student_class"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default="studying", nullable=False)

    student = db.relationship("StudentProfile", back_populates="enrollments")
    classroom = db.relationship("ClassRoom", back_populates="enrollments")
    scores = db.relationship(
        "ScoreRecord", back_populates="enrollment", cascade="all, delete-orphan"
    )

    @property
    def status_label(self):
        return ENROLL_STATUS.get(self.status, self.status)

    @property
    def latest_score(self):
        published = [s for s in self.scores if s.is_published]
        if not published:
            return None
        return sorted(published, key=lambda s: s.updated_at or datetime.min)[-1]


# ---------------------------------------------------------------- ket qua


class ScoreRecord(db.Model):
    """Ket qua mot ky danh gia cua hoc vien trong lop, cham theo 4 ky nang."""

    __tablename__ = "score_records"

    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollments.id"), nullable=False)
    term = db.Column(db.String(50), nullable=False)   # vi du: Dau vao / Giua khoa / Cuoi khoa

    listening = db.Column(db.Float)
    reading = db.Column(db.Float)
    writing = db.Column(db.Float)
    speaking = db.Column(db.Float)
    overall = db.Column(db.Float)

    comment = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    enrollment = db.relationship("Enrollment", back_populates="scores")
    logs = db.relationship("ScoreLog", back_populates="score", cascade="all, delete-orphan")

    def compute_overall(self):
        """Tinh band Overall = trung binh 4 ky nang, lam tron theo quy tac IELTS."""
        parts = [self.listening, self.reading, self.writing, self.speaking]
        if any(p is None for p in parts):
            self.overall = None
        else:
            self.overall = ielts_round(sum(parts) / 4)
        return self.overall

    @property
    def summary(self):
        return (
            f"L={self.listening} R={self.reading} "
            f"W={self.writing} S={self.speaking} Overall={self.overall}"
        )


class ScoreLog(db.Model):
    """Nhat ky thay doi diem, phuc vu doi chieu khi co khieu nai."""

    __tablename__ = "score_logs"

    id = db.Column(db.Integer, primary_key=True)
    score_id = db.Column(db.Integer, db.ForeignKey("score_records.id"), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    changed_at = db.Column(db.DateTime, default=datetime.now)
    old_value = db.Column(db.String(255))
    new_value = db.Column(db.String(255))
    action = db.Column(db.String(50), default="Sửa điểm")

    score = db.relationship("ScoreRecord", back_populates="logs")
    user = db.relationship("User")
