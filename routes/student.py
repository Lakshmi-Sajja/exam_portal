# routes/student.py
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from models import Booking, Course, Evaluation, EvaluationScore, Exam, Rubric, Slot, db
from roles import student_required

student = Blueprint('student', __name__, url_prefix='/student')


# ---------------------------------------------------------------------------
# Step 20 — Dashboard
# ---------------------------------------------------------------------------

@student.route('/dashboard')
@student_required
def dashboard():
    today = date.today()

    # exams that are open for booking right now
    open_exams = Exam.query.filter(
        Exam.booking_open == True,
        Exam.booking_start <= today,
        Exam.booking_end >= today
    ).all()
    open_exam_ids = [e.id for e in open_exams]

    available_exams_count = len(open_exams)

    # slots still available linked to those open exams
    available_slots_count = Slot.query.filter(
        Slot.exam_id.in_(open_exam_ids),
        Slot.status == 'Available'
    ).count() if open_exam_ids else 0

    # this student's active bookings
    booked_slots_count = Booking.query.filter_by(
        student_id=current_user.id,
        status='Booked'
    ).count()

    # published results for this student
    published_results_count = (
        Evaluation.query
        .join(Booking, Evaluation.booking_id == Booking.id)
        .filter(
            Booking.student_id == current_user.id,
            Booking.status == 'Completed',
            Evaluation.is_published == True
        )
        .count()
    )

    return render_template(
        'student/dashboard.html',
        available_exams=available_exams_count,
        available_slots=available_slots_count,
        booked_slots=booked_slots_count,
        published_results=published_results_count
    )


# ---------------------------------------------------------------------------
# Step 15 — Exam browsing and search
# ---------------------------------------------------------------------------

@student.route('/exams')
@student_required
def exams():
    today = date.today()

    q          = request.args.get('q', '').strip()
    course_id  = request.args.get('course_id', '').strip()
    exam_type  = request.args.get('exam_type', '').strip()

    # base query: only booking-open exams within the booking window
    query = (
        Exam.query
        .join(Course, Exam.course_id == Course.id)
        .filter(
            Exam.booking_open == True,
            Exam.booking_start <= today,
            Exam.booking_end >= today
        )
    )

    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(Exam.name.ilike(like), Course.name.ilike(like))
        )
    if course_id:
        query = query.filter(Exam.course_id == course_id)
    if exam_type:
        query = query.filter(Exam.exam_type == exam_type)

    exam_list = query.all()

    all_courses   = Course.query.filter_by(status='active').order_by(Course.name).all()
    all_exam_types = ['Viva', 'Practical', 'Project Demo', 'Assessment']

    return render_template(
        'student/exams.html',
        exams=exam_list,
        courses=all_courses,
        exam_types=all_exam_types,
        q=q,
        selected_course=course_id,
        selected_type=exam_type
    )


# ---------------------------------------------------------------------------
# Exam detail — available slots
# ---------------------------------------------------------------------------

@student.route('/exams/<int:exam_id>/slots')
@student_required
def exam_slots(exam_id):
    today = date.today()
    exam  = db.session.get(Exam, exam_id)

    if exam is None:
        flash('Exam not found.', 'danger')
        return redirect(url_for('student.exams'))

    booking_open = (
        exam.booking_open
        and exam.booking_start <= today <= exam.booking_end
    )

    slots = (
        Slot.query
        .filter_by(exam_id=exam_id, status='Available')
        .order_by(Slot.date, Slot.start_time)
        .all()
    )

    return render_template(
        'student/exam_slots.html',
        exam=exam,
        slots=slots,
        booking_open=booking_open
    )


# ---------------------------------------------------------------------------
# Step 16 — Book a slot
# ---------------------------------------------------------------------------

