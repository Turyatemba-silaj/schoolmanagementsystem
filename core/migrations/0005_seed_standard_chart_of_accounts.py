from django.db import migrations


STANDARD_ACCOUNTS = [
    ('1000', 'Cash on Hand', 'asset'),
    ('1010', 'Bank Account', 'asset'),
    ('1100', 'Accounts Receivable', 'asset'),
    ('1200', 'Prepaid Expenses', 'asset'),
    ('2000', 'Accounts Payable', 'liability'),
    ('2100', 'Fees Received in Advance', 'liability'),
    ('3000', 'School Fund Balance', 'equity'),
    ('4000', 'Tuition and School Fees Income', 'income'),
    ('4010', 'Application Fees Income', 'income'),
    ('4020', 'Transport Fees Income', 'income'),
    ('5000', 'Payroll Expense', 'expense'),
    ('5010', 'Teaching Materials Expense', 'expense'),
    ('5020', 'Utilities Expense', 'expense'),
    ('5030', 'Repairs and Maintenance Expense', 'expense'),
    ('5040', 'Administrative Expense', 'expense'),
]


def seed_accounts(apps, schema_editor):
    Account = apps.get_model('core', 'Account')
    for code, name, account_type in STANDARD_ACCOUNTS:
        Account.objects.get_or_create(
            account_code=code,
            defaults={
                'account_name': name,
                'account_type': account_type,
                'is_active': True,
            },
        )


def unseed_accounts(apps, schema_editor):
    Account = apps.get_model('core', 'Account')
    Account.objects.filter(account_code__in=[code for code, _, _ in STANDARD_ACCOUNTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_supplier_account_auditlog_journalentry_journalline_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_accounts, unseed_accounts),
    ]
