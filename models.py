from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


#Users

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / examiner / student
    is_active = db.Column(db.Boolean, default=True)  # overrides UserMixin's default

    #one-to-one links to the profile tables
    examiner_profile = db.relationship('ExaminerProfile', backref='user', uselist=False)
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ExaminerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    department = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')  # pending / approved / deactivated


class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    roll_number = db.Column(db.String(30))
    department = db.Column(db.String(100))
    contact = db.Column(db.String(20))


#Courses and exams

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active / inactive

    exams = db.relationship('Exam', backref='course', cascade='all, delete-orphan')


class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # assigned by admin
    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(30), nullable=False)  # Viva / Practical / Project Demo / Assessment
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    max_marks = db.Column(db.Integer, nullable=False)

    #timeline
    slot_creation_start = db.Column(db.Date)
    slot_creation_end = db.Column(db.Date)
    booking_start = db.Column(db.Date)
    booking_end = db.Column(db.Date)  # also used as the cancellation deadline

    #admin switches
    slot_creation_open = db.Column(db.Boolean, default=False)
    booking_open = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default='Draft')  # Draft / Slot Creation / Booking Open / Closed / Completed

    examiner = db.relationship('User', foreign_keys=[examiner_id])
    rubrics = db.relationship('Rubric', backref='exam', cascade='all, delete-orphan')
    slots = db.relationship('Slot', backref='exam', cascade='all, delete-orphan')


class Rubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    criterion_name = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Float, default=0)
    description = db.Column(db.Text)


#Slots and bookings

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Available')  # Available / Full / Cancelled / Completed

    examiner = db.relationship('User', foreign_keys=[examiner_id])
    bookings = db.relationship('Booking', backref='slot', cascade='all, delete-orphan')


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)  # makes duplicate check easy
    booking_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='Booked')  # Booked / Cancelled / Completed
    cancelled_at = db.Column(db.DateTime)

    student = db.relationship('User', foreign_keys=[student_id])
    exam = db.relationship('Exam', foreign_keys=[exam_id])
    evaluation = db.relationship('Evaluation', backref='booking', uselist=False, cascade='all, delete-orphan')


#Evaluation

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), unique=True, nullable=False)
    total_marks = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)

    scores = db.relationship('EvaluationScore', backref='evaluation', cascade='all, delete-orphan')


class EvaluationScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluation.id'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('rubric.id'), nullable=False)
    marks = db.Column(db.Float, nullable=False)

    rubric = db.relationship('Rubric')