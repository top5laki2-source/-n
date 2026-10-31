"""Use case: Dang nhap, Dang xuat, Doi mat khau, Quen mat khau."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import PasswordResetRequest, User

auth_bp = Blueprint("auth", __name__)


def home_for(user):
    """Dieu huong ve trang chu tuong ung voi vai tro."""
    if user.is_admin:
        return url_for("admin.dashboard")
    if user.is_teacher:
        return url_for("teacher.dashboard")
    return url_for("student.dashboard")


@auth_bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(home_for(current_user))
    return redirect(url_for("auth.login"))


@auth_bp.route("/dang-nhap", methods=["GET", "POST"])
def login():
    """UC Dang nhap - include Xac thuc tai khoan va xac dinh vai tro.

    Luong phu <<extend>>: khoa tai khoan sau N lan dang nhap sai.
    """
    if current_user.is_authenticated:
        return redirect(home_for(current_user))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            if user is not None:
                user.failed_logins += 1
                max_failed = current_app.config["MAX_LOGIN_FAILED"]
                if user.failed_logins >= max_failed and not user.is_admin:
                    user.is_locked = True
                    flash(
                        f"Tài khoản đã bị khóa do đăng nhập sai {max_failed} lần. "
                        "Vui lòng liên hệ quản trị viên.",
                        "danger",
                    )
                else:
                    remain = max_failed - user.failed_logins
                    flash(
                        f"Sai tên đăng nhập hoặc mật khẩu. Còn {max(remain, 0)} lần thử.",
                        "danger",
                    )
                db.session.commit()
            else:
                flash("Sai tên đăng nhập hoặc mật khẩu.", "danger")
            return render_template("auth/login.html", username=username)

        if user.is_locked:
            flash("Tài khoản đang bị khóa. Vui lòng liên hệ quản trị viên.", "danger")
            return render_template("auth/login.html", username=username)

        user.failed_logins = 0
        db.session.commit()
        login_user(user)
        flash(f"Xin chào {user.full_name}!", "success")
        next_url = request.args.get("next")
        return redirect(next_url or home_for(user))

    return render_template("auth/login.html", username="")


@auth_bp.route("/dang-xuat")
@login_required
def logout():
    """UC Dang xuat."""
    logout_user()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/doi-mat-khau", methods=["GET", "POST"])
@login_required
def change_password():
    """UC Doi mat khau."""
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not current_user.check_password(old):
            flash("Mật khẩu hiện tại không đúng.", "danger")
        elif len(new) < 6:
            flash("Mật khẩu mới phải có ít nhất 6 ký tự.", "danger")
        elif new != confirm:
            flash("Xác nhận mật khẩu không khớp.", "danger")
        else:
            current_user.set_password(new)
            db.session.commit()
            flash("Đổi mật khẩu thành công.", "success")
            return redirect(home_for(current_user))

    return render_template("auth/change_password.html")


@auth_bp.route("/quen-mat-khau", methods=["GET", "POST"])
def forgot_password():
    """UC Quen mat khau (<<extend>> cua Dang nhap).

    Gui yeu cau den quan tri vien, quan tri vien se dat lai mat khau.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        user = User.query.filter_by(username=username).first()

        if user and (user.email or "").lower() == email.lower() and email:
            existing = PasswordResetRequest.query.filter_by(
                user_id=user.id, handled=False
            ).first()
            if not existing:
                db.session.add(PasswordResetRequest(user_id=user.id))
                db.session.commit()
            flash(
                "Đã gửi yêu cầu đặt lại mật khẩu. Quản trị viên sẽ liên hệ với bạn.",
                "success",
            )
            return redirect(url_for("auth.login"))
        flash("Tên đăng nhập và email không khớp với tài khoản nào.", "danger")

    return render_template("auth/forgot_password.html")
