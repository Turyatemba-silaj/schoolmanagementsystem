from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.dispatch import receiver

from .models import AuditLog


def client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_auth_log(action, request, user, note):
    path = getattr(request, 'path', '') or ''
    method = getattr(request, 'method', '') or ''
    try:
        AuditLog.objects.create(
            action=action,
            model_name='Authentication',
            object_id=str(user.pk),
            object_repr=str(user),
            changed_by=user,
            path=path[:256],
            method=method[:12],
            ip_address=client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:256],
            note=note,
        )
    except (DatabaseError, OperationalError, ProgrammingError):
        return


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    create_auth_log(AuditLog.Action.LOGIN, request, user, f'{user} logged into the system.')


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        create_auth_log(AuditLog.Action.LOGOUT, request, user, f'{user} logged out of the system.')
