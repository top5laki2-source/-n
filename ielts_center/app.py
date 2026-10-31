"""Diem khoi chay ung dung Flask - He thong quan ly trung tam IELTS."""
import os

from flask import Flask, render_template

from config import BASE_DIR, Config
from extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Import sau khi khoi tao db de tranh vong lap import
    import models  # noqa: F401
    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.student import student_bp
    from blueprints.teacher import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    @app.context_processor
    def inject_globals():
        return {
            "CENTER_NAME": app.config["CENTER_NAME"],
            "ROLE_LABELS": models.ROLE_LABELS,
        }

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.template_filter("vnd")
    def format_vnd(value):
        try:
            return f"{int(value):,}".replace(",", ".") + " đ"
        except (TypeError, ValueError):
            return value

    @app.template_filter("date_vn")
    def format_date(value):
        return value.strftime("%d/%m/%Y") if value else "—"

    @app.template_filter("datetime_vn")
    def format_datetime(value):
        return value.strftime("%d/%m/%Y %H:%M") if value else "—"

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
