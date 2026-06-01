from time import monotonic

from django.db import DatabaseError, OperationalError, ProgrammingError
from django.urls import resolve

from .models import AuditLog


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._audit_started_at = monotonic()
        response = self.get_response(request)
        self.log_request(request, response)
        return response

    def log_request(self, request, response):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return

        action = self.get_action(request)
        view_name = self.get_view_name(request)
        duration_ms = int((monotonic() - getattr(request, '_audit_started_at', monotonic())) * 1000)
        activity_detail = self.get_activity_detail(request, view_name, response, duration_ms)
        try:
            AuditLog.objects.create(
                action=action,
                model_name='System Activity',
                object_id=str(user.pk),
                object_repr=f'{user.username} {request.method} {request.path}',
                changed_by=user,
                path=request.path[:256],
                method=request.method[:12],
                status_code=getattr(response, 'status_code', None),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:256],
                note=activity_detail,
            )
        except (DatabaseError, OperationalError, ProgrammingError):
            return

    def get_action(self, request):
        if request.path.endswith('/login/') and request.method == 'POST':
            return AuditLog.Action.LOGIN
        if request.path.endswith('/logout/'):
            return AuditLog.Action.LOGOUT
        if request.method == 'GET':
            return AuditLog.Action.VIEW
        if request.method == 'POST':
            if '/add/' in request.path:
                return AuditLog.Action.CREATE
            if '/edit/' in request.path:
                return AuditLog.Action.UPDATE
            return AuditLog.Action.POST
        if request.method in ['PUT', 'PATCH']:
            return AuditLog.Action.UPDATE
        if request.method == 'DELETE':
            return AuditLog.Action.DELETE
        return AuditLog.Action.SECURITY

    def get_view_name(self, request):
        try:
            match = resolve(request.path_info)
        except Exception:
            return 'unresolved'
        return match.view_name or f'{match.func.__module__}.{match.func.__name__}'

    def get_client_ip(self, request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def get_activity_detail(self, request, view_name, response, duration_ms):
        detail = f'{request.method} {request.path} handled by {view_name} with status {getattr(response, "status_code", "")} in {duration_ms}ms.'
        if request.method == 'POST':
            submitted = self.safe_post_data(request)
            if submitted:
                detail = f'{detail} Submitted: {submitted}.'
        return detail[:1000]

    def safe_post_data(self, request):
        hidden_fields = {'csrfmiddlewaretoken', 'password', 'password1', 'password2', 'old_password', 'new_password1', 'new_password2'}
        values = []
        for key, value in request.POST.items():
            if key in hidden_fields:
                continue
            clean_value = str(value).strip()
            if len(clean_value) > 60:
                clean_value = f'{clean_value[:57]}...'
            values.append(f'{key}={clean_value}')
        return ', '.join(values)[:700]
