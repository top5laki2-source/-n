"""Cac use case cua Giao vien: xem lop giang day va quan ly ket qua hoc tap."""
import csv
import io

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from extensions import db
from models import (
    SKILLS,
    WEEKDAYS,
    ClassRoom,
    Enrollment,
    ScoreLog,
    ScoreRecord,
)
from utils import band_valid, parse_float, teacher_required

teacher_bp = Blueprint("teacher", __name__, url_prefix="/giao-vien")

TERMS = ["Đầu vào", "Giữa khóa", "Cuối khóa"]


@teacher_bp.before_request
@teacher_required
def _guard():
    return None


def my_classes():
    """Chi lay cac lop ma giao vien dang dang nhap duoc phan cong."""
    profile = current_user.teacher
    if profile is None:
        return []
    return (
        ClassRoom.query.filter_by(teacher_id=profile.id).order_by(ClassRoom.code).all()
    )


def owns_class(classroom):
    profile = current_user.teacher
    return profile is not None and classroom is not None and classroom.teacher_id == profile.id


# ============================================================ TRANG CHU


@teacher_bp.route("/")
def dashboard():
    """UC Xem danh sach lop duoc phan cong."""
    classes = my_classes()
    total_students = sum(c.current_size for c in classes)
    pending = 0
    for c in classes:
        for e in c.enrollments:
            if e.status != "stopped" and not any(s.is_published for s in e.scores):
                pending += 1
    return render_template(
        "teacher/dashboard.html",
        classes=classes,
        total_students=total_students,
        pending=pending,
    )


@teacher_bp.route("/lich-day")
def schedule():
    """UC Xem lich day ca nhan."""
    classes = my_classes()
    table = {i: [] for i in range(7)}
    for c in classes:
        if c.status in ("cancelled", "finished"):
            continue
        for s in c.schedules:
            table[s.weekday].append((s, c))
    for day in table:
        table[day].sort(key=lambda item: item[0].start_time)
    return render_template("teacher/schedule.html", table=table, weekdays=WEEKDAYS)


# ============================================================ LOP HOC


@teacher_bp.route("/lop/<int:class_id>")
def class_detail(class_id):
    """UC Xem danh sach hoc vien trong lop + Xem tien do ca lop."""
    classroom = db.session.get(ClassRoom, class_id)
    if not owns_class(classroom):
        flash("Bạn không được phân công phụ trách lớp này.", "danger")
        return redirect(url_for("teacher.dashboard"))

    # Tien do ca lop: band trung binh theo tung ky nang (chi tinh diem da chot)
    totals = {key: [] for key, _ in SKILLS}
    overalls = []
    active_enrollments = [
        enrollment for enrollment in classroom.enrollments
        if enrollment.status != "stopped"
    ]
    for enrollment in active_enrollments:
        latest = enrollment.latest_score
        if latest is None:
            continue
        for key, _ in SKILLS:
            value = getattr(latest, key)
            if value is not None:
                totals[key].append(value)
        if latest.overall is not None:
            overalls.append(latest.overall)

    averages = {
        key: (round(sum(values) / len(values), 2) if values else None)
        for key, values in totals.items()
    }
    class_average = round(sum(overalls) / len(overalls), 2) if overalls else None

    return render_template(
        "teacher/class_detail.html",
        classroom=classroom,
        active_enrollments=active_enrollments,
        skills=SKILLS,
        averages=averages,
        class_average=class_average,
        scores_by_term={
            enrollment.id: {
                term: next(
                    (
                        score for score in enrollment.scores
                        if score.term == term and score.is_published
                    ),
                    None,
                )
                for term in TERMS[1:]
            }
            for enrollment in active_enrollments
        },
    )


@teacher_bp.route("/lop/<int:class_id>/hoc-vien/<int:enrollment_id>")
def student_scores(class_id, enrollment_id):
    """Xem chi tiet diem da cong bo cua hoc vien trong lop giao vien phu trach."""
    classroom = db.session.get(ClassRoom, class_id)
    if not owns_class(classroom):
        flash("Bạn không được phân công phụ trách lớp này.", "danger")
        return redirect(url_for("teacher.dashboard"))

    enrollment = Enrollment.query.filter_by(
        id=enrollment_id, class_id=class_id
    ).first()
    if enrollment is None:
        abort(404)

    term_order = {term: index for index, term in enumerate(TERMS)}
    published_scores = sorted(
        (score for score in enrollment.scores if score.is_published),
        key=lambda score: (
            term_order.get(score.term, len(TERMS)),
            score.id,
        ),
    )
    return render_template(
        "teacher/student_scores.html",
        classroom=classroom,
        enrollment=enrollment,
        published_scores=published_scores,
        skills=SKILLS,
    )


# ============================================================ NHAP DIEM


