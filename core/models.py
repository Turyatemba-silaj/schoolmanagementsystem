from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        STAFF = 'staff', 'Staff'
        STUDENT = 'student', 'Student'
        GUARDIAN = 'guardian', 'Guardian'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        PENDING = 'pending', 'Pending'
        SUSPENDED = 'suspended', 'Suspended'

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.STUDENT)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username


class Department(TimestampedModel):
    department_name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.department_name


class Staff(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    employee_code = models.CharField(max_length=64, unique=True)
    full_name = models.CharField(max_length=256)
    designation = models.CharField(max_length=128, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    hire_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.full_name


class StaffAttendance(TimestampedModel):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        SICK = 'sick', 'Sick'
        SUSPENDED = 'suspended', 'Suspension'

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance_records')
    attendance_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PRESENT)
    marked_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_staff_attendance',
    )
    replacement_staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_attendance_records',
    )
    replacement_for_staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='covered_attendance_records',
    )
    auto_created_replacement = models.BooleanField(default=False)
    absence_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('staff', 'attendance_date')
        ordering = ('-attendance_date', 'staff__full_name')

    def __str__(self):
        return f"{self.staff} - {self.attendance_date} - {self.status}"


class Payroll(TimestampedModel):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='payroll_records')
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    present_days = models.PositiveIntegerField(default=0)
    sick_days = models.PositiveIntegerField(default=0)
    absent_days = models.PositiveIntegerField(default=0)
    suspension_days = models.PositiveIntegerField(default=0)
    working_days = models.PositiveIntegerField(default=0)
    payable_days = models.PositiveIntegerField(default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_payrolls',
    )
    generated_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=32, default='generated')

    class Meta:
        unique_together = ('staff', 'month', 'year')
        ordering = ('-year', '-month', 'staff__full_name')

    def __str__(self):
        return f"{self.staff} payroll {self.month}/{self.year}"


class Guardian(TimestampedModel):
    full_name = models.CharField(max_length=256)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    occupation = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.full_name


class Student(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    admission_no = models.CharField(max_length=64, unique=True)
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    gender = models.CharField(max_length=32, blank=True)
    dob = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=16, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class StudentGuardian(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='guardian_links')
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE)
    relationship = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = ('student', 'guardian')

    def __str__(self):
        return f"{self.guardian} ({self.relationship})"


class AcademicYear(TimestampedModel):
    year_name = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.year_name


class Term(TimestampedModel):
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='terms')
    term_name = models.CharField(max_length=128)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return f"{self.term_name} ({self.year.year_name})"


class SchoolClass(TimestampedModel):
    class_name = models.CharField(max_length=128)
    class_level = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.class_name


class Stream(TimestampedModel):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='streams')
    stream_name = models.CharField(max_length=128)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return f"{self.stream_name} ({self.school_class.class_name})"


class Enrollment(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    stream = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True)
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    enrollment_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return f"{self.student} - {self.school_class} ({self.year.year_name})"


class Attendance(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    stream = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True)
    attendance_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=32, default='present')

    def __str__(self):
        return f"{self.student} - {self.attendance_date}"


class Subject(TimestampedModel):
    subject_code = models.CharField(max_length=64, unique=True)
    subject_name = models.CharField(max_length=128)
    subject_type = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.subject_name


class ClassSubject(TimestampedModel):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('school_class', 'subject')

    def __str__(self):
        return f"{self.school_class} - {self.subject}"


class Exam(TimestampedModel):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='exams')
    exam_name = models.CharField(max_length=128)
    exam_type = models.CharField(max_length=64, blank=True)
    exam_date = models.DateField()
    max_marks = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=32, default='scheduled')

    def __str__(self):
        return self.exam_name


class ExamResult(TimestampedModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2)
    grade = models.CharField(max_length=16, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('exam', 'student', 'subject')

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.subject}"


class FeesStructure(TimestampedModel):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    fee_type = models.CharField(max_length=128)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.fee_type} - {self.school_class} ({self.term.term_name})"


class FeeDiscount(TimestampedModel):
    fees_structure = models.ForeignKey(FeesStructure, on_delete=models.CASCADE, related_name='discounts')
    discount_type = models.CharField(max_length=128)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    applicable_from = models.DateField(null=True, blank=True)
    applicable_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.discount_type} ({self.discount_value})"


