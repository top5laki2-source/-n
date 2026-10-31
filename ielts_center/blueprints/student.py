"""Cac use case cua Hoc vien: xem thong tin khoa hoc va ket qua - tien do hoc tap."""
import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, url_for
from flask_login import current_user

from extensions import db
from models import SKILLS, WEEKDAYS, ClassRoom, Course, Enrollment, ScoreRecord
from utils import student_required

student_bp = Blueprint("student", __name__, url_prefix="/hoc-vien")


@student_bp.before_request
@student_required
def _guard():
    return None


def my_enrollments():
    """Hoc vien chi xem duoc du lieu cua chinh minh."""
    profile = current_user.student
    if profile is None:
        return []
    return (
        Enrollment.query.filter_by(student_id=profile.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )


@student_bp.route("/")
def dashboard():
    enrollments = my_enrollments()
    studying = [e for e in enrollments if e.status == "studying"]
    latest = None
    for enrollment in enrollments:
        score = enrollment.latest_score
        if score and (latest is None or (score.overall or 0) > (latest.overall or 0)):
            latest = score
    return render_template(
        "student/dashboard.html",
        enrollments=enrollments,
        studying=studying,
        latest=latest,
        profile=current_user.student,
    )


@student_bp.route("/khoa-hoc")
def courses():
    """UC Xem danh sach khoa hoc dang mo."""
    open_courses = Course.query.filter_by(is_open=True).order_by(Course.entry_band).all()
    return render_template("student/courses.html", courses=open_courses)


@student_bp.route("/lop/<int:class_id>")
def class_detail(class_id):
    """UC Xem chi tiet lop dang hoc: giao vien, phong, thoi khoa bieu."""
    profile = current_user.student
    enrollment = Enrollment.query.filter_by(
        student_id=profile.id if profile else 0, class_id=class_id
    ).first()
    if enrollment is None or enrollment.status == "stopped":
        flash("Bạn không thuộc lớp học này.", "danger")
        return redirect(url_for("student.dashboard"))

    classroom = db.session.get(ClassRoom, class_id)
    return render_template(
        "student/class_detail.html",
        classroom=classroom,
        enrollment=enrollment,
        weekdays=WEEKDAYS,
    )


@student_bp.route("/ket-qua")
def results():
    """UC Xem diem tung ky nang + Xem bieu do tien bo + Xem nhan xet cua giao vien."""
    enrollments = my_enrollments()
    published = []
    for enrollment in enrollments:
        for record in enrollment.scores:
            if record.is_published:
                published.append((enrollment, record))
    published.sort(key=lambda item: (item[1].updated_at or item[1].id))

    entry_band = current_user.student.entry_band if current_user.student else None

    # Diem dau vao duoc dua vao bieu do lam moc so sanh ban dau
    chart_labels = ["Đầu vào"] + [f"{e.classroom.code} - {r.term}" for e, r in published]
    chart_data = {
        key: [None] + [getattr(r, key) for _, r in published] for key, _ in SKILLS
    }
    chart_data["overall"] = [entry_band] + [r.overall for _, r in published]

    improvement = None
    if entry_band is not None and published:
        last_overall = published[-1][1].overall
        if last_overall is not None:
            improvement = round(last_overall - entry_band, 1)

    return render_template(
        "student/results.html",
        published=published,
        skills=SKILLS,
        chart_labels=chart_labels,
        chart_data=chart_data,
        entry_band=entry_band,
        improvement=improvement,
    )


@student_bp.route("/bang-diem.csv")
def export_transcript():
    """UC Tai bang diem ca nhan."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Học viên", current_user.full_name])
    writer.writerow([])
    writer.writerow(
        ["Lớp", "Khóa học", "Kỳ", "Listening", "Reading", "Writing", "Speaking",
         "Overall", "Nhận xét"]
    )
    for enrollment in my_enrollments():
        for record in enrollment.scores:
            if not record.is_published:
                continue
            writer.writerow(
                [
                    enrollment.classroom.code,
                    enrollment.classroom.course.name,
                    record.term,
                    record.listening, record.reading, record.writing, record.speaking,
                    record.overall,
                    (record.comment or "").replace("\n", " "),
                ]
            )

    output = "﻿" + buffer.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=bang-diem-ca-nhan.csv"},
    )
