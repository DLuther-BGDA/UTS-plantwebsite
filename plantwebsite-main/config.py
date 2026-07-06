import os

class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application Secret Keys and Security Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_strong_and_unique_secret_key_here")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "a_unique_and_random_salt_for_password_hashing")
    SECURITY_PASSWORD_HASH = os.environ.get("SECURITY_PASSWORD_HASH", 'pbkdf2_sha512')

    # Flask-Security Feature Flags
    SECURITY_REGISTERABLE = False # Users cannot register themselves
    SECURITY_SEND_REGISTER_EMAIL = False # No registration emails sent
    SECURITY_CONFIRMABLE = False # No email confirmation required
    SECURITY_CHANGEABLE = os.environ.get("SECURITY_CHANGEABLE", "True").lower() in ["true", "1", "t"]

    # Mail Server Configuration
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@yourdomain.com")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 465))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "False").lower() in ["true", "1", "t"]
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "True").lower() in ["true", "1", "t"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    #Secret initial password for first-time user setup
    SECRET_INITIAL_PASSWORD = os.environ.get('SECRET_INITIAL_PASSWORD', 'a_very_secret_initial_password_you_must_change')