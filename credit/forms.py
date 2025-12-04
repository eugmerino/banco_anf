from django import forms
from .models import LoanPayment
from datetime import datetime



# Formulario para proyección de crédito
class CreditProjectionForm(forms.Form):
    amount = forms.DecimalField(label="Monto", decimal_places=2)
    quotas = forms.IntegerField(label="Plazo (meses)")
    annual_interest_rate = forms.DecimalField(label="Interés anual (%)", decimal_places=2)


# Formulario para pago de cuota
class LoanPaymentForm(forms.ModelForm):
    class Meta:
        model = LoanPayment
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        installment = cleaned.get("installment")
        payment_date = cleaned.get("payment_date")
        amount = cleaned.get("amount")

        if not (installment and payment_date and amount):
            return cleaned

        total_cuota = installment.total_amount
        due_date = installment.due_date

        # 1️⃣ VALIDACIÓN EXISTENTE
        if payment_date > due_date and amount > total_cuota:
            self.add_error(
                "amount",
                "No puede pagar un monto mayor al total de la cuota cuando el pago se registra después del vencimiento."
            )

        # 2️⃣ NUEVA VALIDACIÓN: NO EXCEDER MONTO FINAL DEL CRÉDITO
        account = installment.account
        credit = account.credit

        capital_pagado = account.capital_paid
        
        # datos de la cuota
        mora = installment.late_fees
        interes = installment.interest + installment.accrued_interest
        capital_cuota = installment.capital

        # cuanto del pago cubrirá la cuota
        pago_para_cuota = mora + interes + capital_cuota

        # excedente hacia capital
        excedente = amount - pago_para_cuota
        if excedente < 0:
            excedente = 0

        # capital acumulado si este pago se aplica
        nuevo_capital_total = capital_pagado + capital_cuota + excedente

        if nuevo_capital_total > credit.amount:
            self.add_error(
                "amount",
                f"Este pago excede el monto total del crédito. "
                f"Capital acumulado sería {nuevo_capital_total}, "
                f"pero el crédito es de {credit.amount}."
            )

        return cleaned

