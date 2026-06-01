from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.db import transaction
from django.forms import modelform_factory
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from .forms import (
    ApplicationForm,
    BootstrapModelForm,
    ClassForm,
    PayeeLoginForm,
    PayeePaymentForm,
    PaymentForm,
    StaffForm,
    StudentForm,
)
from .models import (
    AcademicYear,
    Admission,
    ApplicationRequirement,
    ApplicationRequirementCheck,
    ApplicationDocument,
    Attendance,
    BookBorrowing,
    ClassSubject,
    Department,
    DisciplineRecord,
    Document,
    Event,
    EventParticipant,
    Guardian,
    FeesStructure,
    FeeDiscount,
    HealthRecord,
    Hostel,
    HostelAllocation,
    HostelRoom,
    Account,
    AuditLog,
    Expense,
    Invoice,
    JournalEntry,
    JournalLine,
    Holiday,
    LibraryBook,
    OnlineApplication,
    Payment,
    Receipt,
    SchoolClass,
    Stream,
    Student,
    StudentGuardian,
    Staff,
    StaffAttendance,
    Payroll,
    Supplier,
    Enrollment,
    Subject,
    SystemSetting,
    Term,
    TransportAllocation,
    TransportRoute,
    Vehicle,
    Exam,
    ExamResult,
    Leave,
    Notification,
)


class HomeView(TemplateView):
    template_name = 'core/home.html'


def bundled_asset(request, asset_name):
    asset_map = {
        'site.css': ('static/core/css/site.css', 'text/css'),
        'muslim-school-hero.png': ('static/core/img/muslim-school-hero.png', 'image/png'),
    }
    try:
        relative_path, content_type = asset_map[asset_name]
    except KeyError:
        raise Http404('Asset not found')

    asset_path = settings.BASE_DIR / relative_path
    if not asset_path.exists():
        raise Http404('Asset not found')

    response = FileResponse(asset_path.open('rb'), content_type=content_type)
    response['Cache-Control'] = 'public, max-age=300'
    return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_count'] = Student.objects.count()
        context['staff_count'] = Staff.objects.count()
        context['class_count'] = SchoolClass.objects.count()
        context['application_count'] = OnlineApplication.objects.count()
        context['department_count'] = Department.objects.count()
        context['subject_count'] = Subject.objects.count()
        context['pending_application_count'] = OnlineApplication.objects.filter(status='pending').count()
        context['attendance_present_count'] = Attendance.objects.filter(status='present').count()
        context['attendance_absent_count'] = Attendance.objects.filter(status='absent').count()
        context['attendance_sick_count'] = Attendance.objects.filter(status='sick').count()
        context['attendance_suspended_count'] = Attendance.objects.filter(status='suspended').count()
        context['total_payments'] = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
        context['total_balance'] = Payment.objects.aggregate(total=Sum('balance'))['total'] or 0
        context['average_score'] = ExamResult.objects.aggregate(avg=Avg('marks_obtained'))['avg'] or 0
        context['recent_students'] = Student.objects.select_related('user').order_by('-created_at')[:5]
        context['recent_payments'] = Payment.objects.select_related('student', 'fees_structure').order_by('-payment_date')[:5]
        context['upcoming_events'] = Event.objects.order_by('start_date')[:5]
        context['class_overview'] = SchoolClass.objects.annotate(
            enrollment_count=Count('enrollment'),
            subject_count=Count('classsubject', distinct=True),
            fee_count=Count('feesstructure', distinct=True),
        ).order_by('class_level', 'class_name')
        application_statuses = OnlineApplication.objects.values('status').annotate(total=Count('id')).order_by('status')
        context['dashboard_charts'] = {
            'overview': {
                'labels': ['Students', 'Staff', 'Classes', 'Applications'],
                'values': [
                    context['student_count'],
                    context['staff_count'],
                    context['class_count'],
                    context['application_count'],
                ],
            },
            'attendance': {
                'labels': ['Present', 'Absent', 'Sick', 'Suspended'],
                'values': [
                    context['attendance_present_count'],
                    context['attendance_absent_count'],
                    context['attendance_sick_count'],
                    context['attendance_suspended_count'],
                ],
            },
            'finance': {
                'labels': ['Paid', 'Balance'],
                'values': [float(context['total_payments']), float(context['total_balance'])],
            },
            'applications': {
                'labels': [row['status'].title() for row in application_statuses],
                'values': [row['total'] for row in application_statuses],
            },
            'classes': {
                'labels': [school_class.class_name for school_class in context['class_overview']],
                'values': [school_class.enrollment_count for school_class in context['class_overview']],
            },
        }
        return context


class FinanceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/finance_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_income = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_expenses = Expense.objects.filter(status__in=['approved', 'paid']).aggregate(total=Sum('amount'))['total'] or 0
        outstanding_fees = Payment.objects.aggregate(total=Sum('balance'))['total'] or 0
        invoice_total = Invoice.objects.aggregate(total=Sum('amount'))['total'] or 0
        invoice_paid = Invoice.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
        pending_expenses = Expense.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

        account_rows = []
        for account in Account.objects.filter(is_active=True).order_by('account_code'):
            totals = account.journal_lines.aggregate(debit=Sum('debit'), credit=Sum('credit'))
            debit = totals['debit'] or 0
            credit = totals['credit'] or 0
            balance = debit - credit
            if account.account_type in [Account.AccountType.LIABILITY, Account.AccountType.EQUITY, Account.AccountType.INCOME]:
                balance = credit - debit
            account_rows.append({
                'account': account,
                'debit': debit,
                'credit': credit,
                'balance': balance,
            })

        context.update({
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_position': total_income - total_expenses,
            'outstanding_fees': outstanding_fees,
            'invoice_total': invoice_total,
            'invoice_paid': invoice_paid,
            'invoice_balance': invoice_total - invoice_paid,
            'pending_expenses': pending_expenses,
            'recent_payments': Payment.objects.select_related('student').order_by('-payment_date', '-id')[:6],
            'recent_expenses': Expense.objects.select_related('supplier', 'account').order_by('-expense_date', '-id')[:6],
            'recent_journals': JournalEntry.objects.order_by('-entry_date', '-id')[:6],
            'recent_audits': AuditLog.objects.select_related('changed_by').order_by('-created_at')[:8],
            'account_rows': account_rows,
        })
        return context


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'core/student_list.html'
    context_object_name = 'students'

    def get_queryset(self):
        return Student.objects.select_related('user').prefetch_related(
            'enrollments__school_class',
            'enrollments__stream',
        )


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'core/student_detail.html'
    context_object_name = 'student'

    def get_queryset(self):
        return Student.objects.select_related('user').prefetch_related(
            'guardian_links__guardian',
            'enrollments__school_class',
            'enrollments__stream',
            'enrollments__year',
            'documents',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        context['guardians'] = StudentGuardian.objects.select_related('guardian').filter(student=student)
        context['enrollments'] = Enrollment.objects.select_related('school_class', 'stream', 'year').filter(student=student)
        context['attendance_records'] = Attendance.objects.select_related('school_class', 'stream').filter(student=student).order_by('-attendance_date')[:10]
        context['exam_results'] = ExamResult.objects.select_related('exam', 'subject').filter(student=student).order_by('-exam__exam_date')[:10]
        context['payments'] = Payment.objects.select_related('fees_structure').filter(student=student).order_by('-payment_date')[:10]
        context['documents'] = Document.objects.filter(student=student).order_by('-uploaded_at')[:10]
        context['borrowings'] = BookBorrowing.objects.select_related('book').filter(student=student).order_by('-issue_date')[:10]
        context['hostel_allocations'] = HostelAllocation.objects.select_related('room', 'room__hostel').filter(student=student).order_by('-allocation_date')[:5]
        context['transport_allocations'] = TransportAllocation.objects.select_related('vehicle').filter(student=student).order_by('-allocation_date')[:5]
        context['health_records'] = HealthRecord.objects.filter(student=student).order_by('-record_date')[:5]
        context['discipline_records'] = DisciplineRecord.objects.select_related('recorded_by').filter(student=student).order_by('-record_date')[:5]
        context['fee_total_paid'] = Payment.objects.filter(student=student).aggregate(total=Sum('amount_paid'))['total'] or 0
        context['fee_total_balance'] = Payment.objects.filter(student=student).aggregate(total=Sum('balance'))['total'] or 0
        return context


class StudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/student_form.html'
    success_url = reverse_lazy('student_list')


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/student_form.html'
    success_url = reverse_lazy('student_list')


class StaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'core/staff_list.html'
    context_object_name = 'staff_members'


class StaffDetailView(LoginRequiredMixin, DetailView):
    model = Staff
    template_name = 'core/staff_detail.html'
    context_object_name = 'staff'

    def get_queryset(self):
        return Staff.objects.select_related('user', 'department')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff = self.object
        context['class_subjects'] = ClassSubject.objects.select_related('school_class', 'subject').filter(staff=staff)
        context['approved_admissions'] = Admission.objects.select_related('student', 'application').filter(approved_by=staff).order_by('-admission_date')[:10]
        context['leave_records'] = Leave.objects.filter(staff=staff).order_by('-applied_on')[:10]
        context['discipline_records'] = DisciplineRecord.objects.select_related('student').filter(recorded_by=staff).order_by('-record_date')[:10]
        context['attendance_records'] = StaffAttendance.objects.select_related('marked_by').filter(staff=staff).order_by('-attendance_date')[:10]
        context['payroll_records'] = Payroll.objects.filter(staff=staff).order_by('-year', '-month')[:10]
        return context


class StaffCreateView(LoginRequiredMixin, CreateView):
    model = Staff
    form_class = StaffForm
    template_name = 'core/staff_form.html'
    success_url = reverse_lazy('staff_list')


class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = 'core/staff_form.html'
    success_url = reverse_lazy('staff_list')


class ClassListView(LoginRequiredMixin, ListView):
    model = SchoolClass
    template_name = 'core/class_list.html'
    context_object_name = 'classes'

    def get_queryset(self):
        return SchoolClass.objects.annotate(
            enrollment_count=Count('enrollment'),
            stream_count=Count('streams', distinct=True),
            subject_count=Count('classsubject', distinct=True),
        ).order_by('class_level', 'class_name')


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = SchoolClass
    template_name = 'core/class_detail.html'
    context_object_name = 'school_class'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_class = self.object
        context['streams'] = Stream.objects.filter(school_class=school_class)
        context['subjects'] = ClassSubject.objects.select_related('subject', 'staff').filter(school_class=school_class)
        context['enrollments'] = Enrollment.objects.select_related('student', 'stream', 'year').filter(school_class=school_class)
        context['fees'] = FeesStructure.objects.select_related('term').filter(school_class=school_class)
        context['attendance_records'] = Attendance.objects.select_related('student', 'stream').filter(school_class=school_class).order_by('-attendance_date')[:10]
        return context


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = SchoolClass
    form_class = ClassForm
    template_name = 'core/class_form.html'
    success_url = reverse_lazy('class_list')


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = SchoolClass
    form_class = ClassForm
    template_name = 'core/class_form.html'
    success_url = reverse_lazy('class_list')


class ApplicationListView(LoginRequiredMixin, ListView):
    model = OnlineApplication
    template_name = 'core/application_list.html'
    context_object_name = 'applications'

    def get_queryset(self):
        return OnlineApplication.objects.select_related('applied_class').order_by('-application_date')


class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = OnlineApplication
    template_name = 'core/application_detail.html'
    context_object_name = 'application'

    def get_queryset(self):
        return OnlineApplication.objects.select_related('applied_class')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.object
        context['documents'] = ApplicationDocument.objects.filter(application=application).order_by('-uploaded_at')
        context['admissions'] = Admission.objects.select_related('student', 'approved_by').filter(application=application).order_by('-admission_date')
        context['requirement_checks'] = get_application_requirement_checks(application)
        context['requirements_satisfied'] = application_requirements_satisfied(application)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        if action == 'save_requirements':
            update_application_requirement_checks(self.object, request)
            messages.success(request, 'Application requirements updated.')
            return redirect('application_detail', pk=self.object.pk)
        if action == 'issue_admission':
            try:
                admission = admit_application(self.object, request)
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages))
            else:
                messages.success(
                    request,
                    f'Admission number {admission.admission_no} issued and student record created.',
                )
            return redirect('application_detail', pk=self.object.pk)
        return super().get(request, *args, **kwargs)


