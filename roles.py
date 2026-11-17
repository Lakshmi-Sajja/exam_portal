from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, logout_user


def role_required(role):
    # builds a decorator that only lets users with the given role in
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # not logged in -> go to login page
            if not current_user.is_authenticated:
                flash('Please log in first', 'warning')
                return redirect(url_for('auth.login'))

            # logged in but wrong role -> forbidden
            if current_user.role != role:
                abort(403)

            # examiners must still be approved (admin may deactivate them later)
            if role == 'examiner':
                if current_user.examiner_profile.status != 'approved':
                    logout_user()
                    flash('Your examiner account is not approved', 'danger')
                    return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return wrapper
    return decorator


admin_required = role_required('admin')
examiner_required = role_required('examiner')
student_required = role_required('student')