@student.route('/exams/<int:exam_id>/book/<int:slot_id>', methods=['POST'])
@student_required
def book_slot(exam_id, slot_id):
    today = date.today()

    exam = db.session.get(Exam, exam_id)
    slot = db.session.get(Slot, slot_id)

    if exam is None or slot is None:
        flash('Exam or slot not found.', 'danger')
        return redirect(url_for('student.exams'))

    # 1. Booking window check
    if not (exam.booking_open and exam.booking_start <= today <= exam.booking_end):
        flash('Booking is not open for this exam right now.', 'warning')
        return redirect(url_for('student.exam_slots', exam_id=exam_id))

    # 2. Duplicate booking check
    existing = Booking.query.filter_by(
        student_id=current_user.id,
        exam_id=exam_id,
        status='Booked'
    ).first()
    if existing:
        flash('You already have an active booking for this exam.', 'warning')
        return redirect(url_for('student.exam_slots', exam_id=exam_id))

    # 3. Seat availability check
    if slot.available_seats <= 0:
        flash('No seats available in this slot.', 'warning')
        return redirect(url_for('student.exam_slots', exam_id=exam_id))

    # Create the booking
    booking = Booking(
        student_id=current_user.id,
        slot_id=slot_id,
        exam_id=exam_id,
        booking_date=datetime.now(),
        status='Booked'
    )
    db.session.add(booking)

    # Decrement available seats
    slot.available_seats -= 1
    if slot.available_seats == 0:
        slot.status = 'Full'

    db.session.commit()
    flash('Slot booked successfully!', 'success')
    return redirect(url_for('student.bookings'))


# ---------------------------------------------------------------------------
# Step 16 — View all bookings
# ---------------------------------------------------------------------------

@student.route('/bookings')
@student_required
def bookings():
    today = date.today()
    all_bookings = (
        Booking.query
        .filter_by(student_id=current_user.id)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return render_template('student/bookings.html', bookings=all_bookings, today=today)


# ---------------------------------------------------------------------------
# Step 16 — Cancel a booking
# ---------------------------------------------------------------------------

@student.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@student_required
def cancel_booking(booking_id):
    today = date.today()
    booking = db.session.get(Booking, booking_id)

    if booking is None:
        flash('Booking not found.', 'danger')
        return redirect(url_for('student.bookings'))

    # 1. Ownership check
    if booking.student_id != current_user.id:
        flash('You are not allowed to cancel this booking.', 'danger')
        return redirect(url_for('student.bookings'))

    # 2. Status check
    if booking.status != 'Booked':
        flash('Only active bookings can be cancelled.', 'warning')
        return redirect(url_for('student.bookings'))

    # 3. Deadline check
    exam = db.session.get(Exam, booking.exam_id)
    if today > exam.booking_end:
        flash('The cancellation deadline has passed.', 'warning')
        return redirect(url_for('student.bookings'))

    # Cancel the booking
    booking.status = 'Cancelled'
    booking.cancelled_at = datetime.now()

    # Return the seat to the slot
    slot = db.session.get(Slot, booking.slot_id)
    slot.available_seats += 1
    if slot.status == 'Full':
        slot.status = 'Available'

    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('student.bookings'))


# ---------------------------------------------------------------------------
# Step 18 — Results list
# ---------------------------------------------------------------------------

@student.route('/results')
@student_required
def results():
    published = (
        Booking.query
        .join(Evaluation, Booking.id == Evaluation.booking_id)
        .filter(
            Booking.student_id == current_user.id,
            Booking.status == 'Completed',
            Evaluation.is_published == True
        )
        .all()
    )
    return render_template('student/results.html', bookings=published)


# ---------------------------------------------------------------------------
# Step 18 — Result detail
# ---------------------------------------------------------------------------

@student.route('/results/<int:booking_id>')
@student_required
def result_detail(booking_id):
    booking = db.session.get(Booking, booking_id)

    if booking is None or booking.student_id != current_user.id:
        flash('Result not found.', 'danger')
        return redirect(url_for('student.results'))

    evaluation = booking.evaluation
    if evaluation is None or not evaluation.is_published:
        flash('Result is not published yet.', 'warning')
        return redirect(url_for('student.results'))

    scores = (
        EvaluationScore.query
        .filter_by(evaluation_id=evaluation.id)
        .all()
    )

    return render_template(
        'student/result_detail.html',
        booking=booking,
        evaluation=evaluation,
        scores=scores
    )


# ---------------------------------------------------------------------------
# Step 21 — Profile view/edit
# ---------------------------------------------------------------------------

@student.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    user    = current_user
    profile = user.student_profile

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        contact  = request.form.get('contact', '').strip()
        password = request.form.get('password', '').strip()

        if not name:
            flash('Name cannot be empty.', 'danger')
            return redirect(url_for('student.profile'))

        if password:
            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return redirect(url_for('student.profile'))
            user.set_password(password)

        user.name = name
        if profile:
            profile.contact = contact

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student/profile.html', user=user, profile=profile)
