from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    AcademicYear,
    Account,
    Admission,
    ApplicationDocument,
    ApplicationRequirement,
    ApplicationRequirementCheck,
    Attendance,
    AuditLog,
    BookBorrowing,
    ClassSubject,
    Department,
    DisciplineRecord,
    Document,
    Enrollment,
    Event,
    EventParticipant,
    Exam,
    ExamResult,
    Expense,
    FeeDiscount,
    FeesStructure,
    Guardian,
    HealthRecord,
    Holiday,
    Hostel,
    HostelAllocation,
    HostelRoom,
    Invoice,
    JournalEntry,
    JournalLine,
    Leave,
    LibraryBook,
    Notification,
    OnlineApplication,
    Payment,
    Payroll,
    Receipt,
    SchoolClass,
    Staff,
    StaffAttendance,
    Stream,
    Student,
    StudentGuardian,
    Subject,
    Supplier,
    SystemSetting,
    Term,
    TransportAllocation,
    TransportRoute,
    User,
    Vehicle,
)


class Command(BaseCommand):
    help = 'Seed at least five standard demonstration records in every core school table.'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.seed()
        self.stdout.write(self.style.SUCCESS('Every core school table now has at least five records.'))

    def seed(self):
        self.ensure_users()
        self.ensure_departments()
        self.ensure_staff()
        self.ensure_guardians()
        self.ensure_students()
        self.ensure_academics()
        self.ensure_attendance_and_results()
        self.ensure_finance()
        self.ensure_services()
        self.ensure_applications()
        self.ensure_miscellaneous()
        self.ensure_audit_logs()

    def ensure_count(self, model, creator, target=5):
        while model.objects.count() < target:
            index = model.objects.count() + 1
            creator(index)

    def ensure_users(self):
        UserModel = get_user_model()

        def create_user(index):
            UserModel.objects.create_user(
                username=f'demo.user{index}',
                password='demo12345',
                first_name=f'Demo{index}',
                last_name='User',
                email=f'demo.user{index}@school.test',
                role=User.Role.OTHER,
                status=User.Status.ACTIVE,
            )

        self.ensure_count(UserModel, create_user)

    def ensure_departments(self):
        names = ['Administration', 'Mathematics', 'Science', 'Languages', 'Finance']
        for index, name in enumerate(names, start=1):
            Department.objects.get_or_create(
                department_name=name,
                defaults={'description': f'{name} department', 'status': 'active'},
            )

    def ensure_staff(self):
        departments = list(Department.objects.order_by('id')[:5])
        UserModel = get_user_model()
        for index in range(1, 6):
            user, _ = UserModel.objects.get_or_create(
                username=f'demo.staff{index}',
                defaults={
                    'first_name': f'Staff{index}',
                    'last_name': 'Member',
                    'email': f'staff{index}@school.test',
                    'role': User.Role.STAFF,
                    'status': User.Status.ACTIVE,
                },
            )
            if not user.has_usable_password():
                user.set_password('staff12345')
                user.save()
            Staff.objects.get_or_create(
                employee_code=f'STAFF-{index:03d}',
                defaults={
                    'user': user,
                    'department': departments[(index - 1) % len(departments)],
                    'full_name': f'Demo Staff {index}',
                    'designation': ['Head Teacher', 'Teacher', 'Bursar', 'Librarian', 'Nurse'][(index - 1) % 5],
                    'phone': f'+25670000000{index}',
                    'email': f'staff{index}@school.test',
                    'address': 'Kampala, Uganda',
                    'hire_date': date(2022, 1, min(index, 28)),
                    'base_salary': Decimal('1200000.00') + Decimal(index * 100000),
                    'status': 'active',
                },
            )

    def ensure_guardians(self):
        for index in range(1, 6):
            Guardian.objects.get_or_create(
                full_name=f'Demo Guardian {index}',
                defaults={
                    'phone': f'+25675000000{index}',
                    'email': f'guardian{index}@school.test',
                    'address': 'Kampala, Uganda',
                    'occupation': ['Farmer', 'Teacher', 'Trader', 'Engineer', 'Nurse'][(index - 1) % 5],
                },
            )

    def ensure_students(self):
        UserModel = get_user_model()
        for index in range(1, 6):
            user, _ = UserModel.objects.get_or_create(
                username=f'demo.student{index}',
                defaults={
                    'first_name': f'Student{index}',
                    'last_name': 'Learner',
                    'email': f'student{index}@school.test',
                    'role': User.Role.STUDENT,
                    'status': User.Status.ACTIVE,
                },
            )
            if not user.has_usable_password():
                user.set_password('student12345')
                user.save()
            Student.objects.get_or_create(
                admission_no=f'ADM2026-{index:04d}',
                defaults={
                    'user': user,
                    'first_name': f'Student{index}',
                    'last_name': 'Learner',
                    'gender': 'Female' if index % 2 else 'Male',
                    'dob': date(2010 + index, 2, min(index, 28)),
                    'blood_group': ['O+', 'A+', 'B+', 'AB+', 'O-'][(index - 1) % 5],
                    'phone': f'+25676000000{index}',
                    'address': 'Kampala, Uganda',
                    'status': 'active',
                },
            )

        students = list(Student.objects.order_by('id')[:5])
        guardians = list(Guardian.objects.order_by('id')[:5])
        for index, student in enumerate(students, start=1):
            StudentGuardian.objects.get_or_create(
                student=student,
                guardian=guardians[(index - 1) % len(guardians)],
                defaults={'relationship': ['Father', 'Mother', 'Guardian', 'Uncle', 'Aunt'][(index - 1) % 5]},
            )

    def ensure_academics(self):
        for index in range(1, 6):
            AcademicYear.objects.get_or_create(
                year_name=f'2026 Academic Year {index}',
                defaults={
                    'start_date': date(2026, 1, 1) + timedelta(days=index - 1),
                    'end_date': date(2026, 12, 1) + timedelta(days=index - 1),
                    'status': 'active' if index == 1 else 'planned',
                },
            )
            SchoolClass.objects.get_or_create(
                class_name=f'Senior {index}',
                defaults={'class_level': f'S{index}', 'description': f'Senior {index} class', 'status': 'active'},
            )
            Subject.objects.get_or_create(
                subject_code=f'SUB-{index:03d}',
                defaults={'subject_name': ['Mathematics', 'English', 'Biology', 'Islamic Studies', 'History'][(index - 1) % 5]},
            )

        years = list(AcademicYear.objects.order_by('id')[:5])
        classes = list(SchoolClass.objects.order_by('id')[:5])
        students = list(Student.objects.order_by('id')[:5])
        subjects = list(Subject.objects.order_by('id')[:5])
        staff = list(Staff.objects.order_by('id')[:5])

        for index, school_class in enumerate(classes, start=1):
            Stream.objects.get_or_create(
                school_class=school_class,
                stream_name=f'Stream {index}',
                defaults={'status': 'active'},
            )
            Term.objects.get_or_create(
                year=years[(index - 1) % len(years)],
                term_name=f'Term {index}',
                defaults={
                    'start_date': date(2026, min(index, 12), 1),
                    'end_date': date(2026, min(index + 1, 12), 20),
                    'status': 'active',
                },
            )
            ClassSubject.objects.get_or_create(
                school_class=school_class,
                subject=subjects[(index - 1) % len(subjects)],
                defaults={'staff': staff[(index - 1) % len(staff)]},
            )

        streams = list(Stream.objects.order_by('id')[:5])
        for index, student in enumerate(students, start=1):
            Enrollment.objects.get_or_create(
                student=student,
                school_class=classes[(index - 1) % len(classes)],
                year=years[(index - 1) % len(years)],
                defaults={
                    'stream': streams[(index - 1) % len(streams)],
                    'enrollment_date': date(2026, 1, min(index, 28)),
                    'status': 'active',
                },
            )

    def ensure_attendance_and_results(self):
        students = list(Student.objects.order_by('id')[:5])
        classes = list(SchoolClass.objects.order_by('id')[:5])
        streams = list(Stream.objects.order_by('id')[:5])
        terms = list(Term.objects.order_by('id')[:5])
        subjects = list(Subject.objects.order_by('id')[:5])
        staff = list(Staff.objects.order_by('id')[:5])

        for index, student in enumerate(students, start=1):
            Attendance.objects.get_or_create(
                student=student,
                school_class=classes[(index - 1) % len(classes)],
                attendance_date=date(2026, 2, min(index, 28)),
                defaults={'stream': streams[(index - 1) % len(streams)], 'status': 'present'},
            )
            StaffAttendance.objects.get_or_create(
                staff=staff[(index - 1) % len(staff)],
                attendance_date=date(2026, 2, min(index, 28)),
                defaults={'status': 'present', 'marked_by': staff[0]},
            )
            Payroll.objects.get_or_create(
                staff=staff[(index - 1) % len(staff)],
                month=index,
                year=2026,
                defaults={
                    'base_salary': staff[(index - 1) % len(staff)].base_salary,
                    'present_days': 20,
                    'working_days': 22,
                    'payable_days': 20,
                    'deductions': Decimal('50000.00'),
                    'net_salary': staff[(index - 1) % len(staff)].base_salary - Decimal('50000.00'),
                    'generated_by': staff[0],
                    'status': 'generated',
                },
            )
            exam, _ = Exam.objects.get_or_create(
                term=terms[(index - 1) % len(terms)],
                exam_name=f'Mid Term Exam {index}',
                defaults={
                    'exam_type': 'Mid Term',
                    'exam_date': date(2026, 3, min(index, 28)),
                    'max_marks': 100,
                    'status': 'completed',
                },
            )
            ExamResult.objects.get_or_create(
                exam=exam,
                student=student,
                subject=subjects[(index - 1) % len(subjects)],
                defaults={'marks_obtained': Decimal(70 + index), 'grade': 'A', 'remarks': 'Good progress'},
            )

    def ensure_finance(self):
        classes = list(SchoolClass.objects.order_by('id')[:5])
        terms = list(Term.objects.order_by('id')[:5])
        students = list(Student.objects.order_by('id')[:5])
        staff = list(Staff.objects.order_by('id')[:5])
        for index in range(1, 6):
            FeesStructure.objects.get_or_create(
                school_class=classes[(index - 1) % len(classes)],
                term=terms[(index - 1) % len(terms)],
                fee_type=f'Tuition Package {index}',
                defaults={'amount': Decimal('900000.00') + Decimal(index * 50000), 'description': 'Standard term fees'},
            )
            Account.objects.get_or_create(
                account_code=f'DEMO-{index:03d}',
                defaults={
                    'account_name': ['Cash', 'Bank', 'Fees Income', 'Salaries', 'Supplies'][(index - 1) % 5],
                    'account_type': [Account.AccountType.ASSET, Account.AccountType.ASSET, Account.AccountType.INCOME, Account.AccountType.EXPENSE, Account.AccountType.EXPENSE][(index - 1) % 5],
                    'description': 'Demo accounting account',
                    'is_active': True,
                },
            )
            Supplier.objects.get_or_create(
                supplier_name=f'Demo Supplier {index}',
                defaults={'contact_person': f'Supplier Contact {index}', 'phone': f'+25677000000{index}', 'email': f'supplier{index}@school.test', 'status': 'active'},
            )

        fees = list(FeesStructure.objects.order_by('id')[:5])
        accounts = list(Account.objects.order_by('id')[:5])
        suppliers = list(Supplier.objects.order_by('id')[:5])
        payments = []
        for index, student in enumerate(students, start=1):
            FeeDiscount.objects.get_or_create(
                fees_structure=fees[(index - 1) % len(fees)],
                discount_type=f'Demo Discount {index}',
                defaults={'discount_value': Decimal('5.00') + Decimal(index), 'applicable_from': date(2026, 1, 1)},
            )
            payment, _ = Payment.objects.get_or_create(
                student=student,
                fees_structure=fees[(index - 1) % len(fees)],
                transaction_id=f'DEMO-PAY-{index:03d}',
                defaults={
                    'payment_date': date(2026, 2, min(index, 28)),
                    'amount_paid': Decimal('300000.00') + Decimal(index * 10000),
                    'payment_method': 'Bank Deposit',
                    'paid_by': f'Demo Guardian {index}',
                    'receipted_by': staff[(index - 1) % len(staff)],
                },
            )
            payments.append(payment)
            Receipt.objects.get_or_create(
                payment=payment,
                defaults={'receipt_no': f'RCT-2026-{index:04d}', 'receipt_date': payment.payment_date},
            )
            journal, _ = JournalEntry.objects.get_or_create(
                description=f'Demo journal entry {index}',
                defaults={'entry_date': date(2026, 2, min(index, 28)), 'reference': f'JREF-{index:03d}', 'status': JournalEntry.Status.POSTED},
            )
            JournalLine.objects.get_or_create(
                journal_entry=journal,
                account=accounts[(index - 1) % len(accounts)],
                description=f'Demo debit line {index}',
                defaults={'debit': Decimal('100000.00'), 'credit': Decimal('0.00')},
            )
            Invoice.objects.get_or_create(
                description=f'Demo invoice {index}',
                student=student,
                defaults={'invoice_date': date(2026, 2, min(index, 28)), 'amount': Decimal('500000.00'), 'amount_paid': Decimal('100000.00'), 'status': Invoice.Status.PART_PAID},
            )
            Expense.objects.get_or_create(
                description=f'Demo expense {index}',
                supplier=suppliers[(index - 1) % len(suppliers)],
                defaults={'account': accounts[(index - 1) % len(accounts)], 'expense_date': date(2026, 2, min(index, 28)), 'amount': Decimal('150000.00'), 'payment_method': 'Cash', 'reference': f'EXPREF-{index:03d}', 'status': Expense.Status.APPROVED, 'approved_by': staff[0]},
            )

    def ensure_services(self):
        students = list(Student.objects.order_by('id')[:5])
        staff = list(Staff.objects.order_by('id')[:5])
        for index in range(1, 6):
            LibraryBook.objects.get_or_create(
                title=f'Demo Library Book {index}',
                defaults={'isbn': f'ISBN-DEMO-{index:03d}', 'author': f'Author {index}', 'publisher': 'School Press', 'category': 'General', 'quantity': 10, 'available_quantity': 9, 'status': 'available'},
            )
            Hostel.objects.get_or_create(
                hostel_name=f'Demo Hostel {index}',
                defaults={'gender_type': 'Female' if index % 2 else 'Male', 'description': 'Student residence'},
            )
            TransportRoute.objects.get_or_create(
                route_name=f'Demo Route {index}',
                defaults={'start_point': 'School', 'end_point': f'Area {index}', 'distance': Decimal(5 + index), 'route_fee': Decimal('150000.00'), 'status': 'active'},
            )
            Vehicle.objects.get_or_create(
                vehicle_no=f'UAX {100 + index}D',
                defaults={'driver_name': f'Driver {index}', 'driver_phone': f'+25678000000{index}', 'capacity': 40, 'status': 'active'},
            )

        books = list(LibraryBook.objects.order_by('id')[:5])
        hostels = list(Hostel.objects.order_by('id')[:5])
        vehicles = list(Vehicle.objects.order_by('id')[:5])
        for index, student in enumerate(students, start=1):
            BookBorrowing.objects.get_or_create(
                book=books[(index - 1) % len(books)],
                student=student,
                defaults={'issue_date': date(2026, 2, min(index, 28)), 'fine_amount': Decimal('0.00'), 'status': 'borrowed'},
            )
            room, _ = HostelRoom.objects.get_or_create(
                hostel=hostels[(index - 1) % len(hostels)],
                room_no=f'R-{index:03d}',
                defaults={'room_name': f'Room {index}', 'capacity': 4, 'status': 'available'},
            )
            HostelAllocation.objects.get_or_create(
                room=room,
                student=student,
                defaults={'allocation_date': date(2026, 1, min(index, 28)), 'status': 'active'},
            )
            TransportAllocation.objects.get_or_create(
                vehicle=vehicles[(index - 1) % len(vehicles)],
                student=student,
                defaults={'allocation_date': date(2026, 1, min(index, 28)), 'status': 'active'},
            )
            HealthRecord.objects.get_or_create(
                student=student,
                medical_condition=f'Demo condition {index}',
                defaults={'allergies': 'None reported', 'medication': 'None', 'doctor_name': f'Dr Demo {index}', 'record_date': date(2026, 1, min(index, 28)), 'notes': 'Routine health record'},
            )
            DisciplineRecord.objects.get_or_create(
                student=student,
                offence_type=f'Demo discipline item {index}',
                defaults={'recorded_by': staff[(index - 1) % len(staff)], 'description': 'Guidance record', 'action_taken': 'Counselling', 'record_date': date(2026, 1, min(index, 28)), 'status': 'closed'},
            )

    def ensure_applications(self):
        classes = list(SchoolClass.objects.order_by('id')[:5])
        students = list(Student.objects.order_by('id')[:5])
        staff = list(Staff.objects.order_by('id')[:5])
        for index in range(1, 6):
            application, _ = OnlineApplication.objects.get_or_create(
                application_no=f'APP2026{index:04d}',
                defaults={
                    'applicant_name': f'Demo Applicant {index}',
                    'dob': date(2011 + index, 4, min(index, 28)),
                    'gender': 'Female' if index % 2 else 'Male',
                    'previous_school': f'Previous School {index}',
                    'applied_class': classes[(index - 1) % len(classes)],
                    'status': 'approved',
                    'application_date': date(2026, 1, min(index, 28)),
                },
            )
            ApplicationDocument.objects.get_or_create(
                application=application,
                document_type=f'Demo Application Document {index}',
                defaults={'file_path': f'application_documents/demo-{index}.pdf'},
            )
            Admission.objects.get_or_create(
                admission_no=f'ADMIT2026{index:03d}',
                defaults={'application': application, 'student': students[(index - 1) % len(students)], 'approved_by': staff[(index - 1) % len(staff)], 'admission_date': date(2026, 1, min(index, 28)), 'status': 'active'},
            )

        requirement_names = [
            'Birth Certificate',
            'Previous School Report',
            'Passport Photo',
            'Medical Form',
            'Parent Or Guardian Details',
        ]
        for index, name in enumerate(requirement_names, start=1):
            ApplicationRequirement.objects.get_or_create(
                requirement_name=name,
                applied_class=None,
                defaults={'description': f'{name} required for admission.', 'is_required': True, 'sort_order': index, 'status': 'active'},
            )
        requirements = list(ApplicationRequirement.objects.order_by('id')[:5])
        applications = list(OnlineApplication.objects.order_by('id')[:5])
        for index, application in enumerate(applications, start=1):
            ApplicationRequirementCheck.objects.get_or_create(
                application=application,
                requirement=requirements[(index - 1) % len(requirements)],
                defaults={'is_satisfied': True, 'note': 'Verified during sample data entry.', 'reviewed_by': staff[(index - 1) % len(staff)], 'reviewed_at': timezone.now()},
            )

    def ensure_miscellaneous(self):
        students = list(Student.objects.order_by('id')[:5])
        staff = list(Staff.objects.order_by('id')[:5])
        years = list(AcademicYear.objects.order_by('id')[:5])
        for index, student in enumerate(students, start=1):
            Document.objects.get_or_create(
                student=student,
                document_type=f'Demo Student Document {index}',
                defaults={'file_path': f'student_documents/demo-{index}.pdf'},
            )
            Event.objects.get_or_create(
                event_title=f'Demo School Event {index}',
                defaults={'event_type': 'Academic', 'start_date': date(2026, 5, min(index, 28)), 'end_date': date(2026, 5, min(index + 1, 28)), 'description': 'School activity', 'organized_by': 'Administration'},
            )
            Leave.objects.get_or_create(
                staff=staff[(index - 1) % len(staff)],
                leave_type=f'Demo Leave {index}',
                defaults={'start_date': date(2026, 6, min(index, 28)), 'end_date': date(2026, 6, min(index + 1, 28)), 'reason': 'Planned leave', 'status': 'approved'},
            )
            Notification.objects.get_or_create(
                user=student.user,
                title=f'Demo Notification {index}',
                defaults={'message': 'This is a sample school notification.', 'is_read': False},
            )
            Holiday.objects.get_or_create(
                year=years[(index - 1) % len(years)],
                holiday_name=f'Demo Holiday {index}',
                defaults={'holiday_type': 'Public', 'holiday_date': date(2026, 7, min(index, 28)), 'description': 'School holiday'},
            )
            SystemSetting.objects.get_or_create(
                setting_key=f'demo_setting_{index}',
                defaults={'setting_value': f'Demo value {index}', 'updated_by': staff[(index - 1) % len(staff)]},
            )

        events = list(Event.objects.order_by('id')[:5])
        for index, event in enumerate(events, start=1):
            EventParticipant.objects.get_or_create(
                event=event,
                student=students[(index - 1) % len(students)],
                defaults={'participation_type': 'Participant'},
            )

    def ensure_audit_logs(self):
        users = list(get_user_model().objects.order_by('id')[:5])

        def create_log(index):
            AuditLog.objects.create(
                action=AuditLog.Action.CREATE,
                model_name='Seed Data',
                object_id=str(index),
                object_repr=f'Sample record batch {index}',
                changed_by=users[(index - 1) % len(users)] if users else None,
                path='/manage/',
                method='SEED',
                status_code=200,
                note='Sample immutable audit log generated by seed_five_records.',
            )

        self.ensure_count(AuditLog, create_log)
