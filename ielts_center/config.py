"""Cau hinh ung dung."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ielts-center-secret-key-doi-khi-trien-khai")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "ielts_center.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # So lan dang nhap sai toi da truoc khi khoa tai khoan
    MAX_LOGIN_FAILED = 5

    # Ten trung tam hien thi tren giao dien
    CENTER_NAME = "TRUNG TÂM ANH NGỮ IELTS"