class Payment(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    fees_structure = models.ForeignKey(FeesStructure, on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateField(default=timezone.now)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=64, blank=True)
    transaction_id = models.CharField(max_length=128, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_by = models.CharField(max_length=256, blank=True)
    receipted_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipted_payments',
    )

    def __str__(self):
        return f"{self.student} - {self.amount_paid}"

    def save(self, *args, **kwargs):
        old_group = None
        if self.pk:
            old_group = Payment.objects.filter(pk=self.pk).values('student_id', 'fees_structure_id').first()
        super().save(*args, **kwargs)
        self.recalculate_balances(self.student_id, self.fees_structure_id)
        if old_group and (
            old_group['student_id'] != self.student_id
            or old_group['fees_structure_id'] != self.fees_structure_id
        ):
            self.recalculate_balances(old_group['student_id'], old_group['fees_structure_id'])

    def delete(self, *args, **kwargs):
        student_id = self.student_id
        fees_structure_id = self.fees_structure_id
        result = super().delete(*args, **kwargs)
        self.recalculate_balances(student_id, fees_structure_id)
        return result

    @classmethod
    def recalculate_balances(cls, student_id, fees_structure_id):
        if not student_id or not fees_structure_id:
            return

        payments = list(
            cls.objects.select_related('fees_structure')
            .filter(student_id=student_id, fees_structure_id=fees_structure_id)
            .order_by('payment_date', 'id')
        )
        if not payments:
            return

        expected_amount = payments[0].fees_structure.amount if payments[0].fees_structure else Decimal('0.00')
        cumulative_paid = Decimal('0.00')
        for payment in payments:
            cumulative_paid += payment.amount_paid or Decimal('0.00')
            balance = expected_amount - cumulative_paid
            if balance < 0:
                balance = Decimal('0.00')
            if payment.balance != balance:
                cls.objects.filter(pk=payment.pk).update(balance=balance)


class Receipt(TimestampedModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE)
    receipt_no = models.CharField(max_length=128, unique=True)
    receipt_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.receipt_no


class Account(TimestampedModel):
    class AccountType(models.TextChoices):
        ASSET = 'asset', 'Asset'
        LIABILITY = 'liability', 'Liability'
        EQUITY = 'equity', 'Equity'
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'

    account_code = models.CharField(max_length=32, unique=True)
    account_name = models.CharField(max_length=160)
    account_type = models.CharField(max_length=32, choices=AccountType.choices)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_accounts')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('account_code',)

    def __str__(self):
        return f'{self.account_code} - {self.account_name}'


class JournalEntry(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        VOID = 'void', 'Void'

    entry_no = models.CharField(max_length=64, unique=True, blank=True)
    entry_date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=256)
    reference = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_journal_entries',
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-entry_date', '-id')

    def __str__(self):
        return f'{self.entry_no or "Draft"} - {self.description}'

    def save(self, *args, **kwargs):
        if not self.entry_no:
            year = timezone.localdate().year
            prefix = f'JE{year}'
            last_entry = JournalEntry.objects.filter(entry_no__startswith=prefix).order_by('-entry_no').first()
            if last_entry:
                try:
                    next_number = int(last_entry.entry_no.replace(prefix, '', 1)) + 1
                except ValueError:
                    next_number = JournalEntry.objects.filter(entry_no__startswith=prefix).count() + 1
            else:
                next_number = 1
            self.entry_no = f'{prefix}{next_number:05d}'
        if self.status == self.Status.POSTED and self.posted_at is None:
            self.posted_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def total_debit(self):
        return sum((line.debit for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_credit(self):
        return sum((line.credit for line in self.lines.all()), Decimal('0.00'))

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalLine(TimestampedModel):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(max_length=256, blank=True)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ('journal_entry', 'id')

    def __str__(self):
        amount = self.debit if self.debit else self.credit
        side = 'Dr' if self.debit else 'Cr'
        return f'{self.journal_entry.entry_no} - {self.account} {side} {amount}'

    def clean(self):
        if self.debit and self.credit:
            raise ValidationError('A journal line cannot have both debit and credit amounts.')
        if not self.debit and not self.credit:
            raise ValidationError('A journal line must have either a debit or a credit amount.')


class Supplier(TimestampedModel):
    supplier_name = models.CharField(max_length=256)
    contact_person = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_number = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, default='active')

    class Meta:
        ordering = ('supplier_name',)

    def __str__(self):
        return self.supplier_name


class Invoice(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ISSUED = 'issued', 'Issued'
        PART_PAID = 'part_paid', 'Part Paid'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    invoice_no = models.CharField(max_length=64, unique=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=256)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ('-invoice_date', '-id')

    def __str__(self):
        return f'{self.invoice_no or "Draft invoice"} - {self.description}'

    @property
    def balance(self):
        balance = (self.amount or Decimal('0.00')) - (self.amount_paid or Decimal('0.00'))
        return balance if balance > 0 else Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            year = timezone.localdate().year
            prefix = f'INV{year}'
            last_invoice = Invoice.objects.filter(invoice_no__startswith=prefix).order_by('-invoice_no').first()
            if last_invoice:
                try:
                    next_number = int(last_invoice.invoice_no.replace(prefix, '', 1)) + 1
                except ValueError:
                    next_number = Invoice.objects.filter(invoice_no__startswith=prefix).count() + 1
            else:
                next_number = 1
            self.invoice_no = f'{prefix}{next_number:05d}'
        if self.amount_paid and self.amount_paid >= self.amount:
            self.status = self.Status.PAID
        elif self.amount_paid:
            self.status = self.Status.PART_PAID
        super().save(*args, **kwargs)


class Expense(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        PAID = 'paid', 'Paid'
        REJECTED = 'rejected', 'Rejected'

    expense_no = models.CharField(max_length=64, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='expenses')
    expense_date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=256)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=64, blank=True)
    reference = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses',
    )

    class Meta:
        ordering = ('-expense_date', '-id')

    def __str__(self):
        return f'{self.expense_no or "Draft expense"} - {self.description}'

    def save(self, *args, **kwargs):
        if not self.expense_no:
            year = timezone.localdate().year
            prefix = f'EXP{year}'
            last_expense = Expense.objects.filter(expense_no__startswith=prefix).order_by('-expense_no').first()
            if last_expense:
                try:
                    next_number = int(last_expense.expense_no.replace(prefix, '', 1)) + 1
                except ValueError:
                    next_number = Expense.objects.filter(expense_no__startswith=prefix).count() + 1
            else:
                next_number = 1
            self.expense_no = f'{prefix}{next_number:05d}'
        super().save(*args, **kwargs)


class AuditLogQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError('Audit logs are immutable and cannot be deleted.')

    def update(self, **kwargs):
        raise ValidationError('Audit logs are immutable and cannot be edited.')


def current_local_time():
    return timezone.localtime().time()


class AuditLog(TimestampedModel):
    class Action(models.TextChoices):
        VIEW = 'view', 'View'
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        POST = 'post', 'Post'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        SECURITY = 'security', 'Security'

    action = models.CharField(max_length=32, choices=Action.choices)
    model_name = models.CharField(max_length=128)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=256)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    path = models.CharField(max_length=256, blank=True)
    method = models.CharField(max_length=12, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)
    note = models.TextField(blank=True)
    activity_date = models.DateField(default=timezone.localdate)
    activity_time = models.TimeField(default=current_local_time)
    created_at = models.DateTimeField(default=timezone.now)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.get_action_display()} {self.model_name} {self.object_id}'

    def delete(self, *args, **kwargs):
        raise ValidationError('Audit logs are immutable and cannot be deleted.')

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValidationError('Audit logs are immutable and cannot be edited.')
        local_now = timezone.localtime()
        self.activity_date = self.activity_date or local_now.date()
        self.activity_time = self.activity_time or local_now.time()
        super().save(*args, **kwargs)


