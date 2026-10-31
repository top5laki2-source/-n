"""Ham dung chung: phan quyen, kiem tra trung lich, tien ich nho."""
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user

from models import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, ClassRoom, Schedule


def role_required(*roles):
    """Chi cho phep cac vai tro duoc liet ke truy cap route."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Vui lòng đăng nhập để tiếp tục.", "warning")
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required(ROLE_ADMIN)
teacher_required = role_required(ROLE_TEACHER)
student_required = role_required(ROLE_STUDENT)


def _to_minutes(hhmm):
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def _overlap(a_start, a_end, b_start, b_end):
    return _to_minutes(a_start) < _to_minutes(b_end) and _to_minutes(b_start) < _to_minutes(a_end)


def check_schedule_conflict(
    class_id, weekday, start_time, end_time, room=None, teacher_id=None,
    exclude_schedule_id=None,
):
    """Kiem tra trung lich giao vien va phong hoc.

    Tra ve chuoi mo ta xung dot, hoac None neu khong trung.
    Day chinh la use case <<include>> "Kiem tra trung lich" trong so do phan ra.
    """
    if _to_minutes(start_time) >= _to_minutes(end_time):
        return "Giờ kết thúc phải sau giờ bắt đầu."

    query = Schedule.query.filter(Schedule.weekday == weekday)
    for other in query.all():
        # Bo qua chinh buoi hoc dang duoc kiem tra lai
        if exclude_schedule_id is not None and other.id == exclude_schedule_id:
            continue

        # Trung gio voi chinh buoi hoc khac cua lop nay
        if other.class_id == class_id:
            if _overlap(start_time, end_time, other.start_time, other.end_time):
                return (
                    f"Lớp đã có buổi học trùng giờ vào {other.weekday_label} "
                    f"{other.start_time}-{other.end_time}."
                )
            continue

        other_class = other.classroom
        if other_class.status in ("cancelled", "finished"):
            continue
        if not _overlap(start_time, end_time, other.start_time, other.end_time):
            continue

        if teacher_id and other_class.teacher_id == teacher_id:
            return (
                f"Giáo viên đã có lịch dạy lớp {other_class.code} "
                f"({other.weekday_label} {other.start_time}-{other.end_time})."
            )
        if room and other_class.room and other_class.room.strip().lower() == room.strip().lower():
            return (
                f"Phòng {room} đã được lớp {other_class.code} sử dụng "
                f"({other.weekday_label} {other.start_time}-{other.end_time})."
            )
    return None


def check_teacher_conflict_for_class(classroom, teacher_id):
    """Khi phan cong giao vien moi, kiem tra toan bo lich cua lop do."""
    for sch in classroom.schedules:
        msg = check_schedule_conflict(
            classroom.id, sch.weekday, sch.start_time, sch.end_time,
            teacher_id=teacher_id, exclude_schedule_id=sch.id,
        )
        if msg:
            return msg
    return None


def parse_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value, default=None):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def band_valid(value):
    """Band IELTS hop le: 0.0 - 9.0, buoc 0.5."""
    if value is None:
        return True
    return 0 <= value <= 9 and (value * 2) == int(value * 2)
