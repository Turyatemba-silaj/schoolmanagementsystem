# School Management System

This Django project implements a school management system based on the provided ERD.

## Features

- Custom user model for administrators, staff, students, and guardians
- Department and staff management
- Student, guardian, and admission workflows
- Academic years, terms, classes, streams, enrollments, exams, and results
- Attendance tracking, fees structure, payments, receipts, and discounts
- Library book cataloging and borrowing
- Hostel and room management
- Transport routes, vehicles, and student allocations
- Online applications with document attachments
- Events, event participants, health records, discipline records, leave requests, notifications, holidays, and system settings

## Setup

1. Create and activate the virtual environment (already present in this workspace):
   ```bash
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. Apply migrations:
   ```bash
   .venv\Scripts\python.exe manage.py migrate
   ```
4. Create a superuser:
   ```bash
   .venv\Scripts\python.exe manage.py createsuperuser
   ```
5. Run the development server:
   ```bash
   .venv\Scripts\python.exe manage.py runserver
   ```

## Frontend

Open `http://127.0.0.1:8000/` to access the school management frontend. Use the navigation menu to view:

- Students: `/students/`
- Staff: `/staff/`
- Classes: `/classes/`
- Applications: `/applications/`

## API Endpoints

- `http://127.0.0.1:8000/api/students/`
- `http://127.0.0.1:8000/api/staff/`

## Admin

Access the Django admin at `http://127.0.0.1:8000/admin/` to manage the full ERD entities.