class LibraryBook(TimestampedModel):
    isbn = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=256)
    author = models.CharField(max_length=256, blank=True)
    publisher = models.CharField(max_length=256, blank=True)
    category = models.CharField(max_length=128, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    available_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default='available')

    def __str__(self):
        return self.title


class BookBorrowing(TimestampedModel):
    book = models.ForeignKey(LibraryBook, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=32, default='borrowed')

    def __str__(self):
        return f"{self.book} - {self.student}"


class Hostel(TimestampedModel):
    hostel_name = models.CharField(max_length=256)
    gender_type = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.hostel_name


class HostelRoom(TimestampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    room_no = models.CharField(max_length=64)
    room_name = models.CharField(max_length=128, blank=True)
    capacity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=32, default='available')

    def __str__(self):
        return f"{self.room_no} - {self.hostel.hostel_name}"


class HostelAllocation(TimestampedModel):
    room = models.ForeignKey(HostelRoom, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    allocation_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return f"{self.student} - {self.room}"


class TransportRoute(TimestampedModel):
    route_name = models.CharField(max_length=256)
    start_point = models.CharField(max_length=256, blank=True)
    end_point = models.CharField(max_length=256, blank=True)
    distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    route_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.route_name


class Vehicle(TimestampedModel):
    vehicle_no = models.CharField(max_length=128, unique=True)
    driver_name = models.CharField(max_length=256, blank=True)
    driver_phone = models.CharField(max_length=32, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.vehicle_no


class TransportAllocation(TimestampedModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    allocation_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return f"{self.student} - {self.vehicle}"


class OnlineApplication(TimestampedModel):
    application_no = models.CharField(max_length=128, unique=True)
    applicant_name = models.CharField(max_length=256)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    previous_school = models.CharField(max_length=256, blank=True)
    applied_class = models.ForeignKey(SchoolClass, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=32, default='pending')
    application_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.application_no

    def save(self, *args, **kwargs):
        if not self.application_no:
            self.application_no = self.generate_application_no()
        super().save(*args, **kwargs)

    @classmethod
    def generate_application_no(cls):
        year = timezone.localdate().year
        prefix = f'APP{year}'
        last_application = cls.objects.filter(application_no__startswith=prefix).order_by('-application_no').first()
        if last_application:
            try:
                next_number = int(last_application.application_no.replace(prefix, '', 1)) + 1
            except ValueError:
                next_number = cls.objects.filter(application_no__startswith=prefix).count() + 1
        else:
            next_number = 1

        application_no = f'{prefix}{next_number:04d}'
        while cls.objects.filter(application_no=application_no).exists():
            next_number += 1
            application_no = f'{prefix}{next_number:04d}'
        return application_no


class ApplicationRequirement(TimestampedModel):
    requirement_name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    applied_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, null=True, blank=True)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default='active')

    class Meta:
        ordering = ('sort_order', 'requirement_name')
        unique_together = ('requirement_name', 'applied_class')

    def __str__(self):
        if self.applied_class:
            return f'{self.requirement_name} - {self.applied_class}'
        return self.requirement_name


class ApplicationRequirementCheck(TimestampedModel):
    application = models.ForeignKey(OnlineApplication, on_delete=models.CASCADE, related_name='requirement_checks')
    requirement = models.ForeignKey(ApplicationRequirement, on_delete=models.CASCADE)
    is_satisfied = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('requirement__sort_order', 'requirement__requirement_name')
        unique_together = ('application', 'requirement')

    def __str__(self):
        status = 'Satisfied' if self.is_satisfied else 'Pending'
        return f'{self.application.application_no} - {self.requirement.requirement_name} - {status}'


class ApplicationDocument(TimestampedModel):
    application = models.ForeignKey(OnlineApplication, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=128)
    file_path = models.FileField(upload_to='application_documents/')
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.document_type} - {self.application.application_no}"


