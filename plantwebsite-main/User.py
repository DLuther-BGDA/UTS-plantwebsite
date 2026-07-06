from extensions import bcrypt, db
from itsdangerous import URLSafeTimedSerializer
from flask_security import UserMixin
from flask import current_app 

class User(UserMixin, db.Model):
    """
    Represents a user in the application.
    Integrates with Flask-Security for user management.
    """


    __tablename__ = "users" 

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    write_permission = db.Column(db.Boolean, nullable=False, default=False)
    role = db.Column(db.String(80), nullable=False, default="user")

    def __repr__(self):
        """String representation of a User object."""
        return f"<User {self.email}>"

    def set_password(self, new_pwd):
        """Hashes and sets the user's password."""
        self.password = bcrypt.generate_password_hash(new_pwd).decode('utf-8')

    def verify_password(self, verify_pwd):
        """Verifies a given password against the stored hash."""
        # If password is None (for new users who haven't set it), verification fails.
        if self.password is None:
            return False
        return bcrypt.check_password_hash(self.password, verify_pwd)

    def is_admin(self):
        """Checks if the user has Administrator role."""
        return self.role == "Administrator"

    def toggle_write_perm(self):
        """Toggles the user's write permission."""
        self.write_permission = not self.write_permission

    def generate_token(self, app_instance, email):
        """Generates a URL-safe, timed token for purposes like password reset."""
        serialiser = URLSafeTimedSerializer(app_instance.config["SECRET_KEY"])
        return serialiser.dumps(email, salt=app_instance.config["SECURITY_PASSWORD_SALT"])

    @staticmethod
    def confirm_token(app_instance, token, expiration=1800):
        """
        Confirms and loads data from a URL-safe, timed token.
        Returns the data (e.g., email) if valid and not expired, otherwise False.
        """
        serialiser = URLSafeTimedSerializer(app_instance.config["SECRET_KEY"])
        try:
            email = serialiser.loads(
                token, salt=app_instance.config["SECURITY_PASSWORD_SALT"], max_age=expiration
            )
            return email
        except Exception:
            # Token is invalid or expired.
            return False