class ApplicationCreateView(CreateView):
    model = OnlineApplication
    form_class = ApplicationForm
    template_name = 'core/application_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        save_application_document_from_form(self.object, form)
        log_audit(AuditLog.Action.CREATE, self.object, self.request, 'Online application created.')
        messages.success(self.request, f'Application {self.object.application_no} submitted for review.')
        return response

    def get_success_url(self):
        if not self.request.user.is_authenticated:
            return reverse_lazy('home')
        return reverse_lazy('application_detail', kwargs={'pk': self.object.pk})


class ApplicationUpdateView(LoginRequiredMixin, UpdateView):
    model = OnlineApplication
    form_class = ApplicationForm
    template_name = 'core/application_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        save_application_document_from_form(self.object, form)
        log_audit(AuditLog.Action.UPDATE, self.object, self.request, 'Online application updated.')
        return response

    def get_success_url(self):
        return reverse_lazy('application_detail', kwargs={'pk': self.object.pk})


def application_requirements_for(application):
    return ApplicationRequirement.objects.filter(status='active').filter(
        Q(applied_class__isnull=True) | Q(applied_class=application.applied_class)
    ).order_by('sort_order', 'requirement_name')


def get_application_requirement_checks(application):
    requirements = application_requirements_for(application)
    checks = {
        check.requirement_id: check
        for check in ApplicationRequirementCheck.objects.select_related('requirement').filter(
            application=application,
            requirement__in=requirements,
        )
    }
    rows = []
    for requirement in requirements:
        check = checks.get(requirement.id)
        if check is None:
            check = ApplicationRequirementCheck.objects.create(
                application=application,
                requirement=requirement,
            )
        rows.append(check)
    return rows


def application_requirements_satisfied(application):
    checks = get_application_requirement_checks(application)
    required_checks = [check for check in checks if check.requirement.is_required]
    return bool(required_checks) and all(check.is_satisfied for check in required_checks)


def update_application_requirement_checks(application, request):
    reviewer = get_current_staff(request.user)
    for check in get_application_requirement_checks(application):
        check.is_satisfied = request.POST.get(f'requirement_{check.requirement_id}') == 'on'
        check.note = request.POST.get(f'note_{check.requirement_id}', '').strip()
        check.reviewed_by = reviewer
        check.reviewed_at = timezone.now()
        check.save()
    log_audit(AuditLog.Action.UPDATE, application, request, 'Application requirement checklist reviewed.')


def save_application_document_from_form(application, form):
    document_type = form.cleaned_data.get('document_type')
    document_file = form.cleaned_data.get('document_file')
    if not document_type or not document_file:
        return
    ApplicationDocument.objects.create(
        application=application,
        document_type=document_type,
        file_path=document_file,
    )
    matching_requirements = application_requirements_for(application).filter(requirement_name__iexact=document_type)
    for requirement in matching_requirements:
        ApplicationRequirementCheck.objects.update_or_create(
            application=application,
            requirement=requirement,
            defaults={
                'is_satisfied': True,
                'note': 'Supporting document uploaded with the application.',
                'reviewed_at': timezone.now(),
            },
        )


def generate_admission_no():
    year = timezone.localdate().year
    prefix = f'ADM{year}-'
    last_student = Student.objects.filter(admission_no__startswith=prefix).order_by('-admission_no').first()
    if last_student:
        try:
            next_number = int(last_student.admission_no.replace(prefix, '', 1)) + 1
        except ValueError:
            next_number = Student.objects.filter(admission_no__startswith=prefix).count() + 1
    else:
        next_number = 1

    admission_no = f'{prefix}{next_number:04d}'
    while Student.objects.filter(admission_no=admission_no).exists() or Admission.objects.filter(admission_no=admission_no).exists():
        next_number += 1
        admission_no = f'{prefix}{next_number:04d}'
    return admission_no


def unique_student_username(admission_no):
    UserModel = get_user_model()
    username = admission_no.lower()
    if not UserModel.objects.filter(username=username).exists():
        return username
    counter = 2
    while UserModel.objects.filter(username=f'{username}-{counter}').exists():
        counter += 1
    return f'{username}-{counter}'


@transaction.atomic
def admit_application(application, request):
    if Admission.objects.filter(application=application).exists():
        raise ValidationError('This application already has an admission record.')
    if not application_requirements_satisfied(application):
        raise ValidationError('Admission cannot be issued until all required school requirements are satisfied.')

    admission_no = generate_admission_no()
    name_parts = application.applicant_name.split()
    first_name = name_parts[0] if name_parts else application.applicant_name
    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

    UserModel = get_user_model()
    user = UserModel(
        username=unique_student_username(admission_no),
        first_name=first_name,
        last_name=last_name,
        role=UserModel.Role.STUDENT,
        status=UserModel.Status.ACTIVE,
    )
    user.set_unusable_password()
    user.save()

    student = Student.objects.create(
        user=user,
        admission_no=admission_no,
        first_name=first_name,
        last_name=last_name,
        gender=application.gender,
        dob=application.dob,
        status='active',
    )

    academic_year = AcademicYear.objects.filter(status='active').order_by('-start_date', '-id').first()
    if academic_year is None:
        academic_year = AcademicYear.objects.order_by('-start_date', '-id').first()
    if application.applied_class and academic_year:
        Enrollment.objects.create(
            student=student,
            school_class=application.applied_class,
            year=academic_year,
            status='active',
        )

    admission = Admission.objects.create(
        application=application,
        student=student,
        approved_by=get_current_staff(request.user),
        admission_no=admission_no,
        status='active',
    )
    application.status = 'admitted'
    application.save(update_fields=['status', 'updated_at'])
    log_audit(AuditLog.Action.CREATE, admission, request, 'Application admitted after all requirements were satisfied.')
    return admission


def latest_payment_for_student(student):
    return Payment.objects.select_related(
        'fees_structure',
        'fees_structure__school_class',
        'receipted_by',
    ).filter(student=student).order_by('-payment_date', '-id').first()


