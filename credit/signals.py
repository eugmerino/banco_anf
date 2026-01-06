from django.db.models.signals import post_save
from django.dispatch import receiver
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from .models import Credit, CreditAccount, LoanInstallment


#Crear la cuenta del crédito cuando se crea un crédito nuevo
@receiver(post_save, sender=Credit)
def create_credit_account(sender, instance, created, **kwargs):
    if created:
        # Crear la cuenta del crédito con todo en 0
        CreditAccount.objects.create(credit=instance)


# Crear la primera cuota cuando se crea una cuenta de crédito nueva
@receiver(post_save, sender=CreditAccount)
def create_first_installment(sender, instance, created, **kwargs):
    if not created:
        return

    account = instance
    credit = account.credit

    from credit.models import LoanInstallment

    # Si ya existen cuotas, no crear
    if LoanInstallment.objects.filter(account=account).exists():
        return

    # Generar primera cuota
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    due_date = credit.credit_date + relativedelta(months=1)

    # Calculo básico de amortización francesa
    interest_rate = Decimal(credit.credit_type.annual_interest_rate / 100 / 12)

    cuota_total = (
        credit.amount * interest_rate *
        ((1 + interest_rate) ** credit.quotas) /
        (((1 + interest_rate) ** credit.quotas) - 1)
    )

    intereses = round(credit.amount * interest_rate, 2)
    capital = round(cuota_total - intereses, 2)

    LoanInstallment.objects.create(
        account=account,
        due_date=due_date,
        capital=capital,
        interest=intereses,
        late_fees=0,
        paid=False
    )
