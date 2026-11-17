from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from models import db, User, ExaminerProfile, StudentProfile, Course, Exam, Rubric, Slot, Booking
from roles import admin_required


def parse_date(s):
    # converts a form string like '2026-11-17' to a Python date object
    # returns None if the string is empty
    if s:
        return datetime.strptime(s, '%Y-%m-%d').date()
    return None

admin = Blueprint('admin', __name__, url_prefix='/admin')


# ---------------------------------------------------------------------------
# Dashboard  (Step 20)
# ---------------------------------------------------------------------------

@admin.route('/dashboard')
@admin_required
def dashboard():
    total_courses   = Course.query.count()
    total_exams     = Exam.query.count()
    total_examiners = ExaminerProfile.query.filter_by(status='approved').count()
    total_students  = StudentProfile.query.count()
    total_slots     = Slot.query.count()
    total_bookings  = Booking.query.count()
    return render_template(
        'admin/dashboard.html',
        total_courses=total_courses,
        total_exams=total_exams,
        total_examiners=total_examiners,
        total_students=total_students,
        total_slots=total_slots,
        total_bookings=total_bookings,
    )


# ---------------------------------------------------------------------------
# Course management  (Step 9)
# ---------------------------------------------------------------------------

@admin.route('/courses')
@admin_required
def courses():
    all_courses = Course.query.order_by(Course.name).all()
    return render_template('admin/courses.html', courses=all_courses)


@admin.route('/courses/add', methods=['GET', 'POST'])
@admin_required
def add_course():
    if request.method == 'POST':
        code        = request.form.get('code', '').strip()
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        status      = request.form.get('status', 'active')

        if not code or not name:
            flash('Course code and name are required.', 'danger')
            return render_template('admin/course_form.html', action='Add', course=None)

        if Course.query.filter_by(code=code).first():
            flash(f'A course with code "{code}" already exists.', 'danger')
            return render_template('admin/course_form.html', action='Add', course=None)

        new_course = Course(code=code, name=name, description=description, status=status)
        db.session.add(new_course)
        db.session.commit()
        flash('Course added successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', action='Add', course=None)