class Admission(TimestampedModel):
    application = models.ForeignKey(OnlineApplication, on_delete=models.SET_NULL, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    admission_date = models.DateField(default=timezone.now)
    admission_no = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=32, default='active')

    def __str__(self):
        return self.admission_no


class Document(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=128)
    file_path = models.FileField(upload_to='student_documents/')
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.document_type


class Event(TimestampedModel):
    event_title = models.CharField(max_length=256)
    event_type = models.CharField(max_length=128, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True)
    organized_by = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.event_title


class EventParticipant(TimestampedModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    participation_type = models.CharField(max_length=128, blank=True)

    class Meta:
        unique_together = ('event', 'student')

    def __str__(self):
        return f"{self.student} - {self.event}"


class HealthRecord(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    medical_condition = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    medication = models.TextField(blank=True)
    doctor_name = models.CharField(max_length=256, blank=True)
    record_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Health record for {self.student}"


class DisciplineRecord(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    recorded_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    offence_type = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    record_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=32, default='open')

    def __str__(self):
        return f"{self.student} - {self.offence_type}"


class Leave(TimestampedModel):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=128)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=32, default='pending')
    applied_on = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.staff} - {self.leave_type}"


class Notification(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=256)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Holiday(TimestampedModel):
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    holiday_type = models.CharField(max_length=128)
    holiday_name = models.CharField(max_length=256)
    holiday_date = models.DateField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.holiday_name


class SystemSetting(TimestampedModel):
    updated_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    setting_key = models.CharField(max_length=128)
    setting_value = models.TextField()
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.setting_key
