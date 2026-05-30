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
