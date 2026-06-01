from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from .models import Enrollment, FeesStructure, OnlineApplication, Payment, SchoolClass, Staff, Student


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            elif isinstance(widget, forms.Select):
                css_class = 'form-select'
            elif isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                css_class = 'form-check-input'
            else:
                css_class = 'form-control'

            existing_classes = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{existing_classes} {css_class}'.strip()


class BootstrapAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    pass


class BootstrapModelForm(BootstrapFormMixin, forms.ModelForm):
    pass


class StudentForm(BootstrapModelForm):
    class Meta:
        model = Student
        fields = [
            'user',
            'admission_no',
            'first_name',
            'last_name',
            'gender',
            'dob',
            'blood_group',
            'phone',
            'address',
            'photo',
            'status',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class StaffForm(BootstrapModelForm):
    class Meta:
        model = Staff
        fields = [
            'user',
            'department',
            'employee_code',
            'full_name',
            'designation',
            'phone',
            'email',
            'address',
            'hire_date',
            'base_salary',
            'status',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ClassForm(BootstrapModelForm):
    class Meta:
        model = SchoolClass
        fields = ['class_name', 'class_level', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class ApplicationForm(BootstrapModelForm):
    document_type = forms.CharField(
        label='Supporting Document Type',
        required=False,
        help_text='Example: Birth certificate, previous school report, medical form.',
    )
    document_file = forms.FileField(
        label='Supporting Document',
        required=False,
        help_text='Upload a requirement document if available.',
    )

    class Meta:
        model = OnlineApplication
        fields = [
            'application_mode',
            'applicant_name',
            'dob',
            'gender',
            'previous_school',
            'applied_class',
            'document_type',
            'document_file',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        document_type = cleaned_data.get('document_type')
        document_file = cleaned_data.get('document_file')
        if bool(document_type) != bool(document_file):
            raise forms.ValidationError('Enter both the supporting document type and the document file.')
        return cleaned_data


class PaymentForm(BootstrapModelForm):
    student_payment_code = forms.CharField(
        label='Student Payment Code',
        help_text='Enter the student admission number/payment code.',
    )
    payment_reference_number = forms.CharField(
        label='Deposit Slip / Mobile Money Reference Number',
        help_text='Enter the bank deposit slip number or mobile money reference number.',
    )

    class Meta:
        model = Payment
        fields = [
            'student_payment_code',
            'payment_date',
            'amount_paid',
            'payment_method',
            'payment_reference_number',
            'paid_by',
            'receipted_by',
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_date'].initial = self.fields['payment_date'].initial or timezone.localdate()
        if self.instance and self.instance.pk:
            self.fields['student_payment_code'].initial = self.instance.student.admission_no
            self.fields['payment_reference_number'].initial = self.instance.transaction_id

    def clean_student_payment_code(self):
        code = self.cleaned_data['student_payment_code'].strip()
        try:
            return Student.objects.get(admission_no=code)
        except Student.DoesNotExist as exc:
            raise forms.ValidationError('No student was found with this payment code.') from exc

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student_payment_code')
        if not student:
            return cleaned_data

        enrollment = Enrollment.objects.filter(student=student).order_by('-enrollment_date', '-id').first()
        if not enrollment:
            raise forms.ValidationError('This student has no enrollment, so a fee structure cannot be selected automatically.')

        fees_structure = FeesStructure.objects.filter(school_class=enrollment.school_class).order_by('-created_at', '-id').first()
        if not fees_structure:
            raise forms.ValidationError('No fee structure was found for this student class.')

        cleaned_data['student'] = student
        cleaned_data['fees_structure'] = fees_structure
        return cleaned_data

    def save(self, commit=True):
        payment = super().save(commit=False)
        payment.student = self.cleaned_data['student']
        payment.fees_structure = self.cleaned_data['fees_structure']
        payment.transaction_id = self.cleaned_data['payment_reference_number'].strip()
        if commit:
            payment.save()
            self.save_m2m()
        return payment


class PayeeLoginForm(BootstrapFormMixin, forms.Form):
    student_number = forms.CharField(
        label='Student Number',
        help_text='Use the student admission number or payment code.',
    )

    def clean_student_number(self):
        student_number = self.cleaned_data['student_number'].strip()
        try:
            return Student.objects.get(admission_no=student_number)
        except Student.DoesNotExist as exc:
            raise forms.ValidationError('No student was found with this number.') from exc


class PayeePaymentForm(BootstrapFormMixin, forms.Form):
    amount_paid = forms.DecimalField(label='Amount Paid', min_value=1, max_digits=12, decimal_places=2)
    payment_method = forms.ChoiceField(
        label='Payment Method',
        choices=[
            ('Mobile Money', 'Mobile Money'),
            ('Bank Deposit', 'Bank Deposit'),
            ('Cash', 'Cash'),
        ],
    )
    payment_reference_number = forms.CharField(
        label='Deposit Slip / Mobile Money Reference Number',
        help_text='Enter the exact bank slip number or mobile money reference.',
    )
    paid_by = forms.CharField(label='Paid By', max_length=256)
