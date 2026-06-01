from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User,
    Department,
    Staff,
    StaffAttendance,
    Payroll,
    Guardian,
    Student,
    StudentGuardian,
    AcademicYear,
    Term,
    SchoolClass,
    Stream,
    Enrollment,
    Attendance,
    Subject,
    ClassSubject,
    Exam,
    ExamResult,
    FeesStructure,
    FeeDiscount,
    Payment,
    Receipt,
    Account,
    JournalEntry,
    JournalLine,
    Supplier,
    Invoice,
    Expense,
    AuditLog,
    LibraryBook,
    BookBorrowing,
    Hostel,
    HostelRoom,
    HostelAllocation,
    TransportRoute,
    Vehicle,
    TransportAllocation,
    OnlineApplication,
    ApplicationDocument,
    Admission,
    Document,
    Event,
    EventParticipant,
    HealthRecord,
    DisciplineRecord,
    Leave,
    Notification,
    Holiday,
    SystemSetting,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'role', 'status')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'email', 'role', 'status', 'is_staff', 'is_superuser')
    list_filter = ('role', 'status', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)


admin.site.register(
    [
        Department,
        Staff,
        StaffAttendance,
        Payroll,
        Guardian,
        Student,
        StudentGuardian,
        AcademicYear,
        Term,
        SchoolClass,
        Stream,
        Enrollment,
        Attendance,
        Subject,
        ClassSubject,
        Exam,
        ExamResult,
        FeesStructure,
        FeeDiscount,
        Payment,
        Receipt,
        Account,
        JournalEntry,
        JournalLine,
        Supplier,
        Invoice,
        Expense,
        LibraryBook,
        BookBorrowing,
        Hostel,
        HostelRoom,
        HostelAllocation,
        TransportRoute,
        Vehicle,
        TransportAllocation,
        OnlineApplication,
        ApplicationDocument,
        Admission,
        Document,
        Event,
        EventParticipant,
        HealthRecord,
        DisciplineRecord,
        Leave,
        Notification,
        Holiday,
        SystemSetting,
    ]
)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('activity_date', 'activity_time', 'changed_by', 'action', 'model_name', 'path', 'method', 'status_code', 'ip_address')
    list_filter = ('action', 'method', 'status_code', 'activity_date', 'created_at')
    search_fields = ('changed_by__username', 'model_name', 'object_repr', 'path', 'note', 'ip_address')
    readonly_fields = (
        'action',
        'model_name',
        'object_id',
        'object_repr',
        'changed_by',
        'path',
        'method',
        'status_code',
        'ip_address',
        'user_agent',
        'note',
        'activity_date',
        'activity_time',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