def current_fee_structure_for_student(student):
    enrollment = Enrollment.objects.filter(student=student).order_by('-enrollment_date', '-id').first()
    if not enrollment:
        return None
    return FeesStructure.objects.filter(school_class=enrollment.school_class).order_by('-created_at', '-id').first()


def payment_summary_for_student(student):
    fees_structure = current_fee_structure_for_student(student)
    payments = Payment.objects.select_related('fees_structure').filter(student=student)
    if fees_structure:
        payments = payments.filter(fees_structure=fees_structure)
    payments = payments.order_by('-payment_date', '-id')
    latest_payment = payments.first()
    total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
    expected_fees = fees_structure.amount if fees_structure else 0
    balance = latest_payment.balance if latest_payment else expected_fees
    return {
        'fees_structure': fees_structure,
        'payments': payments,
        'latest_payment': latest_payment,
        'expected_fees': expected_fees,
        'total_paid': total_paid,
        'balance': balance,
        'fees_cleared': bool(fees_structure and balance <= 0),
    }


def guardians_for_student(student):
    return StudentGuardian.objects.select_related('guardian').filter(student=student)


def create_fee_reminder(student, request=None):
    payment = latest_payment_for_student(student)
    balance = payment.balance if payment else 0
    guardian_names = ', '.join(link.guardian.full_name for link in guardians_for_student(student)) or 'Guardian'
    message = (
        f'Dear {guardian_names}, please clear the outstanding school fees balance '
        f'of {balance} for {student} ({student.admission_no}) on time.'
    )
    Notification.objects.create(
        user=student.user,
        title='School fees payment reminder',
        message=message,
    )
    if request:
        messages.success(request, f'Reminder created for {student}.')