@admin.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        code        = request.form.get('code', '').strip()
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        status      = request.form.get('status', 'active')

        if not code or not name:
            flash('Course code and name are required.', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        # check uniqueness against other courses
        existing = Course.query.filter_by(code=code).first()
        if existing and existing.id != course.id:
            flash(f'Another course already uses code "{code}".', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        course.code        = code
        course.name        = name
        course.description = description
        course.status      = status
        db.session.commit()
        flash('Course updated successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', action='Edit', course=course)


@admin.route('/courses/<int:course_id>/delete', methods=['POST'])
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.exams:
        flash('Cannot delete a course that has exams. Remove the exams first.', 'danger')
        return redirect(url_for('admin.courses'))
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted.', 'success')
    return redirect(url_for('admin.courses'))


# ---------------------------------------------------------------------------
# Exam management  (Step 10)
# ---------------------------------------------------------------------------

@admin.route('/exams')
@admin_required
def exams():
    all_exams = Exam.query.order_by(Exam.name).all()
    return render_template('admin/exams.html', exams=all_exams)


@admin.route('/exams/add', methods=['GET', 'POST'])
@admin_required
def add_exam():
    courses         = Course.query.order_by(Course.name).all()
    approved_examiners = (
        User.query
        .join(ExaminerProfile, User.id == ExaminerProfile.user_id)
        .filter(ExaminerProfile.status == 'approved')
        .order_by(User.name)
        .all()
    )

    if request.method == 'POST':
        course_id            = request.form.get('course_id')
        examiner_id          = request.form.get('examiner_id') or None
        name                 = request.form.get('name', '').strip()
        exam_type            = request.form.get('exam_type', '')
        duration             = request.form.get('duration', '')
        max_marks            = request.form.get('max_marks', '')
        slot_creation_start  = request.form.get('slot_creation_start') or None
        slot_creation_end    = request.form.get('slot_creation_end') or None
        booking_start        = request.form.get('booking_start') or None
        booking_end          = request.form.get('booking_end') or None
        status               = request.form.get('status', 'Draft')

        if not course_id or not name or not exam_type or not duration or not max_marks:
            flash('Course, name, type, duration and max marks are required.', 'danger')
            return render_template('admin/exam_form.html', action='Add', exam=None,
                                   courses=courses, examiners=approved_examiners)

        new_exam = Exam(
            course_id           = int(course_id),
            examiner_id         = int(examiner_id) if examiner_id else None,
            name                = name,
            exam_type           = exam_type,
            duration            = int(duration),
            max_marks           = int(max_marks),
            slot_creation_start = parse_date(slot_creation_start),
            slot_creation_end   = parse_date(slot_creation_end),
            booking_start       = parse_date(booking_start),
            booking_end         = parse_date(booking_end),
            status              = status,
        )
        db.session.add(new_exam)
        db.session.commit()
        flash('Exam created successfully.', 'success')
        return redirect(url_for('admin.exams'))

    return render_template('admin/exam_form.html', action='Add', exam=None,
                           courses=courses, examiners=approved_examiners)


@admin.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    courses = Course.query.order_by(Course.name).all()
    approved_examiners = (
        User.query
        .join(ExaminerProfile, User.id == ExaminerProfile.user_id)
        .filter(ExaminerProfile.status == 'approved')
        .order_by(User.name)
        .all()
    )

    if request.method == 'POST':
        course_id            = request.form.get('course_id')
        examiner_id          = request.form.get('examiner_id') or None
        name                 = request.form.get('name', '').strip()
        exam_type            = request.form.get('exam_type', '')
        duration             = request.form.get('duration', '')
        max_marks            = request.form.get('max_marks', '')
        slot_creation_start  = request.form.get('slot_creation_start') or None
        slot_creation_end    = request.form.get('slot_creation_end') or None
        booking_start        = request.form.get('booking_start') or None
        booking_end          = request.form.get('booking_end') or None
        status               = request.form.get('status', exam.status)

        if not course_id or not name or not exam_type or not duration or not max_marks:
            flash('Course, name, type, duration and max marks are required.', 'danger')
            return render_template('admin/exam_form.html', action='Edit', exam=exam,
                                   courses=courses, examiners=approved_examiners)

        exam.course_id           = int(course_id)
        exam.examiner_id         = int(examiner_id) if examiner_id else None
        exam.name                = name
        exam.exam_type           = exam_type
        exam.duration            = int(duration)
        exam.max_marks           = int(max_marks)
        exam.slot_creation_start = parse_date(slot_creation_start)
        exam.slot_creation_end   = parse_date(slot_creation_end)
        exam.booking_start       = parse_date(booking_start)
        exam.booking_end         = parse_date(booking_end)
        exam.status              = status
        db.session.commit()
        flash('Exam updated successfully.', 'success')
        return redirect(url_for('admin.exams'))

    return render_template('admin/exam_form.html', action='Edit', exam=exam,
                           courses=courses, examiners=approved_examiners)


@admin.route('/exams/<int:exam_id>/delete', methods=['POST'])
@admin_required
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.slots:
        flash('Cannot delete an exam that has slots. Remove the slots first.', 'danger')
        return redirect(url_for('admin.exams'))
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted.', 'success')
    return redirect(url_for('admin.exams'))


# ---------------------------------------------------------------------------
# Rubric management  (Step 11)
# ---------------------------------------------------------------------------

@admin.route('/exams/<int:exam_id>/rubrics')
@admin_required
def rubrics(exam_id):
    exam         = Exam.query.get_or_404(exam_id)
    all_rubrics  = Rubric.query.filter_by(exam_id=exam_id).all()
    total_rubric_marks = sum(r.max_marks for r in all_rubrics)
    return render_template(
        'admin/rubrics.html',
        exam=exam,
        rubrics=all_rubrics,
        total_rubric_marks=total_rubric_marks,
    )


@admin.route('/exams/<int:exam_id>/rubrics/add', methods=['GET', 'POST'])
@admin_required
def add_rubric(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks      = request.form.get('max_marks', '')
        weightage      = request.form.get('weightage', '0')
        description    = request.form.get('description', '').strip()

        if not criterion_name or not max_marks:
            flash('Criterion name and max marks are required.', 'danger')
            return render_template('admin/rubric_form.html', action='Add', rubric=None, exam=exam)

        new_rubric = Rubric(
            exam_id        = exam_id,
            criterion_name = criterion_name,
            max_marks      = int(max_marks),
            weightage      = float(weightage) if weightage else 0,
            description    = description,
        )
        db.session.add(new_rubric)
        db.session.commit()
        flash('Rubric criterion added.', 'success')
        return redirect(url_for('admin.rubrics', exam_id=exam_id))

    return render_template('admin/rubric_form.html', action='Add', rubric=None, exam=exam)


@admin.route('/rubrics/<int:rubric_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_rubric(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    exam   = rubric.exam

    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks      = request.form.get('max_marks', '')
        weightage      = request.form.get('weightage', '0')
        description    = request.form.get('description', '').strip()

        if not criterion_name or not max_marks:
            flash('Criterion name and max marks are required.', 'danger')
            return render_template('admin/rubric_form.html', action='Edit', rubric=rubric, exam=exam)

        rubric.criterion_name = criterion_name
        rubric.max_marks      = int(max_marks)
        rubric.weightage      = float(weightage) if weightage else 0
        rubric.description    = description
        db.session.commit()
        flash('Rubric criterion updated.', 'success')
        return redirect(url_for('admin.rubrics', exam_id=exam.id))

    return render_template('admin/rubric_form.html', action='Edit', rubric=rubric, exam=exam)


@admin.route('/rubrics/<int:rubric_id>/delete', methods=['POST'])
@admin_required
def delete_rubric(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    exam_id = rubric.exam_id
    db.session.delete(rubric)
    db.session.commit()
    flash('Rubric criterion deleted.', 'success')
    return redirect(url_for('admin.rubrics', exam_id=exam_id))


# ---------------------------------------------------------------------------
# Examiner approval / deactivation  (Step 12)
# ---------------------------------------------------------------------------

@admin.route('/examiners')
@admin_required
def examiners():
    all_examiners = (
        User.query
        .join(ExaminerProfile, User.id == ExaminerProfile.user_id)
        .order_by(User.name)
        .all()
    )
    return render_template('admin/examiners.html', examiners=all_examiners)


@admin.route('/examiners/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_examiner(user_id):
    user    = User.query.get_or_404(user_id)
    profile = ExaminerProfile.query.filter_by(user_id=user_id).first_or_404()
    profile.status   = 'approved'
    user.is_active   = True
    db.session.commit()
    flash(f'{user.name} has been approved.', 'success')
    return redirect(url_for('admin.examiners'))


@admin.route('/examiners/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_examiner(user_id):
    user    = User.query.get_or_404(user_id)
    profile = ExaminerProfile.query.filter_by(user_id=user_id).first_or_404()
    profile.status   = 'deactivated'
    user.is_active   = False
    db.session.commit()
    flash(f'{user.name} has been deactivated.', 'warning')
    return redirect(url_for('admin.examiners'))


# ---------------------------------------------------------------------------
# Toggle slot creation / booking  (Step 13)
# ---------------------------------------------------------------------------

@admin.route('/exams/<int:exam_id>/toggle_slot_creation', methods=['POST'])
@admin_required
def toggle_slot_creation(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    exam.slot_creation_open = not exam.slot_creation_open
    db.session.commit()
    state = 'opened' if exam.slot_creation_open else 'closed'
    flash(f'Slot creation {state} for "{exam.name}".', 'success')
    return redirect(url_for('admin.exams'))


@admin.route('/exams/<int:exam_id>/toggle_booking', methods=['POST'])
@admin_required
def toggle_booking(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    exam.booking_open = not exam.booking_open
    db.session.commit()
    state = 'opened' if exam.booking_open else 'closed'
    flash(f'Booking {state} for "{exam.name}".', 'success')
    return redirect(url_for('admin.exams'))


# ---------------------------------------------------------------------------
# Admin oversight — Slots  (Step 19)
# ---------------------------------------------------------------------------

@admin.route('/slots')
@admin_required
def slots():
    q = request.args.get('q', '').strip()
    query = Slot.query.join(Exam, Slot.exam_id == Exam.id).join(User, Slot.examiner_id == User.id)
    if q:
        query = query.filter(
            db.or_(
                Exam.name.ilike(f'%{q}%'),
                User.name.ilike(f'%{q}%'),
            )
        )
    all_slots = query.order_by(Slot.date, Slot.start_time).all()
    return render_template('admin/slots.html', slots=all_slots, q=q)


# ---------------------------------------------------------------------------
# Admin oversight — Bookings  (Step 19)
# ---------------------------------------------------------------------------

@admin.route('/bookings')
@admin_required
def bookings():
    q = request.args.get('q', '').strip()
    query = (
        Booking.query
        .join(User, Booking.student_id == User.id)
        .join(Exam, Booking.exam_id == Exam.id)
    )
    if q:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{q}%'),
                Exam.name.ilike(f'%{q}%'),
            )
        )
    all_bookings = query.order_by(Booking.booking_date.desc()).all()
    return render_template('admin/bookings.html', bookings=all_bookings, q=q)


@admin.route('/bookings/<int:booking_id>/reschedule', methods=['POST'])
@admin_required
def reschedule_booking(booking_id):
    booking      = Booking.query.get_or_404(booking_id)
    new_slot_id  = request.form.get('new_slot_id', '').strip()

    if not new_slot_id:
        flash('New slot ID is required.', 'danger')
        return redirect(url_for('admin.bookings'))

    new_slot = Slot.query.get(int(new_slot_id))
    if not new_slot:
        flash('The specified slot does not exist.', 'danger')
        return redirect(url_for('admin.bookings'))

    if new_slot.available_seats <= 0:
        flash('The selected slot has no available seats.', 'danger')
        return redirect(url_for('admin.bookings'))

    old_slot = booking.slot

    # restore a seat to the old slot
    old_slot.available_seats += 1
    if old_slot.status == 'Full':
        old_slot.status = 'Available'

    # occupy a seat in the new slot
    new_slot.available_seats -= 1
    if new_slot.available_seats == 0:
        new_slot.status = 'Full'

    booking.slot_id = new_slot.id
    db.session.commit()
    flash('Booking rescheduled successfully.', 'success')
    return redirect(url_for('admin.bookings'))


# ---------------------------------------------------------------------------
# Admin oversight — Students  (Step 19)
# ---------------------------------------------------------------------------

@admin.route('/students')
@admin_required
def students():
    q = request.args.get('q', '').strip()
    query = (
        User.query
        .join(StudentProfile, User.id == StudentProfile.user_id)
        .filter(User.role == 'student')
    )
    if q:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%'),
            )
        )
    all_students = query.order_by(User.name).all()
    return render_template('admin/students.html', students=all_students, q=q)


# ---------------------------------------------------------------------------
# Exam reassignment  (Step 19)
# ---------------------------------------------------------------------------

@admin.route('/exams/<int:exam_id>/reassign', methods=['POST'])
@admin_required
def reassign_exam(exam_id):
    exam            = Exam.query.get_or_404(exam_id)
    new_examiner_id = request.form.get('new_examiner_id', '').strip()

    if not new_examiner_id:
        flash('New examiner ID is required.', 'danger')
        return redirect(url_for('admin.exams'))

    new_examiner = User.query.get(int(new_examiner_id))
    if not new_examiner or new_examiner.role != 'examiner':
        flash('Invalid examiner selected.', 'danger')
        return redirect(url_for('admin.exams'))

    exam.examiner_id = new_examiner.id
    # update all slots for this exam
    for slot in exam.slots:
        slot.examiner_id = new_examiner.id
    db.session.commit()
    flash(f'Exam reassigned to {new_examiner.name}.', 'success')
    return redirect(url_for('admin.exams'))