# Examination Management Portal

A Flask web application for managing university examinations. It supports three roles — admin, examiner, and student. The admin creates courses and exams, assigns examiners, and controls when slots can be created and booked. Examiners create time slots and evaluate students. Students browse available exams, book a slot, and view their published results.

## Database

SQLite, stored in `instance/emp.db`. Created automatically on first run via SQLAlchemy. The tables are:

| Table            | Purpose                                              |
|------------------|------------------------------------------------------|
| User             | All accounts (admin, examiner, student)              |
| ExaminerProfile  | Extra details for examiners, including approval status |
| StudentProfile   | Extra details for students (roll number, department) |
| Course           | Courses that exams belong to                         |
| Exam             | Exam details, timeline dates, and status             |
| Rubric           | Marking criteria for each exam                       |
| Slot             | Time slots created by examiners                      |
| Booking          | Student bookings for slots                           |
| Evaluation       | Marks and remarks submitted by the examiner          |
| EvaluationScore  | Per-criterion marks linked to a rubric               |

## How to run

1. Create a virtual environment and activate it

```
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies

```
pip install -r requirements.txt
```

3. Start the app

```
python app.py
```

4. Open http://127.0.0.1:8000 in your browser

The database and admin account are created automatically on first run.

## Admin login

Email: admin@emp.com  
Password: admin123

## Other accounts

- **Examiner** — register at /register/examiner, then log in after the admin approves your account
- **Student** — register at /register/student, log in immediately
