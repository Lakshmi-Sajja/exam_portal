from flask import Flask
from flask_login import LoginManager

from config import Config
from models import db, User

from routes.auth import auth
from routes.admin import admin
from routes.examiner import examiner
from routes.student import student

app = Flask(__name__)
app.config.from_object(Config)

# connect the database and login manager to the app
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # where to send users who are not logged in

# register the blueprints (one per role, plus auth)
app.register_blueprint(auth)
app.register_blueprint(admin)
app.register_blueprint(examiner)
app.register_blueprint(student)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_admin():
    # the admin is pre-seeded, there is no admin registration
    existing = User.query.filter_by(role='admin').first()
    if existing is None:
        new_admin = User(name='Admin', email='admin@emp.com', role='admin')
        new_admin.set_password('admin123')
        db.session.add(new_admin)
        db.session.commit()


# create all tables from models.py, then make sure the admin exists
with app.app_context():
    db.create_all()
    create_admin()


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)