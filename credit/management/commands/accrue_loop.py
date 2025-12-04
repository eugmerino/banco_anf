from django.core.management.base import BaseCommand
from credit.models import LoanInstallment
from datetime import date, timedelta
import time

class Command(BaseCommand):
    help = "Ejecuta los cálculos de mora cada 10 seg. Opcionalmente usar --test-days para simular días desde la fecha de vencimiento."

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-days',
            type=int,
            default=0,
            help="Número de días adicionales para simular vencimiento (útil para pruebas)."
        )

    def handle(self, *args, **kwargs):
        test_days = kwargs['test_days']
        self.stdout.write(f"Iniciando bucle de mora (cada 10 seg...) con test-days={test_days}")

        while True:
            today = date.today() + timedelta(days=test_days)
            installments = LoanInstallment.objects.select_related('account', 'account__credit').all()

            for inst in installments:
                # 1️⃣ Acumular intereses y mora
                inst.accrue_up_to(today)

                # 2️⃣ Verificar si cuota vencida > 60 días
                if not inst.paid and inst.due_date + timedelta(days=60) < today:
                    credit = inst.account.credit
                    if credit.status != "WRITEOFF":
                        credit.status = "WRITEOFF"
                        credit.save(update_fields=["status"])
                        self.stdout.write(
                            f"Crédito {credit} marcado como incobrable (cuota vencida > 60 días, test-days={test_days})."
                        )

            self.stdout.write("Cálculo de mora ejecutado.")
            time.sleep(10)