def log_audit(action, obj, request=None, note=''):
    AuditLog.objects.create(
        action=action,
        model_name=obj._meta.verbose_name.title(),
        object_id=str(obj.pk or ''),
        object_repr=str(obj)[:256],
        changed_by=request.user if request and request.user.is_authenticated else None,
        path=request.path[:256] if request else '',
        method=request.method[:12] if request else '',
        ip_address=request.META.get('REMOTE_ADDR') if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:256] if request else '',
        note=note,
    )


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'core/payment_list.html'
    context_object_name = 'payments'

    def get_queryset(self):
        return Payment.objects.select_related(
            'student',
            'fees_structure',
            'fees_structure__school_class',
            'receipted_by',
        ).order_by('-payment_date', '-id')

    def post(self, request, *args, **kwargs):
        student = Student.objects.filter(pk=request.POST.get('student_id')).first()
        if student:
            create_fee_reminder(student, request)
        else:
            messages.error(request, 'Could not create reminder because the student was not found.')
        return redirect('payment_list')


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'core/payment_form.html'
    success_url = reverse_lazy('payment_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(AuditLog.Action.CREATE, self.object, self.request, 'Student payment recorded.')
        return response


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'core/payment_form.html'
    success_url = reverse_lazy('payment_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(AuditLog.Action.UPDATE, self.object, self.request, 'Student payment updated.')
        return response


def payee_login(request):
    if request.method == 'POST':
        form = PayeeLoginForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student_number']
            request.session['payee_student_id'] = student.pk
            messages.success(request, f'Welcome. Payments are now linked to {student.admission_no}.')
            return redirect('payee_payments')
    else:
        form = PayeeLoginForm()
    return render(request, 'core/payee_login.html', {'form': form})


def payee_logout(request):
    request.session.pop('payee_student_id', None)
    messages.success(request, 'Payee session closed.')
    return redirect('home')


def payee_payments(request):
    student_id = request.session.get('payee_student_id')
    student = Student.objects.filter(pk=student_id).first()
    if not student:
        messages.error(request, 'Enter the student number before making a payment.')
        return redirect('payee_login')

    summary = payment_summary_for_student(student)
    if request.method == 'POST':
        form = PayeePaymentForm(request.POST)
        if form.is_valid():
            if not summary['fees_structure']:
                messages.error(request, 'This student has no active fee structure, so payment cannot be captured automatically.')
                return redirect('payee_payments')

            Payment.objects.create(
                student=student,
                fees_structure=summary['fees_structure'],
                payment_date=timezone.localdate(),
                amount_paid=form.cleaned_data['amount_paid'],
                payment_method=form.cleaned_data['payment_method'],
                transaction_id=form.cleaned_data['payment_reference_number'].strip(),
                paid_by=form.cleaned_data['paid_by'].strip(),
            )
            updated_summary = payment_summary_for_student(student)
            if updated_summary['fees_cleared']:
                messages.success(request, 'Payment captured. Fees are cleared and the report card is ready for authorized staff printing.')
            else:
                messages.success(request, f'Payment captured automatically. Current balance is {updated_summary["balance"]}.')
            return redirect('payee_payments')
    else:
        form = PayeePaymentForm()

    context = {
        'student': student,
        'form': form,
        **summary,
    }
    return render(request, 'core/payee_payments.html', context)


class ExamResultListView(LoginRequiredMixin, ListView):
    model = ExamResult
    template_name = 'core/exam_result_list.html'
    context_object_name = 'exam_results'

    def get_queryset(self):
        return ExamResult.objects.select_related('exam', 'student', 'subject').order_by('-exam__exam_date', 'student__first_name')

    def post(self, request, *args, **kwargs):
        student = Student.objects.filter(pk=request.POST.get('student_id')).first()
        if student:
            create_fee_reminder(student, request)
        else:
            messages.error(request, 'Could not create reminder because the student was not found.')
        return redirect('exam_result_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam_results = list(context['exam_results'])
        student_ids = [result.student_id for result in exam_results]
        latest_payments = {}
        for payment in Payment.objects.select_related('fees_structure', 'fees_structure__school_class').filter(student_id__in=student_ids).order_by('student_id', '-payment_date', '-id'):
            latest_payments.setdefault(payment.student_id, payment)
        context['exam_rows'] = [
            {
                'result': result,
                'payment': latest_payments.get(result.student_id),
                'is_cleared': bool(latest_payments.get(result.student_id) and latest_payments[result.student_id].balance <= 0),
            }
            for result in exam_results
        ]
        return context


class ReportCardIndexView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'core/report_card_index.html'
    context_object_name = 'students'

    def get_queryset(self):
        return Student.objects.select_related('user').prefetch_related('enrollments__school_class', 'enrollments__stream').order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        students = list(context['students'])
        student_ids = [student.id for student in students]
        result_counts = ExamResult.objects.filter(student_id__in=student_ids).values('student_id').annotate(total=Count('id'))
        result_count_map = {row['student_id']: row['total'] for row in result_counts}
        latest_payments = {}
        for payment in Payment.objects.filter(student_id__in=student_ids).order_by('student_id', '-payment_date', '-id'):
            latest_payments.setdefault(payment.student_id, payment)
        context['student_rows'] = []
        for student in students:
            enrollment = student.enrollments.all()[0] if student.enrollments.all() else None
            payment = latest_payments.get(student.id)
            context['student_rows'].append({
                'student': student,
                'enrollment': enrollment,
                'result_count': result_count_map.get(student.id, 0),
                'latest_payment': payment,
                'fees_cleared': bool(payment and payment.balance <= 0),
            })
        return context


def build_report_card_context(student):
    latest_payment = latest_payment_for_student(student)
    fees_cleared = bool(latest_payment and latest_payment.balance <= 0)
    context = {
        'latest_payment': latest_payment,
        'fees_cleared': fees_cleared,
        'generated_on': timezone.localdate(),
    }
    if not fees_cleared:
        return context

    exam_results = ExamResult.objects.select_related('exam', 'subject').filter(student=student).order_by('subject__subject_name', '-exam__exam_date')
    attendance = Attendance.objects.filter(student=student)
    context.update({
        'guardians': StudentGuardian.objects.select_related('guardian').filter(student=student),
        'enrollment': Enrollment.objects.select_related('school_class', 'stream', 'year').filter(student=student).order_by('-enrollment_date').first(),
        'exam_results': exam_results,
        'total_marks': exam_results.aggregate(total=Sum('marks_obtained'))['total'] or 0,
        'average_mark': exam_results.aggregate(avg=Avg('marks_obtained'))['avg'] or 0,
        'attendance_present': attendance.filter(status='present').count(),
        'attendance_absent': attendance.filter(status='absent').count(),
        'attendance_sick': attendance.filter(status='sick').count(),
        'attendance_suspended': attendance.filter(status='suspended').count(),
    })
    return context


class ReportCardDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'core/report_card_detail.html'
    context_object_name = 'student'

    def get_queryset(self):
        return Student.objects.select_related('user').prefetch_related(
            'guardian_links__guardian',
            'enrollments__school_class',
            'enrollments__stream',
            'enrollments__year',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_report_card_context(self.object))
        return context


def report_card_pdf_response(student, context):
    buffer = BytesIO()
    safe_admission_no = ''.join(char for char in student.admission_no if char.isalnum() or char in ('-', '_'))
    filename = f'report-card-{safe_admission_no or student.pk}.pdf'
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title=f'{student} Report Card',
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph('Kyabuza Muslim Secondary School', styles['Title']),
        Paragraph('Official Student Report Card', styles['Heading2']),
        Paragraph(f'Generated on {context["generated_on"]}', styles['Normal']),
        Spacer(1, 0.18 * inch),
    ]

    guardians = ', '.join(link.guardian.full_name for link in context['guardians']) or '-'
    enrollment = context['enrollment']
    student_details = [
        ['Student Name', str(student), 'Admission No.', student.admission_no],
        ['Class', str(enrollment.school_class) if enrollment else '-', 'Stream', str(enrollment.stream) if enrollment and enrollment.stream else '-'],
        ['Academic Year', str(enrollment.year) if enrollment else '-', 'Gender', student.gender or '-'],
        ['Guardian', guardians, 'Fee Status', 'Cleared'],
    ]
    story.append(Table(student_details, colWidths=[1.25 * inch, 2.2 * inch, 1.25 * inch, 2.2 * inch], style=[
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b9c8d8')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef5fc')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#eef5fc')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(Spacer(1, 0.18 * inch))

    result_rows = [['Subject', 'Exam', 'Exam Date', 'Max', 'Marks', 'Grade', 'Remarks']]
    for result in context['exam_results']:
        result_rows.append([
            str(result.subject),
            result.exam.exam_name,
            str(result.exam.exam_date),
            str(result.exam.max_marks),
            str(result.marks_obtained),
            result.grade or '-',
            Paragraph(result.remarks or '-', styles['BodyText']),
        ])
    if len(result_rows) == 1:
        result_rows.append(['No exam results found.', '', '', '', '', '', ''])
    result_rows.append(['Total / Average', '', '', '', str(context['total_marks']), f'Average: {context["average_mark"]:.1f}', ''])
    story.extend([
        Paragraph('Exam Results', styles['Heading2']),
        Table(result_rows, repeatRows=1, colWidths=[1.1 * inch, 1.2 * inch, 0.82 * inch, 0.55 * inch, 0.65 * inch, 0.6 * inch, 1.55 * inch], style=[
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b9c8d8')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#123a63')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eef5fc')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]),
        Spacer(1, 0.18 * inch),
    ])

    latest_payment = context['latest_payment']
    attendance_rows = [
        ['Present', context['attendance_present'], 'Absent', context['attendance_absent'], 'Sick', context['attendance_sick'], 'Suspension', context['attendance_suspended']],
        ['Latest Payment', latest_payment.amount_paid, 'Payment Date', latest_payment.payment_date, 'Latest Balance', latest_payment.balance, '', ''],
    ]
    story.extend([
        Paragraph('Attendance & Fees', styles['Heading2']),
        Table(attendance_rows, colWidths=[0.9 * inch, 0.75 * inch, 0.9 * inch, 0.75 * inch, 0.95 * inch, 0.75 * inch, 0.9 * inch, 0.75 * inch], style=[
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b9c8d8')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef5fc')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#eef5fc')),
            ('BACKGROUND', (4, 0), (4, -1), colors.HexColor('#eef5fc')),
            ('BACKGROUND', (6, 0), (6, -1), colors.HexColor('#eef5fc')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
            ('FONTNAME', (6, 0), (6, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]),
        Spacer(1, 0.55 * inch),
        Table([['Class Teacher', 'Director of Studies', 'Head Teacher'], ['', '', '']], colWidths=[2.15 * inch, 2.15 * inch, 2.15 * inch], style=[
            ('LINEABOVE', (0, 1), (-1, 1), 0.7, colors.HexColor('#728197')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]),
    ])

    doc.build(story)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def report_card_pdf(request, pk):
    student = get_object_or_404(
        Student.objects.select_related('user').prefetch_related(
            'guardian_links__guardian',
            'enrollments__school_class',
            'enrollments__stream',
            'enrollments__year',
        ),
        pk=pk,
    )
    context = build_report_card_context(student)
    if not context['fees_cleared']:
        messages.error(request, 'PDF report card is blocked until school fees are cleared.')
        return redirect('report_card_detail', pk=student.pk)
    return report_card_pdf_response(student, context)


ATTENDANCE_STATUS_OPTIONS = {
    'present': {'code': 'P', 'label': 'Present', 'class': 'success'},
    'absent': {'code': 'A', 'label': 'Absent', 'class': 'danger'},
    'sick': {'code': 'S', 'label': 'Sick', 'class': 'warning'},
    'suspended': {'code': 'X', 'label': 'Suspension', 'class': 'dark'},
}


STAFF_ATTENDANCE_STATUS_OPTIONS = {
    'present': {'code': 'P', 'label': 'Present', 'class': 'success'},
    'absent': {'code': 'A', 'label': 'Absent', 'class': 'danger'},
    'sick': {'code': 'S', 'label': 'Sick', 'class': 'warning'},
    'suspended': {'code': 'X', 'label': 'Suspension', 'class': 'dark'},
}


def get_current_staff(user):
    return Staff.objects.filter(user=user).first()


def clear_replacement_attendance(staff, attendance_date):
    replacement_records = StaffAttendance.objects.filter(
        attendance_date=attendance_date,
        replacement_for_staff=staff,
    )
    replacement_records.filter(auto_created_replacement=True).delete()
    replacement_records.filter(auto_created_replacement=False).update(
        replacement_for_staff=None,
        notes='',
    )


def award_replacement_attendance(staff, replacement_staff, attendance_date, status, reason, marker):
    clear_replacement_attendance(staff, attendance_date)
    replacement_record = StaffAttendance.objects.filter(
        staff=replacement_staff,
        attendance_date=attendance_date,
    ).first()
    note = (
        f'Replacement attendance for {staff.full_name}. '
        f'Original status: {STAFF_ATTENDANCE_STATUS_OPTIONS[status]["label"]}. '
        f'Reason: {reason}'
    )
    if replacement_record is None:
        StaffAttendance.objects.create(
            staff=replacement_staff,
            attendance_date=attendance_date,
            status=StaffAttendance.Status.PRESENT,
            marked_by=marker,
            replacement_for_staff=staff,
            auto_created_replacement=True,
            notes=note,
        )
        return

    replacement_record.status = StaffAttendance.Status.PRESENT
    replacement_record.marked_by = marker
    replacement_record.replacement_for_staff = staff
    replacement_record.notes = note
    replacement_record.save()


@login_required
def attendance_marking(request):
    selected_date = request.POST.get('attendance_date') or request.GET.get('date') or timezone.localdate().isoformat()
    selected_class_id = request.POST.get('class_id') or request.GET.get('class_id')
    selected_stream_id = request.POST.get('stream_id') or request.GET.get('stream_id')

    selected_class = None
    selected_stream = None
    classes = SchoolClass.objects.order_by('class_level', 'class_name')

    if selected_class_id:
        selected_class = SchoolClass.objects.filter(pk=selected_class_id).first()
    if selected_class is None:
        selected_class = classes.first()
        selected_class_id = selected_class.pk if selected_class else None

    streams = Stream.objects.filter(school_class=selected_class).order_by('stream_name') if selected_class else Stream.objects.none()
    if selected_stream_id:
        selected_stream = streams.filter(pk=selected_stream_id).first()

    if request.method == 'POST':
        student = Student.objects.filter(pk=request.POST.get('student_id')).first()
        status = request.POST.get('status')
        if not selected_class or not student or status not in ATTENDANCE_STATUS_OPTIONS:
            messages.error(request, 'Attendance could not be saved. Please choose a class and valid student status.')
        else:
            enrollment = Enrollment.objects.select_related('stream').filter(
                student=student,
                school_class=selected_class,
            ).first()
            record_stream = selected_stream or (enrollment.stream if enrollment else None)
            attendance = Attendance.objects.filter(
                student=student,
                school_class=selected_class,
                attendance_date=selected_date,
            )
            if selected_stream:
                attendance = attendance.filter(stream=selected_stream)
            record = attendance.first()
            if record is None:
                record = Attendance(
                    student=student,
                    school_class=selected_class,
                    stream=record_stream,
                    attendance_date=selected_date,
                )
            record.status = status
            record.stream = record.stream or record_stream
            record.save()
            messages.success(request, f'{student} marked {ATTENDANCE_STATUS_OPTIONS[status]["label"]}.')

        redirect_url = f'{reverse_lazy("attendance_marking")}?class_id={selected_class_id}&date={selected_date}'
        if selected_stream_id:
            redirect_url += f'&stream_id={selected_stream_id}'
        return redirect(redirect_url)

    enrollment_queryset = Enrollment.objects.select_related('student', 'stream').filter(school_class=selected_class) if selected_class else Enrollment.objects.none()
    if selected_stream:
        enrollment_queryset = enrollment_queryset.filter(stream=selected_stream)

    attendance_records = {
        record.student_id: record
        for record in Attendance.objects.filter(
            school_class=selected_class,
            attendance_date=selected_date,
            student_id__in=enrollment_queryset.values_list('student_id', flat=True),
        )
    } if selected_class else {}

    rows = []
    for enrollment in enrollment_queryset.order_by('student__first_name', 'student__last_name'):
        record = attendance_records.get(enrollment.student_id)
        status = record.status if record else ''
        rows.append({
            'student': enrollment.student,
            'stream': enrollment.stream,
            'status': status,
            'status_meta': ATTENDANCE_STATUS_OPTIONS.get(status),
        })

    summary = {
        key: sum(1 for row in rows if row['status'] == key)
        for key in ATTENDANCE_STATUS_OPTIONS
    }
    summary['unmarked'] = sum(1 for row in rows if not row['status'])

    return render(request, 'core/attendance_marking.html', {
        'classes': classes,
        'streams': streams,
        'selected_class': selected_class,
        'selected_stream': selected_stream,
        'selected_date': selected_date,
        'attendance_rows': rows,
        'status_options': ATTENDANCE_STATUS_OPTIONS,
        'summary': summary,
    })


@login_required
def staff_attendance_marking(request):
    selected_date = request.POST.get('attendance_date') or request.GET.get('date') or timezone.localdate().isoformat()
    department_id = request.POST.get('department_id') or request.GET.get('department_id')
    selected_department = Department.objects.filter(pk=department_id).first() if department_id else None
    staff_queryset = Staff.objects.select_related('department').order_by('full_name')
    if selected_department:
        staff_queryset = staff_queryset.filter(department=selected_department)

    marker = get_current_staff(request.user)

    if request.method == 'POST':
        staff = Staff.objects.filter(pk=request.POST.get('staff_id')).first()
        status = request.POST.get('status')
        replacement_staff = Staff.objects.filter(pk=request.POST.get('replacement_staff_id')).first()
        absence_reason = request.POST.get('absence_reason', '').strip()
        needs_replacement = status in ['absent', 'sick', 'suspended']
        if not staff or status not in STAFF_ATTENDANCE_STATUS_OPTIONS:
            messages.error(request, 'Staff attendance could not be saved. Please choose a valid staff member and status.')
        elif needs_replacement and (not replacement_staff or not absence_reason):
            messages.error(request, 'Absent, sick, or suspended staff must have a replacement staff member and reason recorded.')
        elif needs_replacement and replacement_staff == staff:
            messages.error(request, 'Replacement staff must be different from the absent staff member.')
        else:
            record, _ = StaffAttendance.objects.get_or_create(
                staff=staff,
                attendance_date=selected_date,
                defaults={'marked_by': marker},
            )
            record.status = status
            record.marked_by = marker
            if needs_replacement:
                record.replacement_staff = replacement_staff
                record.absence_reason = absence_reason
            else:
                record.replacement_staff = None
                record.absence_reason = ''
            record.save()
            if needs_replacement:
                award_replacement_attendance(staff, replacement_staff, selected_date, status, absence_reason, marker)
            else:
                clear_replacement_attendance(staff, selected_date)
            messages.success(request, f'{staff.full_name} marked {STAFF_ATTENDANCE_STATUS_OPTIONS[status]["label"]}.')

        redirect_url = f'{reverse_lazy("staff_attendance_marking")}?date={selected_date}'
        if department_id:
            redirect_url += f'&department_id={department_id}'
        return redirect(redirect_url)

    records = {
        record.staff_id: record
        for record in StaffAttendance.objects.select_related('replacement_staff').filter(
            attendance_date=selected_date,
            staff_id__in=staff_queryset.values_list('id', flat=True),
        )
    }
    replacement_staff_members = Staff.objects.select_related('department').filter(status='active').order_by('full_name')
    rows = []
    for staff in staff_queryset:
        record = records.get(staff.id)
        status = record.status if record else ''
        rows.append({
            'staff': staff,
            'record': record,
            'status': status,
            'status_meta': STAFF_ATTENDANCE_STATUS_OPTIONS.get(status),
        })

    summary = {
        key: sum(1 for row in rows if row['status'] == key)
        for key in STAFF_ATTENDANCE_STATUS_OPTIONS
    }
    summary['unmarked'] = sum(1 for row in rows if not row['status'])

    return render(request, 'core/staff_attendance_marking.html', {
        'departments': Department.objects.order_by('department_name'),
        'selected_department': selected_department,
        'selected_date': selected_date,
        'attendance_rows': rows,
        'replacement_staff_members': replacement_staff_members,
        'status_options': STAFF_ATTENDANCE_STATUS_OPTIONS,
        'summary': summary,
    })


@login_required
def payroll_list(request):
    today = timezone.localdate()
    month = int(request.POST.get('month') or request.GET.get('month') or today.month)
    year = int(request.POST.get('year') or request.GET.get('year') or today.year)
    generator = get_current_staff(request.user)

    if request.method == 'POST':
        for staff in Staff.objects.order_by('full_name'):
            records = StaffAttendance.objects.filter(
                staff=staff,
                attendance_date__year=year,
                attendance_date__month=month,
            )
            present_days = records.filter(status='present').count()
            sick_days = records.filter(status='sick').count()
            absent_days = records.filter(status='absent').count()
            suspension_days = records.filter(status='suspended').count()
            working_days = present_days + sick_days + absent_days + suspension_days
            payable_days = present_days
            base_salary = staff.base_salary or 0
            if working_days:
                net_salary = base_salary * payable_days / working_days
            else:
                net_salary = 0
            deductions = base_salary - net_salary
            Payroll.objects.update_or_create(
                staff=staff,
                month=month,
                year=year,
                defaults={
                    'base_salary': base_salary,
                    'present_days': present_days,
                    'sick_days': sick_days,
                    'absent_days': absent_days,
                    'suspension_days': suspension_days,
                    'working_days': working_days,
                    'payable_days': payable_days,
                    'deductions': deductions,
                    'net_salary': net_salary,
                    'generated_by': generator,
                    'generated_at': timezone.now(),
                    'status': 'generated',
                },
            )
        messages.success(request, f'Payroll generated for {month}/{year}.')
        return redirect(f'{reverse_lazy("payroll_list")}?month={month}&year={year}')

    payrolls = Payroll.objects.select_related('staff', 'staff__department').filter(month=month, year=year)
    totals = payrolls.aggregate(
        base=Sum('base_salary'),
        deductions=Sum('deductions'),
        net=Sum('net_salary'),
    )
    return render(request, 'core/payroll_list.html', {
        'month': month,
        'year': year,
        'payrolls': payrolls.order_by('staff__full_name'),
        'totals': totals,
    })


@login_required
def students_json(request):
    students = list(
        Student.objects.values(
            'id',
            'admission_no',
            'first_name',
            'last_name',
            'gender',
            'status',
        )
    )
    return JsonResponse({'students': students})


@login_required
def staff_json(request):
    staff_members = list(
        Staff.objects.values(
            'id',
            'employee_code',
            'full_name',
            'designation',
            'status',
        )
    )
    return JsonResponse({'staff': staff_members})


MANAGED_MODELS = {
    'departments': Department,
    'staff': Staff,
    'staff-attendance': StaffAttendance,
    'payroll': Payroll,
    'guardians': Guardian,
    'students': Student,
    'student-guardians': StudentGuardian,
    'academic-years': AcademicYear,
    'terms': Term,
    'classes': SchoolClass,
    'streams': Stream,
    'enrollments': Enrollment,
    'attendance': Attendance,
    'subjects': Subject,
    'class-subjects': ClassSubject,
    'exams': Exam,
    'exam-results': ExamResult,
    'fees-structures': FeesStructure,
    'fee-discounts': FeeDiscount,
    'payments': Payment,
    'receipts': Receipt,
    'accounts': Account,
    'journal-entries': JournalEntry,
    'journal-lines': JournalLine,
    'suppliers': Supplier,
    'invoices': Invoice,
    'expenses': Expense,
    'audit-logs': AuditLog,
    'library-books': LibraryBook,
    'book-borrowings': BookBorrowing,
    'hostels': Hostel,
    'hostel-rooms': HostelRoom,
    'hostel-allocations': HostelAllocation,
    'transport-routes': TransportRoute,
    'vehicles': Vehicle,
    'transport-allocations': TransportAllocation,
    'online-applications': OnlineApplication,
    'application-requirements': ApplicationRequirement,
    'application-requirement-checks': ApplicationRequirementCheck,
    'application-documents': ApplicationDocument,
    'admissions': Admission,
    'documents': Document,
    'events': Event,
    'event-participants': EventParticipant,
    'health-records': HealthRecord,
    'discipline-records': DisciplineRecord,
    'leaves': Leave,
    'notifications': Notification,
    'holidays': Holiday,
    'system-settings': SystemSetting,
}


MANAGED_GROUPS = [
    {
        'name': 'People',
        'description': 'Users, staff, students, guardians, and family links.',
        'models': ['students', 'staff', 'staff-attendance', 'payroll', 'guardians', 'student-guardians', 'notifications'],
    },
    {
        'name': 'Academics',
        'description': 'Academic years, classes, streams, subjects, exams, and results.',
        'models': ['academic-years', 'terms', 'classes', 'streams', 'enrollments', 'attendance', 'subjects', 'class-subjects', 'exams', 'exam-results'],
    },
    {
        'name': 'Finance',
        'description': 'Fees, accounting, suppliers, expenses, invoices, journals, and audit trail.',
        'models': ['fees-structures', 'fee-discounts', 'payments', 'receipts', 'accounts', 'journal-entries', 'journal-lines', 'suppliers', 'invoices', 'expenses', 'audit-logs'],
    },
    {
        'name': 'Admissions',
        'description': 'Online applications, uploaded application documents, and admissions.',
        'models': ['online-applications', 'application-requirements', 'application-requirement-checks', 'application-documents', 'admissions'],
    },
    {
        'name': 'Student Services',
        'description': 'Library, hostel, transport, health, discipline, events, and documents.',
        'models': ['library-books', 'book-borrowings', 'hostels', 'hostel-rooms', 'hostel-allocations', 'transport-routes', 'vehicles', 'transport-allocations', 'documents', 'events', 'event-participants', 'health-records', 'discipline-records', 'leaves', 'holidays'],
    },
    {
        'name': 'Administration',
        'description': 'Departments and system settings.',
        'models': ['departments', 'system-settings'],
    },
]


def get_managed_model(model_name):
    try:
        return MANAGED_MODELS[model_name]
    except KeyError:
        raise Http404('Managed model not found')


class ManageIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'core/manage_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['managed_groups'] = []
        for group in MANAGED_GROUPS:
            context['managed_groups'].append({
                'name': group['name'],
                'description': group['description'],
                'models': [
                    {
                        'slug': slug,
                        'name': MANAGED_MODELS[slug]._meta.verbose_name_plural.title(),
                        'count': MANAGED_MODELS[slug].objects.count(),
                    }
                    for slug in group['models']
                ],
            })
        return context


class ManagedListView(LoginRequiredMixin, ListView):
    template_name = 'core/manage_list.html'
    context_object_name = 'objects'

    def dispatch(self, request, *args, **kwargs):
        self.model_name = kwargs['model_name']
        self.model = get_managed_model(self.model_name)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.verbose_name.title()
        context['model_name_plural'] = self.model._meta.verbose_name_plural.title()
        context['add_url_name'] = 'manage_model_add'
        context['edit_url_name'] = 'manage_model_edit'
        context['model_name_slug'] = self.model_name
        context['is_audit_log'] = self.model is AuditLog
        return context


class ManagedCreateView(LoginRequiredMixin, CreateView):
    template_name = 'core/manage_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.model_name = kwargs['model_name']
        self.model = get_managed_model(self.model_name)
        if self.model is AuditLog:
            raise PermissionDenied('Audit logs are immutable and cannot be created manually.')
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return modelform_factory(
            self.model,
            form=BootstrapModelForm,
            exclude=['created_at', 'updated_at'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.verbose_name.title()
        context['model_name_plural'] = self.model._meta.verbose_name_plural.title()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.model is not AuditLog:
            log_audit(AuditLog.Action.CREATE, self.object, self.request, 'Record created from managed tables.')
        return response

    def get_success_url(self):
        return reverse_lazy('manage_model_list', kwargs={'model_name': self.model_name})


class ManagedUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'core/manage_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.model_name = kwargs['model_name']
        self.model = get_managed_model(self.model_name)
        if self.model is AuditLog:
            raise PermissionDenied('Audit logs are immutable and cannot be edited.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.all()

    def get_form_class(self):
        return modelform_factory(
            self.model,
            form=BootstrapModelForm,
            exclude=['created_at', 'updated_at'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.verbose_name.title()
        context['model_name_plural'] = self.model._meta.verbose_name_plural.title()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.model is not AuditLog:
            log_audit(AuditLog.Action.UPDATE, self.object, self.request, 'Record updated from managed tables.')
        return response

    def get_success_url(self):
        return reverse_lazy('manage_model_list', kwargs={'model_name': self.model_name})
