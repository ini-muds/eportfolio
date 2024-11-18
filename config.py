import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'eportfolio.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # アップロード設定
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads', 'attachments')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip'}
    
    # セッション設定
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_PROTECTION = 'strong'
    
    # アプリケーション設定
    RECORDS_PER_PAGE = 10
    MAX_SEARCH_RESULTS = 50
    OPENAI_API_KEY = 'YOUR_OPENAI_API_KEY'