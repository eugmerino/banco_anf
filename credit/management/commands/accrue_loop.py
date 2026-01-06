from django.core.management.base import BaseCommand
from credit.models import LoanInstallment
from datetime import date
import time

class Command(BaseCommand):
    help = "Ejecuta los cálculos de mora cada 10 seg."

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando bucle de mora (cada 10 seg)...")

        while True:
            installments = LoanInstallment.objects.all()
            for inst in installments:
                inst.accrue_up_to(date.today())
            self.stdout.write("Cálculo de mora ejecutado.")
            time.sleep(10)
