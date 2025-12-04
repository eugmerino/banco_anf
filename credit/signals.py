from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from .models import Credit, CreditAccount, LoanInstallment, LoanPayment
from django.db import transaction
from django.core.exceptions import ValidationError


TWOPLACES = Decimal("0.01")


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


@receiver(post_save, sender=LoanPayment)
def allocate_payment(sender, instance: LoanPayment, created, **kwargs):
    if not created:
        return

    installment: LoanInstallment = instance.installment
    account: CreditAccount = installment.account
    remaining_amount = Decimal(instance.amount)

    # 1. Mora
    to_late_fees = min(installment.late_fees, remaining_amount)
    installment.late_fees -= to_late_fees
    remaining_amount -= to_late_fees

    if to_late_fees > 0:
        account.overdue_events += 1

    # 2. Intereses acumulados
    to_accrued_interest = min(installment.accrued_interest, remaining_amount)
    installment.accrued_interest -= to_accrued_interest
    remaining_amount -= to_accrued_interest

    # 3. Intereses ordinarios
    to_interest = min(installment.interest, remaining_amount)
    installment.interest -= to_interest
    remaining_amount -= to_interest

    # 4. Capital
    to_capital = min(installment.capital, remaining_amount)
    installment.capital -= to_capital
    remaining_amount -= to_capital

    # Si sobra dinero después de cubrir toda la cuota, aplicarlo a capital adicional
    if remaining_amount > 0:
        to_capital += remaining_amount
        installment.capital -= remaining_amount  # puede quedar negativo, ajustamos después
        remaining_amount = Decimal("0.00")

    # Evitar capital negativo
    if installment.capital < 0:
        installment.capital = Decimal("0.00")

    # Guardar pago
    instance.to_late_fees = to_late_fees.quantize(TWOPLACES, ROUND_HALF_UP)
    instance.to_accrued_interest = to_accrued_interest.quantize(TWOPLACES, ROUND_HALF_UP)
    instance.to_interest = to_interest.quantize(TWOPLACES, ROUND_HALF_UP)
    instance.to_capital = to_capital.quantize(TWOPLACES, ROUND_HALF_UP)
    instance.save(update_fields=["to_late_fees", "to_accrued_interest", "to_interest", "to_capital"])

    # Guardar cambios en la cuota
    installment.save(update_fields=["late_fees", "accrued_interest", "interest", "capital"])

    # Actualizar la cuenta de crédito
    account.late_fees_paid += to_late_fees
    account.interest_paid += to_accrued_interest + to_interest
    account.capital_paid += to_capital
    account.save(update_fields=["late_fees_paid", "interest_paid", "capital_paid", "overdue_events"])

    # Marcar cuota como pagada si capital llegó a 0
    if installment.capital <= 0:
        installment.paid = True
        installment.save(update_fields=["paid"])

        # Generar siguiente cuota aquí, después de actualizar capital_paid
        generate_next_installment_after_payment(account, installment)


def generate_next_installment_after_payment(account: CreditAccount, last_installment: LoanInstallment):
    """
    Genera la siguiente cuota después de actualizar capital_paid
    """
    credit = account.credit

    # Verificar si ya existen cuotas posteriores
    later_installments = account.installments.filter(due_date__gt=last_installment.due_date)
    if later_installments.exists():
        return

    remaining_capital = credit.amount - account.capital_paid
    if remaining_capital <= 0:
        return

    total_quotas = credit.quotas
    paid_quotas = account.installments.filter(paid=True).count()
    remaining_quotas = total_quotas - paid_quotas

    if remaining_quotas <= 0:
        return

    r = Decimal(credit.credit_type.annual_interest_rate) / Decimal(12 * 100)
    if r == 0:
        cuota_total = (remaining_capital / remaining_quotas).quantize(TWOPLACES, ROUND_HALF_UP)
    else:
        cuota_total = (remaining_capital * (r * (1 + r) ** remaining_quotas) / ((1 + r) ** remaining_quotas - 1)).quantize(TWOPLACES, ROUND_HALF_UP)

    interest = (remaining_capital * r).quantize(TWOPLACES, ROUND_HALF_UP)
    capital = (cuota_total - interest).quantize(TWOPLACES, ROUND_HALF_UP)
    due_date = last_installment.due_date + relativedelta(months=1)

    LoanInstallment.objects.create(
        account=account,
        due_date=due_date,
        capital=capital,
        interest=interest,
        late_fees=0,
        accrued_interest=0,
        paid=False
    )

@receiver(post_save, sender=CreditAccount)
def update_credit_status(sender, instance: CreditAccount, **kwargs):
    """
    Cuando se actualiza la cuenta de crédito, verifica si el capital abonado
    cubre el monto total del crédito. Si es así, marca el crédito como 'PAID'.
    """
    account = instance
    credit = account.credit

    # Convertir a Decimal por seguridad
    capital_paid = Decimal(account.capital_paid)
    credit_amount = Decimal(credit.amount)

    # Redondeamos a 2 decimales
    capital_paid = capital_paid.quantize(Decimal("0.01"))
    credit_amount = credit_amount.quantize(Decimal("0.01"))

    if capital_paid >= credit_amount and credit.status != "PAID":
        credit.status = "PAID"
        credit.save(update_fields=["status"])

@receiver(post_save, sender=Credit)
def update_customer_classification(sender, instance: Credit, created, **kwargs):
    """
    Actualiza la clasificación del cliente cuando un crédito cambia a Liquidado.
    """
    # Solo actuar si el crédito ya está Liquidado
    if instance.status != "PAID":
        return

    customer = instance.customer

    # Traer los últimos 5 créditos del cliente, más recientes primero
    recent_credits = Credit.objects.filter(customer=customer).order_by('-credit_date')[:5]

    # Contar cuántos créditos tuvieron mora (overdue_events > 0)
    mora_count = sum(1 for c in recent_credits if hasattr(c, 'account') and c.account.overdue_events > 0)

    # Determinar la nueva clasificación
    if mora_count == 0:
        new_class = "A"
    elif mora_count == 1:
        new_class = "B"
    elif mora_count == 2:
        new_class = "C"
    else:
        new_class = "E"

    # Solo actualizar si es diferente
    if customer.classification != new_class:
        customer.classification = new_class
        customer.save(update_fields=["classification"])
        