from datetime import datetime, date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from models import Booking, Evaluation, EvaluationScore, Exam, Rubric, Slot, db
from roles import examiner_required

examiner = Blueprint('examiner', __name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_exam_or_403(exam_id):
    """Return the exam only if it belongs to the current examiner."""
    exam = Exam.query.get_or_404(exam_id)
    if exam.examiner_id != current_user.id:
        flash('You are not assigned to that exam.', 'danger')
        return None
    return exam


def _get_slot_or_403(slot_id):
    """Return the slot only if it belongs to the current examiner."""
    slot = Slot.query.get_or_404(slot_id)
    if slot.examiner_id != current_user.id:
        flash('You do not own that slot.', 'danger')
        return None
    return slot


def _slot_creation_allowed(exam):
    """True when the exam window allows adding / editing slots today."""
    if not exam.slot_creation_open:
        return False
    today = date.today()
    if exam.slot_creation_start and today < exam.slot_creation_start:
        return False
    if exam.slot_creation_end and today > exam.slot_creation_end:
        return False
    return True


def _slot_has_bookings(slot_id):
    return Booking.query.filter_by(slot_id=slot_id, status='Booked').count() > 0


# ── dashboard ─────────────────────────────────────────────────────────────────

@examiner.route('/examiner/dashboard')
@examiner_required
def dashboard():
    exams = Exam.query.filter_by(examiner_id=current_user.id).all()
    exam_ids = [e.id for e in exams]

    slot_count = Slot.query.filter(Slot.exam_id.in_(exam_ids),
                                   Slot.examiner_id == current_user.id).count()

    slot_ids = [s.id for s in Slot.query.filter(
        Slot.exam_id.in_(exam_ids),
        Slot.examiner_id == current_user.id
    ).with_entities(Slot.id).all()]

    students_booked = Booking.query.filter(
        Booking.slot_id.in_(slot_ids),
        Booking.status.in_(['Booked', 'Completed'])
    ).count()

    # pending: booked but no evaluation record yet
    booked_ids = [b.id for b in Booking.query.filter(
        Booking.slot_id.in_(slot_ids),
        Booking.status == 'Booked'
    ).with_entities(Booking.id).all()]

    evaluated_ids = [e.booking_id for e in Evaluation.query.filter(
        Evaluation.booking_id.in_(booked_ids)
    ).with_entities(Evaluation.booking_id).all()]

    pending_evals = len(set(booked_ids) - set(evaluated_ids))

    return render_template(
        'examiner/dashboard.html',
        exam_count=len(exams),
        slot_count=slot_count,
        students_booked=students_booked,
        pending_evals=pending_evals,
    )


# ── exams list ────────────────────────────────────────────────────────────────

@examiner.route('/examiner/exams')
@examiner_required
def exams():
    assigned_exams = Exam.query.filter_by(examiner_id=current_user.id).all()
    return render_template('examiner/exams.html', exams=assigned_exams)


# ── slots list ────────────────────────────────────────────────────────────────

@examiner.route('/examiner/exams/<int:exam_id>/slots')
@examiner_required
def slots(exam_id):
    exam = _get_exam_or_403(exam_id)
    if exam is None:
        return redirect(url_for('examiner.exams'))

    all_slots = Slot.query.filter_by(exam_id=exam_id,
                                     examiner_id=current_user.id).all()

    can_add = _slot_creation_allowed(exam)

    # For each slot, decide whether edit/delete is permitted
    slot_data = []
    for slot in all_slots:
        editable = (not exam.booking_open) and (not _slot_has_bookings(slot.id))
        slot_data.append({'slot': slot, 'editable': editable})

    return render_template(
        'examiner/slots.html',
        exam=exam,
        slot_data=slot_data,
        can_add=can_add,
    )


# ── add slot ──────────────────────────────────────────────────────────────────

@examiner.route('/examiner/exams/<int:exam_id>/slots/add', methods=['GET', 'POST'])
@examiner_required
def add_slot(exam_id):
    exam = _get_exam_or_403(exam_id)
    if exam is None:
        return redirect(url_for('examiner.exams'))

    if not _slot_creation_allowed(exam):
        flash('Slot creation is not open for this exam right now.', 'warning')
        return redirect(url_for('examiner.slots', exam_id=exam_id))

    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        start_str = request.form.get('start_time', '').strip()
        end_str = request.form.get('end_time', '').strip()
        capacity_str = request.form.get('capacity', '').strip()

        # parse and validate
        try:
            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Add')

        try:
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
        except ValueError:
            flash('Invalid time format.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Add')

        if end_time <= start_time:
            flash('End time must be after start time.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Add')

        try:
            capacity = int(capacity_str)
        except ValueError:
            flash('Capacity must be a number.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Add')

        if capacity <= 0:
            flash('Capacity must be greater than 0.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Add')

        new_slot = Slot(
            exam_id=exam_id,
            examiner_id=current_user.id,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            available_seats=capacity,
            status='Available',
        )
        db.session.add(new_slot)
        db.session.commit()
        flash('Slot added successfully.', 'success')
        return redirect(url_for('examiner.slots', exam_id=exam_id))

    return render_template('examiner/slot_form.html', exam=exam, action='Add', slot=None)


# ── edit slot ─────────────────────────────────────────────────────────────────

@examiner.route('/examiner/slots/<int:slot_id>/edit', methods=['GET', 'POST'])
@examiner_required
def edit_slot(slot_id):
    slot = _get_slot_or_403(slot_id)
    if slot is None:
        return redirect(url_for('examiner.exams'))

    exam = slot.exam

    if exam.examiner_id != current_user.id:
        flash('You are not assigned to that exam.', 'danger')
        return redirect(url_for('examiner.exams'))

    if exam.booking_open:
        flash('Cannot edit slots after booking has opened.', 'warning')
        return redirect(url_for('examiner.slots', exam_id=exam.id))

    if _slot_has_bookings(slot_id):
        flash('Cannot edit a slot that already has bookings.', 'warning')
        return redirect(url_for('examiner.slots', exam_id=exam.id))

    if not _slot_creation_allowed(exam):
        flash('Slot creation window is not open.', 'warning')
        return redirect(url_for('examiner.slots', exam_id=exam.id))

    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        start_str = request.form.get('start_time', '').strip()
        end_str = request.form.get('end_time', '').strip()
        capacity_str = request.form.get('capacity', '').strip()

        try:
            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Edit', slot=slot)

        try:
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
        except ValueError:
            flash('Invalid time format.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Edit', slot=slot)

        if end_time <= start_time:
            flash('End time must be after start time.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Edit', slot=slot)

        try:
            capacity = int(capacity_str)
        except ValueError:
            flash('Capacity must be a number.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Edit', slot=slot)

        if capacity <= 0:
            flash('Capacity must be greater than 0.', 'danger')
            return render_template('examiner/slot_form.html', exam=exam, action='Edit', slot=slot)

        slot.date = slot_date
        slot.start_time = start_time
        slot.end_time = end_time
        slot.capacity = capacity
        slot.available_seats = capacity
        db.session.commit()
        flash('Slot updated successfully.', 'success')
        return redirect(url_for('examiner.slots', exam_id=exam.id))

    return render_template('examiner/slot_form.html', exam=exam, action='Edit', slot=slot)


# ── delete slot ───────────────────────────────────────────────────────────────

@examiner.route('/examiner/slots/<int:slot_id>/delete', methods=['POST'])
@examiner_required
def delete_slot(slot_id):
    slot = _get_slot_or_403(slot_id)
    if slot is None:
        return redirect(url_for('examiner.exams'))

    exam = slot.exam

    if exam.booking_open:
        flash('Cannot delete slots after booking has opened.', 'warning')
        return redirect(url_for('examiner.slots', exam_id=exam.id))

    if _slot_has_bookings(slot_id):
        flash('Cannot delete a slot that has bookings.', 'warning')
        return redirect(url_for('examiner.slots', exam_id=exam.id))

    db.session.delete(slot)
    db.session.commit()
    flash('Slot deleted.', 'success')
    return redirect(url_for('examiner.slots', exam_id=exam.id))


# ── students in a slot ────────────────────────────────────────────────────────

@examiner.route('/examiner/slots/<int:slot_id>/students')
@examiner_required
def slot_students(slot_id):
    slot = _get_slot_or_403(slot_id)
    if slot is None:
        return redirect(url_for('examiner.exams'))

    bookings = Booking.query.filter(
        Booking.slot_id == slot_id,
        Booking.status.in_(['Booked', 'Completed'])
    ).all()

    return render_template('examiner/students.html', slot=slot, bookings=bookings)


# ── evaluate a student ────────────────────────────────────────────────────────

@examiner.route('/examiner/bookings/<int:booking_id>/evaluate', methods=['GET', 'POST'])
@examiner_required
def evaluate(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = Slot.query.get_or_404(booking.slot_id)

    if slot.examiner_id != current_user.id:
        flash('You do not have access to this booking.', 'danger')
        return redirect(url_for('examiner.exams'))

    exam = booking.exam
    rubrics = Rubric.query.filter_by(exam_id=exam.id).all()
    evaluation = Evaluation.query.filter_by(booking_id=booking_id).first()

    # Build a dict of existing scores keyed by rubric_id for pre-filling the form
    existing_scores = {}
    if evaluation:
        for score in evaluation.scores:
            existing_scores[score.rubric_id] = score.marks

    if request.method == 'POST':
        remarks = request.form.get('remarks', '').strip()
        marks_map = {}
        error = False

        for rubric in rubrics:
            raw = request.form.get(f'marks_{rubric.id}', '').strip()
            try:
                marks = float(raw)
            except ValueError:
                flash(f'Invalid marks for "{rubric.criterion_name}".', 'danger')
                error = True
                break

            if marks < 0 or marks > rubric.max_marks:
                flash(
                    f'Marks for "{rubric.criterion_name}" must be between 0 and {rubric.max_marks}.',
                    'danger',
                )
                error = True
                break

            marks_map[rubric.id] = marks

        if not error:
            total = sum(marks_map.values())

            if evaluation is None:
                evaluation = Evaluation(
                    booking_id=booking_id,
                    total_marks=total,
                    remarks=remarks,
                    is_published=False,
                )
                db.session.add(evaluation)
                db.session.flush()  # get evaluation.id before adding scores

                for rubric_id, marks in marks_map.items():
                    score = EvaluationScore(
                        evaluation_id=evaluation.id,
                        rubric_id=rubric_id,
                        marks=marks,
                    )
                    db.session.add(score)
            else:
                evaluation.total_marks = total
                evaluation.remarks = remarks

                # update or create each score
                for rubric_id, marks in marks_map.items():
                    score = EvaluationScore.query.filter_by(
                        evaluation_id=evaluation.id,
                        rubric_id=rubric_id,
                    ).first()
                    if score:
                        score.marks = marks
                    else:
                        db.session.add(EvaluationScore(
                            evaluation_id=evaluation.id,
                            rubric_id=rubric_id,
                            marks=marks,
                        ))

            booking.status = 'Completed'
            db.session.commit()
            flash('Evaluation saved successfully.', 'success')
            return redirect(url_for('examiner.slot_students', slot_id=booking.slot_id))

    return render_template(
        'examiner/evaluate.html',
        booking=booking,
        exam=exam,
        rubrics=rubrics,
        existing_scores=existing_scores,
        evaluation=evaluation,
    )
