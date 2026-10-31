"""Cac use case cua Quan tri vien.

Quan ly khoa hoc - lop hoc - giao vien - hoc vien - tai khoan
va luong phu "Mo khoa sua diem sau khi da chot".
"""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from extensions import db
from models import (
    CLASS_STATUS,
    ENROLL_STATUS,
    ROLE_ADMIN,
    ROLE_LABELS,
    ROLE_STUDENT,
    ROLE_TEACHER,
    WEEKDAYS,
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
from utils import (
    admin_required,
    band_valid,
    check_schedule_conflict,
    check_teacher_conflict_for_class,
    parse_float,
    parse_int,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/quan-tri")


@admin_bp.before_request
@admin_required
def _guard():
    """Moi route trong blueprint nay deu yeu cau vai tro Quan tri vien."""
    return None


# ============================================================ TRANG CHU


@admin_bp.route("/")
def dashboard():
    stats = {
        "courses": Course.query.count(),
        "open_courses": Course.query.filter_by(is_open=True).count(),
        "classes": ClassRoom.query.count(),
        "teaching_classes": ClassRoom.query.filter(
            ClassRoom.status.in_(["open", "teaching"])
        ).count(),
        "teachers": TeacherProfile.query.count(),
        "students": StudentProfile.query.count(),
        "enrollments": Enrollment.query.filter_by(status="studying").count(),
        "locked_users": User.query.filter_by(is_locked=True).count(),
    }
    pending_resets = PasswordResetRequest.query.filter_by(handled=False).count()
    unassigned = ClassRoom.query.filter(
        ClassRoom.teacher_id.is_(None), ClassRoom.status.in_(["open", "teaching"])
    ).all()
    recent_classes = ClassRoom.query.order_by(ClassRoom.id.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        pending_resets=pending_resets,
        unassigned=unassigned,
        recent_classes=recent_classes,
    )


# ============================================================ KHOA HOC


@admin_bp.route("/khoa-hoc")
def courses():
    keyword = request.args.get("q", "").strip()
    query = Course.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(db.or_(Course.name.ilike(like), Course.code.ilike(like)))
    return render_template(
        "admin/courses.html", courses=query.order_by(Course.code).all(), keyword=keyword
    )


@admin_bp.route("/khoa-hoc/them", methods=["GET", "POST"])
@admin_bp.route("/khoa-hoc/<int:course_id>/sua", methods=["GET", "POST"])
def course_form(course_id=None):
    course = db.session.get(Course, course_id) if course_id else None
    if course_id and course is None:
        flash("Không tìm thấy khóa học.", "danger")
        return redirect(url_for("admin.courses"))

    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        entry = parse_float(request.form.get("entry_band"))
        target = parse_float(request.form.get("target_band"))
        sessions = parse_int(request.form.get("sessions"), 0)
        tuition = parse_int(request.form.get("tuition"), 0)

        errors = []
        if not code or not name:
            errors.append("Mã khóa học và tên khóa học là bắt buộc.")
        if not band_valid(entry) or not band_valid(target) or entry is None or target is None:
            errors.append("Band điểm phải nằm trong 0.0 - 9.0 và là bội số của 0.5.")
        elif target <= entry:
            errors.append("Band mục tiêu phải cao hơn band đầu vào.")
        if sessions is None or sessions <= 0:
            errors.append("Số buổi phải lớn hơn 0.")
        duplicate = Course.query.filter(Course.code == code).first()
        if duplicate and (course is None or duplicate.id != course.id):
            errors.append(f"Mã khóa học {code} đã tồn tại.")

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            if course is None:
                course = Course()
                db.session.add(course)
            course.code = code
            course.name = name
            course.entry_band = entry
            course.target_band = target
            course.sessions = sessions
            course.tuition = tuition or 0
            course.description = request.form.get("description", "").strip()
            course.is_open = request.form.get("is_open") == "on"
            db.session.commit()
            flash("Đã lưu khóa học.", "success")
            return redirect(url_for("admin.courses"))

    return render_template("admin/course_form.html", course=course)


@admin_bp.route("/khoa-hoc/<int:course_id>/tuyen-sinh", methods=["POST"])
def course_toggle(course_id):
    """UC Ngung tuyen sinh khoa hoc / mo lai tuyen sinh."""
    course = db.session.get(Course, course_id)
    if course:
        course.is_open = not course.is_open
        db.session.commit()
        flash(
            f"Khóa {course.code}: {'đang tuyển sinh' if course.is_open else 'đã ngừng tuyển sinh'}.",
            "info",
        )
    return redirect(url_for("admin.courses"))


# ============================================================ LOP HOC


@admin_bp.route("/lop-hoc")
def classes():
    status = request.args.get("status", "")
    query = ClassRoom.query
    if status:
        query = query.filter_by(status=status)
    return render_template(
        "admin/classes.html",
        classes=query.order_by(ClassRoom.code).all(),
        status=status,
        class_status=CLASS_STATUS,
    )


@admin_bp.route("/lop-hoc/<int:class_id>/xoa", methods=["POST"])
def class_delete(class_id):
    classroom = db.session.get(ClassRoom, class_id)
    if classroom is None:
        flash("Không tìm thấy lớp học.", "danger")
        return redirect(url_for("admin.classes"))
    if classroom.current_size:
        flash(
            f"Không thể xóa lớp {classroom.code} vì vẫn còn học viên đang học hoặc bảo lưu.",
            "danger",
        )
        return redirect(url_for("admin.classes"))
    if classroom.has_score_history:
        flash(
            f"Không thể xóa lớp {classroom.code} vì lớp đã có lịch sử điểm.",
            "danger",
        )
        return redirect(url_for("admin.classes"))

    class_code = classroom.code
    db.session.delete(classroom)
    db.session.commit()
    flash(f"Đã xóa lớp {class_code}.", "success")
    return redirect(url_for("admin.classes"))


@admin_bp.route("/lop-hoc/them", methods=["GET", "POST"])
@admin_bp.route("/lop-hoc/<int:class_id>/sua", methods=["GET", "POST"])
def class_form(class_id=None):
    classroom = db.session.get(ClassRoom, class_id) if class_id else None
    if class_id and classroom is None:
        flash("Không tìm thấy lớp học.", "danger")
        return redirect(url_for("admin.classes"))

    courses_open = Course.query.order_by(Course.code).all()
    teachers = (
        TeacherProfile.query.join(User).filter(TeacherProfile.is_active.is_(True)).all()
    )

    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        course_id = parse_int(request.form.get("course_id"))
        teacher_id = parse_int(request.form.get("teacher_id"))
        room = request.form.get("room", "").strip()
        max_size = parse_int(request.form.get("max_size"), 20)
        start_date_raw = request.form.get("start_date", "")

        errors = []
        if not code:
            errors.append("Mã lớp là bắt buộc.")
        if not course_id:
            errors.append("Phải chọn khóa học cho lớp (mỗi lớp thuộc đúng một khóa học).")
        if max_size is None or max_size <= 0:
            errors.append("Sĩ số tối đa phải lớn hơn 0.")
        duplicate = ClassRoom.query.filter(ClassRoom.code == code).first()
        if duplicate and (classroom is None or duplicate.id != classroom.id):
            errors.append(f"Mã lớp {code} đã tồn tại.")

        start_date = None
        if start_date_raw:
            try:
                start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Ngày khai giảng không hợp lệ.")

        # Kiem tra trung lich giao vien khi doi giao vien phu trach
        if not errors and classroom is not None and teacher_id:
            conflict = check_teacher_conflict_for_class(classroom, teacher_id)
            if conflict:
                errors.append(conflict)

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            if classroom is None:
                classroom = ClassRoom()
                db.session.add(classroom)
            classroom.code = code
            classroom.course_id = course_id
            classroom.teacher_id = teacher_id
            classroom.room = room
            classroom.max_size = max_size
            classroom.start_date = start_date
            classroom.status = request.form.get("status", "open")
            db.session.commit()
            flash("Đã lưu lớp học.", "success")
            return redirect(url_for("admin.class_detail", class_id=classroom.id))

    return render_template(
        "admin/class_form.html",
        classroom=classroom,
        courses=courses_open,
        teachers=teachers,
        class_status=CLASS_STATUS,
    )


@admin_bp.route("/lop-hoc/<int:class_id>")
def class_detail(class_id):
    classroom = db.session.get(ClassRoom, class_id)
    if classroom is None:
        flash("Không tìm thấy lớp học.", "danger")
        return redirect(url_for("admin.classes"))

    active_enrollments = [e for e in classroom.enrollments if e.status != "stopped"]
    enrolled_ids = [e.student_id for e in classroom.enrollments]
    available_students = (
        StudentProfile.query.join(User)
        .filter(StudentProfile.is_active.is_(True), ~StudentProfile.id.in_(enrolled_ids or [0]))
        .order_by(User.full_name)
        .all()
    )
    return render_template(
        "admin/class_detail.html",
        classroom=classroom,
        active_enrollments=active_enrollments,
        weekdays=WEEKDAYS,
        available_students=available_students,
        enroll_status=ENROLL_STATUS,
    )


@admin_bp.route("/lich-hoc")
def schedule_management():
    schedules = (
        Schedule.query.join(ClassRoom)
        .order_by(Schedule.weekday, Schedule.start_time, ClassRoom.code)
        .all()
    )
    classes = ClassRoom.query.order_by(ClassRoom.code).all()
    return render_template(
        "admin/schedules.html",
        schedules=schedules,
        classes=classes,
        weekdays=WEEKDAYS,
    )


def _save_schedule(schedule, classroom):
    weekday = parse_int(request.form.get("weekday"))
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()

    if weekday is None or not 0 <= weekday < len(WEEKDAYS):
        flash("Ngày học không hợp lệ.", "danger")
        return False

    for value in (start_time, end_time):
        try:
            if datetime.strptime(value, "%H:%M").strftime("%H:%M") != value:
                raise ValueError
        except ValueError:
            flash("Giờ bắt đầu và kết thúc phải đúng định dạng HH:MM.", "danger")
            return False

    conflict = check_schedule_conflict(
        classroom.id,
        weekday,
        start_time,
        end_time,
        room=classroom.room,
        teacher_id=classroom.teacher_id,
        exclude_schedule_id=schedule.id,
    )
    if conflict:
        flash("Không lưu được lịch: " + conflict, "danger")
        return False

    schedule.classroom = classroom
    schedule.weekday = weekday
    schedule.start_time = start_time
    schedule.end_time = end_time
    db.session.add(schedule)
    db.session.commit()
    return True


@admin_bp.route("/lich-hoc/them", methods=["POST"])
def schedule_create():
    class_id = parse_int(request.form.get("class_id"))
    classroom = db.session.get(ClassRoom, class_id) if class_id else None
    if classroom is None:
        flash("Vui lòng chọn một lớp học hợp lệ.", "danger")
        return redirect(url_for("admin.schedule_management"))

    if _save_schedule(Schedule(), classroom):
        flash("Đã thêm buổi học vào thời khóa biểu.", "success")
    return redirect(url_for("admin.schedule_management"))


@admin_bp.route("/lich/<int:schedule_id>/sua", methods=["POST"])
def schedule_update(schedule_id):
    schedule = db.session.get(Schedule, schedule_id)
    if schedule is None:
        flash("Không tìm thấy buổi học.", "danger")
        return redirect(url_for("admin.schedule_management"))

    return_to_detail = "class_id" not in request.form
    class_id = parse_int(request.form.get("class_id"), schedule.class_id)
    classroom = db.session.get(ClassRoom, class_id) if class_id else None
    if classroom is None:
        flash("Vui lòng chọn một lớp học hợp lệ.", "danger")
        destination = (
            url_for("admin.class_detail", class_id=schedule.class_id)
            if return_to_detail
            else url_for("admin.schedule_management")
        )
        return redirect(destination)

    if _save_schedule(schedule, classroom):
        flash("Đã cập nhật buổi học.", "success")
    destination = (
        url_for("admin.class_detail", class_id=schedule.class_id)
        if return_to_detail
        else url_for("admin.schedule_management")
    )
    return redirect(destination)


@admin_bp.route("/lop-hoc/<int:class_id>/lich/them", methods=["POST"])
def schedule_add(class_id):
    """UC Xep thoi khoa bieu - include Kiem tra trung lich giao vien va phong hoc."""
    classroom = db.session.get(ClassRoom, class_id)
    if classroom is None:
        flash("Không tìm thấy lớp học.", "danger")
        return redirect(url_for("admin.classes"))

    if _save_schedule(Schedule(), classroom):
        flash("Đã thêm buổi học vào thời khóa biểu.", "success")
    return redirect(url_for("admin.class_detail", class_id=class_id))


@admin_bp.route("/lich/<int:schedule_id>/xoa", methods=["POST"])
def schedule_delete(schedule_id):
    schedule = db.session.get(Schedule, schedule_id)
    if schedule:
        class_id = schedule.class_id
        db.session.delete(schedule)
        db.session.commit()
        flash("Đã xóa buổi học khỏi thời khóa biểu.", "info")
        return redirect(url_for("admin.class_detail", class_id=class_id))
    return redirect(url_for("admin.classes"))


@admin_bp.route("/lop-hoc/<int:class_id>/trang-thai", methods=["POST"])
def class_status(class_id):
    """UC Dong / huy lop."""
    classroom = db.session.get(ClassRoom, class_id)
    if classroom:
        classroom.status = request.form.get("status", classroom.status)
        db.session.commit()
        flash(f"Lớp {classroom.code}: {classroom.status_label}.", "info")
    return redirect(url_for("admin.class_detail", class_id=class_id))


# ============================================================ GIAO VIEN


@admin_bp.route("/giao-vien")
def teachers():
    keyword = request.args.get("q", "").strip()
    query = TeacherProfile.query.join(User)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.username.ilike(like)))
    return render_template(
        "admin/teachers.html", teachers=query.order_by(User.full_name).all(), keyword=keyword
    )