@teacher_bp.route("/lop/<int:class_id>/nhap-diem", methods=["GET", "POST"])
def enter_scores(class_id):
    """UC Nhap diem 4 ky nang - include Tinh band Overall (lam tron 0.5)."""
    classroom = db.session.get(ClassRoom, class_id)
    if not owns_class(classroom):
        flash("Bạn không được phân công phụ trách lớp này.", "danger")
        return redirect(url_for("teacher.dashboard"))

    term = request.args.get("term") or request.form.get("term") or TERMS[1]

    if request.method == "POST":
        saved, blocked, invalid = 0, 0, 0
        for enrollment in classroom.enrollments:
            if enrollment.status not in ("studying", "finished"):
                continue
            prefix = f"e{enrollment.id}_"
            values = {key: parse_float(request.form.get(prefix + key)) for key, _ in SKILLS}

            if all(v is None for v in values.values()) and not request.form.get(
                prefix + "comment"
            ):
                continue
            if any(not band_valid(v) for v in values.values()):
                invalid += 1
                continue

            record = ScoreRecord.query.filter_by(
                enrollment_id=enrollment.id, term=term
            ).first()
            if record and record.is_published:
                blocked += 1
                continue

            old_summary = record.summary if record else "(chưa có)"
            if record is None:
                record = ScoreRecord(enrollment_id=enrollment.id, term=term)
                db.session.add(record)

            for key, _ in SKILLS:
                setattr(record, key, values[key])
            record.comment = request.form.get(prefix + "comment", "").strip()
            record.compute_overall()
            db.session.flush()

            db.session.add(
                ScoreLog(
                    score_id=record.id,
                    changed_by=current_user.id,
                    old_value=old_summary,
                    new_value=record.summary,
                    action="Nhập/sửa điểm",
                )
            )
            saved += 1

        db.session.commit()
        if saved:
            flash(f"Đã lưu điểm cho {saved} học viên (kỳ {term}).", "success")
        if blocked:
            flash(
                f"{blocked} học viên đã chốt điểm nên không sửa được. "
                "Cần quản trị viên mở khóa.",
                "warning",
            )
        if invalid:
            flash(f"{invalid} học viên có điểm không hợp lệ (0.0 - 9.0, bước 0.5).", "danger")
        return redirect(url_for("teacher.enter_scores", class_id=class_id, term=term))

    active_enrollments = [
        enrollment for enrollment in classroom.enrollments
        if enrollment.status != "stopped"
    ]
    records = {}
    for enrollment in active_enrollments:
        records[enrollment.id] = ScoreRecord.query.filter_by(
            enrollment_id=enrollment.id, term=term
        ).first()

    return render_template(
        "teacher/enter_scores.html",
        classroom=classroom,
        active_enrollments=active_enrollments,
        skills=SKILLS,
        terms=TERMS,
        term=term,
        records=records,
    )


@teacher_bp.route("/lop/<int:class_id>/chot-diem", methods=["POST"])
def publish_scores(class_id):
    """UC Chot va cong bo ket qua - include Gui thong bao ket qua cho hoc vien."""
    classroom = db.session.get(ClassRoom, class_id)
    if not owns_class(classroom):
        flash("Bạn không được phân công phụ trách lớp này.", "danger")
        return redirect(url_for("teacher.dashboard"))

    term = request.form.get("term", TERMS[1])
    published, missing = 0, 0
    for enrollment in classroom.enrollments:
        if enrollment.status == "stopped":
            continue
        record = ScoreRecord.query.filter_by(enrollment_id=enrollment.id, term=term).first()
        if record is None or record.overall is None:
            missing += 1
            continue
        if record.is_published:
            continue
        record.is_published = True
        db.session.add(
            ScoreLog(
                score_id=record.id,
                changed_by=current_user.id,
                old_value="Chưa công bố",
                new_value=f"Đã công bố - Overall {record.overall}",
                action="Chốt và công bố kết quả",
            )
        )
        published += 1

    db.session.commit()
    if published:
        flash(
            f"Đã chốt và công bố kết quả kỳ {term} cho {published} học viên. "
            "Học viên đã có thể xem điểm.",
            "success",
        )
    if missing:
        flash(f"{missing} học viên chưa đủ điểm 4 kỹ năng nên chưa chốt được.", "warning")
    return redirect(url_for("teacher.enter_scores", class_id=class_id, term=term))


@teacher_bp.route("/lop/<int:class_id>/xuat-bang-diem")
def export_scores(class_id):
    """UC Xuat bang diem lop (CSV mo duoc bang Excel)."""
    classroom = db.session.get(ClassRoom, class_id)
    if not owns_class(classroom):
        flash("Bạn không được phân công phụ trách lớp này.", "danger")
        return redirect(url_for("teacher.dashboard"))

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Lớp", classroom.code, "Khóa học", classroom.course.name])
    writer.writerow([])
    writer.writerow(
        ["Mã HV", "Họ tên", "Kỳ", "Listening", "Reading", "Writing", "Speaking",
         "Overall", "Nhận xét", "Trạng thái"]
    )
    for enrollment in classroom.enrollments:
        for record in sorted(enrollment.scores, key=lambda r: r.term):
            writer.writerow(
                [
                    enrollment.student.code or "",
                    enrollment.student.full_name,
                    record.term,
                    record.listening, record.reading, record.writing, record.speaking,
                    record.overall,
                    (record.comment or "").replace("\n", " "),
                    "Đã công bố" if record.is_published else "Chưa công bố",
                ]
            )

    output = "﻿" + buffer.getvalue()  # BOM de Excel doc dung tieng Viet
    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=bang-diem-{classroom.code}.csv"
        },
    )
