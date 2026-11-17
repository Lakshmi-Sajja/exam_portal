from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import ExaminerProfile, StudentProfile, User, db

auth = Blueprint('auth', __name__)


def go_to_dashboard(user):
    # send each role to its own dashboard
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    if user.role == 'examiner':
        return redirect(url_for('examiner.dashboard'))
    return redirect(url_for('student.dashboard'))


@auth.route('/')
def index():
    if current_user.is_authenticated:
        return go_to_dashboard(current_user)
    return redirect(url_for('auth.login'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('Your account has been deactivated', 'danger')
            return redirect(url_for('auth.login'))

        # examiners can only log in after the admin approves them
        if user.role == 'examiner':
            status = user.examiner_profile.status
            if status == 'pending':
                flash('Your account is waiting for admin approval', 'warning')
                return redirect(url_for('auth.login'))
            if status == 'deactivated':
                flash('Your account has been deactivated', 'danger')
                return redirect(url_for('auth.login'))

        login_user(user)
        return go_to_dashboard(user)

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('This email is already registered', 'danger')
            return redirect(url_for('auth.register_student'))

        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('auth.register_student'))

        user = User(name=name, email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()  # commit first so user.id exists

        profile = StudentProfile(
            user_id=user.id,
            roll_number=request.form['roll_number'].strip(),
            department=request.form['department'].strip(),
            contact=request.form['contact'].strip(),
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_student.html')


@auth.route('/register/examiner', methods=['GET', 'POST'])
def register_examiner():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('This email is already registered', 'danger')
            return redirect(url_for('auth.register_examiner'))

        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('auth.register_examiner'))

        user = User(name=name, email=email, role='examiner')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # status starts as pending until the admin approves
        profile = ExaminerProfile(
            user_id=user.id,
            department=request.form['department'].strip(),
            contact=request.form['contact'].strip(),
            status='pending',
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration successful. You can log in after the admin approves your account.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_examiner.html')