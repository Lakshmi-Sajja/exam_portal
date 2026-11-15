# Examination Management Portal: Basic Functionalities by Role

A summary of what each role can do in the Examination Management Portal (EMP), built with Flask, Jinja2, Bootstrap and SQLite.

## 1. Overview

The portal has three roles. Each role logs in and sees only the pages and actions allowed for it.

| Role | How they get an account | Access condition |
| --- | --- | --- |
| Admin | Pre-seeded in the database (no registration) | Always active |
| Examiner | Self-registers | Must be approved by Admin before reaching the dashboard |
| Student | Self-registers | Active immediately after registration |

## 2. Admin

The admin is the superuser who manages the whole system.

### 2.1 Dashboard

- Total courses
- Total examinations
- Total examiners and students
- Total examination slots
- Total bookings

### 2.2 Course management

- Create, edit and remove courses
- Fields: course code, name, description, status

### 2.3 Examination management

- Create, edit and remove examinations for a course
- Set examination type (Viva / Practical / Project Demo / Assessment), duration and maximum marks
- Configure the timeline: slot creation start and end dates, slot booking start and end dates
- Manage status (Draft / Slot Creation / Booking Open / Closed / Completed)
- Assign an examiner to an examination

### 2.4 Rubric management

- Create and manage rubric criteria for each examination
- Fields: criterion name, maximum marks, weightage, description

### 2.5 Examiner management

- Add examiners directly
- Approve pending examiner registrations
- Deactivate examiners

### 2.6 Slot and booking control

- Open and close examiner slot creation
- Open and close student slot booking
- View all examination slots
- View all bookings
- Reschedule a student's booking to another slot
- Change the assigned examiner in exceptional situations

### 2.7 View and search

- View all students, examiners, examinations and bookings, including historical data
- Search students, examiners, examinations or bookings by name or ID

## 3. Examiner

Examiners are faculty who conduct and evaluate examinations.

### 3.1 Account

- Register and log in
- After registering, the account stays pending until the Admin approves it

### 3.2 Dashboard

- Assigned examinations
- Slots created
- Number of students booked
- Pending evaluations

### 3.3 Slot management

- Create slots for assigned examinations, only during the slot creation period
- Set date, start time, end time and maximum student capacity
- Update or remove slots, only before booking starts

### 3.4 Evaluation

- View the students booked in their own slots
- Evaluate a student against each rubric criterion
- Submit marks and remarks
- Evaluate only students booked into their own slots

## 4. Student

### 4.1 Account

- Register and log in
- Edit profile

### 4.2 Dashboard

- Available examinations
- Available slots
- Upcoming examinations
- Booked slots
- Published results

### 4.3 Examinations

- View available examinations
- Search and filter examinations
- View the examination schedule

### 4.4 Booking

- Book an available slot, only during the booking period
- Cancel a booking before the booking deadline
- View booking status (Booked / Cancelled / Completed)
- View full booking history

### 4.5 Results

- View examination history
- View published results, marks and examiner remarks

## 5. Rules enforced by the system

1. Examiners can create slots only during the slot creation period.
2. Students can book only during the booking period.
3. A slot cannot be booked beyond its capacity.
4. A slot closes automatically (status Full) when capacity is reached, and reopens if a booking is cancelled.
5. A student cannot book the same examination twice.
6. Examiners can evaluate only students in their own slots.
7. Slots can be edited or removed only before booking starts.
8. Cancelled bookings are kept with status Cancelled, so history is never lost.
9. Admin can reschedule bookings and change examiners when required.

## 6. Feature summary by role

| Feature | Admin | Examiner | Student |
| --- | --- | --- | --- |
| Register / log in | Log in only | Yes | Yes |
| Manage courses | Yes | No | No |
| Manage examinations and rubrics | Yes | No | No |
| Approve or deactivate examiners | Yes | No | No |
| Open/close slot creation and booking | Yes | No | No |
| Create and edit slots | View only | Yes | No |
| Book and cancel slots | Reschedule only | No | Yes |
| Evaluate students | No | Yes | No |
| View results | All | Own students | Own results |
| Search | Students, examiners, exams, bookings | No | Examinations |
| Dashboard | Yes | Yes | Yes |