@admin_bp.route("/giao-vien/them", methods=["GET", "POST"])
@admin_bp.route("/giao-vien/<int:teacher_id>/sua", methods=["GET", "POST"])
def teacher_form(teacher_id=None):
    """UC Them / cap nhat ho so giao vien - include Tao tai khoan."""
    teacher = db.session.get(TeacherProfile, teacher_id) if teacher_id else None
    if teacher_id and teacher is None:
        flash("Không tìm thấy giáo viên.", "danger")
        return redirect(url_for("admin.teachers"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        degree = request.form.get("degree", "").strip()
        ielts_band = parse_float(request.form.get("ielts_band"))
        skills = request.form.get("skills", "").strip()

        errors = []
        if not full_name:
            errors.append("Họ tên là bắt buộc.")
        if not band_valid(ielts_band):
            errors.append("Band IELTS của giáo viên không hợp lệ.")
        if teacher is None:
            if not username:
                errors.append("Tên đăng nhập là bắt buộc.")
            elif User.query.filter_by(username=username).first():
                errors.append(f"Tên đăng nhập {username} đã tồn tại.")

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            if teacher is None:
                user = User(
                    username=username, role=ROLE_TEACHER, full_name=full_name,
                    email=email, phone=phone,
                )
                user.set_password(request.form.get("password") or "123456")
                db.session.add(user)
                db.session.flush()
                teacher = TeacherProfile(user_id=user.id)
                db.session.add(teacher)
                flash("Đã tạo tài khoản giáo viên (mật khẩu mặc định: 123456).", "info")
            else:
                teacher.user.full_name = full_name
                teacher.user.email = email
                teacher.user.phone = phone

            teacher.degree = degree
            teacher.ielts_band = ielts_band
            teacher.skills = skills
            teacher.note = request.form.get("note", "").strip()
            db.session.commit()
            flash("Đã lưu hồ sơ giáo viên.", "success")
            return redirect(url_for("admin.teachers"))

    return render_template("admin/teacher_form.html", teacher=teacher)


@admin_bp.route("/giao-vien/<int:teacher_id>/trang-thai", methods=["POST"])
def teacher_toggle(teacher_id):
    """UC Ngung hoat dong giao vien (khong xoa de giu lich su giang day)."""
    teacher = db.session.get(TeacherProfile, teacher_id)
    if teacher:
        if teacher.is_active and any(
            c.status in ("open", "teaching") for c in teacher.classes
        ):
            flash(
                "Không thể ngừng hoạt động: giáo viên còn lớp đang dạy. "
                "Hãy phân công giáo viên khác trước.",
                "danger",
            )
        else:
            teacher.is_active = not teacher.is_active
            teacher.user.is_locked = not teacher.is_active
            db.session.commit()
            flash("Đã cập nhật trạng thái giáo viên.", "info")
    return redirect(url_for("admin.teachers"))


# ============================================================ HOC VIEN


@admin_bp.route("/hoc-vien")
def students():
    keyword = request.args.get("q", "").strip()
    query = StudentProfile.query.join(User)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(
                User.full_name.ilike(like),
                User.username.ilike(like),
                StudentProfile.code.ilike(like),
            )
        )
    return render_template(
        "admin/students.html", students=query.order_by(User.full_name).all(), keyword=keyword
    )


@admin_bp.route("/hoc-vien/them", methods=["GET", "POST"])
@admin_bp.route("/hoc-vien/<int:student_id>/sua", methods=["GET", "POST"])
def student_form(student_id=None):
    """UC Them / cap nhat ho so hoc vien - include Tao tai khoan va Ghi nhan band dau vao."""
    student = db.session.get(StudentProfile, student_id) if student_id else None
    if student_id and student is None:
        flash("Không tìm thấy học viên.", "danger")
        return redirect(url_for("admin.students"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        code = request.form.get("code", "").strip().upper()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        entry_band = parse_float(request.form.get("entry_band"))
        dob_raw = request.form.get("dob", "")

        errors = []
        if not full_name:
            errors.append("Họ tên là bắt buộc.")
        if not band_valid(entry_band):
            errors.append("Band điểm đầu vào không hợp lệ (0.0 - 9.0, bước 0.5).")
        dob = None
        if dob_raw:
            try:
                dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Ngày sinh không hợp lệ.")
        duplicate_code = StudentProfile.query.filter(StudentProfile.code == code).first()
        if code and duplicate_code and (student is None or duplicate_code.id != student.id):
            errors.append(f"Mã học viên {code} đã tồn tại.")
        if student is None:
            if not username:
                errors.append("Tên đăng nhập là bắt buộc.")
            elif User.query.filter_by(username=username).first():
                errors.append(f"Tên đăng nhập {username} đã tồn tại.")

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            if student is None:
                user = User(
                    username=username, role=ROLE_STUDENT, full_name=full_name,
                    email=email, phone=phone,
                )
                user.set_password(request.form.get("password") or "123456")
                db.session.add(user)
                db.session.flush()
                student = StudentProfile(user_id=user.id)
                db.session.add(student)
                flash("Đã tạo tài khoản học viên (mật khẩu mặc định: 123456).", "info")
            else:
                student.user.full_name = full_name
                student.user.email = email
                student.user.phone = phone

            student.code = code or None
            student.dob = dob
            student.entry_band = entry_band
            student.address = request.form.get("address", "").strip()
            db.session.commit()
            flash("Đã lưu hồ sơ học viên.", "success")
            return redirect(url_for("admin.students"))

    return render_template("admin/student_form.html", student=student)


@admin_bp.route("/hoc-vien/<int:student_id>")
def student_detail(student_id):
    student = db.session.get(StudentProfile, student_id)
    if student is None:
        flash("Không tìm thấy học viên.", "danger")
        return redirect(url_for("admin.students"))

    enrolled_class_ids = [e.class_id for e in student.enrollments]
    open_classes = [
        c
        for c in ClassRoom.query.filter(ClassRoom.status.in_(["open", "teaching"])).all()
        if c.id not in enrolled_class_ids
    ]
    return render_template(
        "admin/student_detail.html",
        student=student,
        open_classes=open_classes,
        enroll_status=ENROLL_STATUS,
    )


def _do_enroll(student, classroom):
    """Xu ly nghiep vu xep lop, tra ve (thong_bao, loai_thong_bao).

    include: Ghi nhan band dau vao, Kiem tra si so va trinh do cua lop.
    """
    if student is None or classroom is None:
        return "Dữ liệu không hợp lệ.", "danger"

    if student.entry_band is None:
        return (
            "Chưa có band điểm kiểm tra đầu vào. "
            "Hãy cập nhật hồ sơ học viên trước khi xếp lớp.",
            "danger",
        )

    if classroom.status in ("cancelled", "finished"):
        return f"Lớp {classroom.code} đã đóng nên không nhận thêm học viên.", "danger"

    if classroom.is_full:
        return f"Lớp {classroom.code} đã đủ sĩ số ({classroom.max_size}).", "danger"

    if student.entry_band < classroom.course.entry_band:
        return (
            f"Band đầu vào {student.entry_band} thấp hơn yêu cầu của khóa "
            f"{classroom.course.code} ({classroom.course.entry_band}).",
            "danger",
        )

    if Enrollment.query.filter_by(student_id=student.id, class_id=classroom.id).first():
        return "Học viên đã có trong lớp này.", "warning"

    db.session.add(Enrollment(student_id=student.id, class_id=classroom.id))
    db.session.commit()
    return f"Đã xếp {student.full_name} vào lớp {classroom.code}.", "success"


@admin_bp.route("/hoc-vien/<int:student_id>/ghi-danh", methods=["POST"])
def enroll(student_id):
    """UC Ghi danh vao khoa hoc + Xep hoc vien vao lop (thao tac tu ho so hoc vien)."""
    student = db.session.get(StudentProfile, student_id)
    class_id = parse_int(request.form.get("class_id"))
    classroom = db.session.get(ClassRoom, class_id) if class_id else None

    message, category = _do_enroll(student, classroom)
    flash(message, category)
    if student is None:
        return redirect(url_for("admin.students"))
    return redirect(url_for("admin.student_detail", student_id=student_id))


@admin_bp.route("/lop-hoc/<int:class_id>/them-hoc-vien", methods=["POST"])
def class_add_student(class_id):
    """UC Xep hoc vien vao lop (thao tac tu trang chi tiet lop)."""
    classroom = db.session.get(ClassRoom, class_id)
    student_id = parse_int(request.form.get("student_id"))
    student = db.session.get(StudentProfile, student_id) if student_id else None

    message, category = _do_enroll(student, classroom)
    flash(message, category)
    return redirect(url_for("admin.class_detail", class_id=class_id))


@admin_bp.route(
    "/lop-hoc/<int:class_id>/hoc-vien/<int:enrollment_id>/xoa", methods=["POST"]
)
def class_remove_student(class_id, enrollment_id):
    """Ngừng ghi danh khỏi lớp nhưng giữ lại lịch sử điểm."""
    classroom = db.session.get(ClassRoom, class_id)
    enrollment = db.session.get(Enrollment, enrollment_id)
    if classroom is None:
        flash("Không tìm thấy lớp học.", "danger")
        return redirect(url_for("admin.classes"))
    if enrollment is None or enrollment.class_id != class_id:
        flash("Không tìm thấy học viên trong lớp này.", "danger")
        return redirect(url_for("admin.class_detail", class_id=class_id))

    enrollment.status = "stopped"
    db.session.commit()
    flash(f"Đã xóa {enrollment.student.full_name} khỏi lớp {classroom.code}.", "success")
    return redirect(url_for("admin.class_detail", class_id=class_id))


@admin_bp.route("/ghi-danh/<int:enrollment_id>/trang-thai", methods=["POST"])
def enrollment_status(enrollment_id):
    """UC Bao luu / ngung hoc (khong xoa du lieu de giu lich su diem)."""
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment:
        new_status = request.form.get("status")
        if new_status in ENROLL_STATUS:
            enrollment.status = new_status
            db.session.commit()
            flash(f"Đã cập nhật: {enrollment.status_label}.", "info")
        return redirect(url_for("admin.student_detail", student_id=enrollment.student_id))
    return redirect(url_for("admin.students"))


# ============================================================ TAI KHOAN


@admin_bp.route("/tai-khoan")
def accounts():
    role = request.args.get("role", "")
    query = User.query
    if role:
        query = query.filter_by(role=role)
    resets = (
        PasswordResetRequest.query.filter_by(handled=False)
        .order_by(PasswordResetRequest.created_at.desc())
        .all()
    )
    return render_template(
        "admin/accounts.html",
        users=query.order_by(User.role, User.username).all(),
        role=role,
        role_labels=ROLE_LABELS,
        resets=resets,
    )


@admin_bp.route("/tai-khoan/them", methods=["GET", "POST"])
def account_form():
    """UC Tao tai khoan (dung cho tai khoan quan tri vien / nhan vien)."""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", ROLE_ADMIN)
        password = request.form.get("password", "") or "123456"

        if not username or not full_name:
            flash("Tên đăng nhập và họ tên là bắt buộc.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Tên đăng nhập đã tồn tại.", "danger")
        elif role not in ROLE_LABELS:
            flash("Vai trò không hợp lệ.", "danger")
        else:
            user = User(
                username=username, full_name=full_name, role=role,
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            if role == ROLE_TEACHER:
                db.session.add(TeacherProfile(user_id=user.id))
            elif role == ROLE_STUDENT:
                db.session.add(StudentProfile(user_id=user.id))
            db.session.commit()
            flash(f"Đã tạo tài khoản {username}.", "success")
            return redirect(url_for("admin.accounts"))

    return render_template("admin/account_form.html", role_labels=ROLE_LABELS)


@admin_bp.route("/tai-khoan/<int:user_id>/vai-tro", methods=["POST"])
def account_role(user_id):
    """UC Gan / sua vai tro."""
    user = db.session.get(User, user_id)
    new_role = request.form.get("role")
    if user and new_role in ROLE_LABELS:
        if user.id == current_user.id:
            flash("Không thể tự đổi vai trò của chính mình.", "danger")
        else:
            user.role = new_role
            if new_role == ROLE_TEACHER and user.teacher is None:
                db.session.add(TeacherProfile(user_id=user.id))
            if new_role == ROLE_STUDENT and user.student is None:
                db.session.add(StudentProfile(user_id=user.id))
            db.session.commit()
            flash(f"Đã đổi vai trò của {user.username} thành {user.role_label}.", "success")
    return redirect(url_for("admin.accounts"))


@admin_bp.route("/tai-khoan/<int:user_id>/khoa", methods=["POST"])
def account_lock(user_id):
    """UC Khoa / mo tai khoan."""
    user = db.session.get(User, user_id)
    if user:
        if user.id == current_user.id:
            flash("Không thể tự khóa tài khoản của chính mình.", "danger")
        else:
            user.is_locked = not user.is_locked
            if not user.is_locked:
                user.failed_logins = 0
            db.session.commit()
            flash(
                f"Tài khoản {user.username} đã {'bị khóa' if user.is_locked else 'được mở khóa'}.",
                "info",
            )
    return redirect(url_for("admin.accounts"))


@admin_bp.route("/tai-khoan/<int:user_id>/dat-lai-mat-khau", methods=["POST"])
def account_reset_password(user_id):
    """UC Dat lai mat khau cho nguoi dung."""
    user = db.session.get(User, user_id)
    if user:
        new_password = request.form.get("new_password") or "123456"
        user.set_password(new_password)
        user.failed_logins = 0
        user.is_locked = False
        for req in PasswordResetRequest.query.filter_by(user_id=user.id, handled=False).all():
            req.handled = True
        db.session.commit()
        flash(f"Đã đặt lại mật khẩu cho {user.username}.", "success")
    return redirect(url_for("admin.accounts"))


# ============================================================ KET QUA HOC TAP


@admin_bp.route("/ket-qua")
def scores():
    published = (
        ScoreRecord.query.filter_by(is_published=True)
        .order_by(ScoreRecord.updated_at.desc())
        .limit(100)
        .all()
    )
    logs = ScoreLog.query.order_by(ScoreLog.changed_at.desc()).limit(30).all()
    return render_template("admin/scores.html", scores=published, logs=logs)


@admin_bp.route("/ket-qua/<int:score_id>/mo-khoa", methods=["POST"])
def score_unlock(score_id):
    """Luong phu <<extend>>: Mo khoa sua diem sau khi da chot."""
    score = db.session.get(ScoreRecord, score_id)
    if score:
        score.is_published = False
        db.session.add(
            ScoreLog(
                score_id=score.id,
                changed_by=current_user.id,
                old_value="Đã chốt",
                new_value="Mở khóa để sửa",
                action="Mở khóa sửa điểm",
            )
        )
        db.session.commit()
        flash("Đã mở khóa. Giáo viên có thể sửa lại điểm.", "info")
    return redirect(url_for("admin.scores"))
