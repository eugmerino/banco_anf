from .models import LoanInstallment

def accrue_mora_daily():
    installments = LoanInstallment.objects.filter(paid=False)
    for inst in installments:
        inst.accrue_daily_penalties()
