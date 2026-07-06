from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy 

bcrypt = Bcrypt()
db = SQLAlchemy() 

def init_app(app):
    """
    Initializes Flask extensions with the Flask app instance.
    This function should be called once in your create_app() function.
    """
    bcrypt.init_app(app)
    db.init_app(app)
