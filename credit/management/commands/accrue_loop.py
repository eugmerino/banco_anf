from django.core.management.base import BaseCommand
from credit.models import LoanInstallment
from datetime import date, timedelta
import time

from django.core.management.base import BaseCommand
from credit.models import LoanInstallment
from datetime import date, timedelta
import time

class Command(BaseCommand):
    help = "Ejecuta los cálculos de mora cada 10 seg."

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando bucle de mora (cada 10 seg...)")

        while True:
            today = date.today()
            installments = LoanInstallment.objects.select_related('account', 'account__credit').all()

            for inst in installments:
                # Acumular intereses y mora
                inst.accrue_up_to(today)

                # Verificar si cuota vencida > 60 días
                if not inst.paid and inst.due_date + timedelta(days=60) < today:
                    credit = inst.account.credit
                    if credit.status != "WRITEOFF":
                        credit.status = "WRITEOFF"
                        credit.save(update_fields=["status"])
                        self.stdout.write(
                            f"Crédito {credit} marcado como incobrable (cuota vencida > 60 días)."
                        )

            self.stdout.write("Cálculo de mora ejecutado.")
            time.sleep(10)


# Comando: python manage.py accrue_loop