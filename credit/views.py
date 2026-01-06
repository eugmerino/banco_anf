from django.contrib.admin import site
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Credit
from decimal import Decimal, ROUND_HALF_UP
from .forms import CreditProjectionForm


@staff_member_required
def credit_forecast_view(request, credit_id):
    credit = get_object_or_404(Credit, pk=credit_id)
    
    extra_context = site.each_context(request)

    # Datos para cálculo de amortización francesa
    # Convertir todos los valores a Decimal
    P = Decimal(credit.amount)
    n = credit.quotas
    i = Decimal(credit.credit_type.annual_interest_rate) / Decimal('100') / Decimal('12')


    # Lista para guardar cada cuota
    amortization_table = []

    saldo = P
    for month in range(1, n + 1):
        interes = (saldo * i).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Cuota fija
        cuota = (P * (i * (1 + i) ** n) / ((1 + i) ** n - 1)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        capital = (cuota - interes).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        saldo = (saldo - capital).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        amortization_table.append({
            "mes": month,
            "cuota": cuota,
            "interes": interes,
            "capital": capital,
            "saldo": saldo,
        })


    extra_context.update({
        "opts": Credit._meta,
        "original": credit,
        "title": "Pronóstico del crédito",
        "credit": credit,
        "amortization_table": amortization_table,
        "cuota": cuota,
    })

    return render(request, "credit/credit.html", extra_context)


@staff_member_required
def credit_projection_view(request):
    form = CreditProjectionForm(request.POST or None)
    amortization_table = None
    cuota = None

    if request.method == "POST" and form.is_valid():
        amount = form.cleaned_data["amount"]
        quotas = form.cleaned_data["quotas"]
        annual_interest_rate = form.cleaned_data["annual_interest_rate"]

        # --- Cálculo de amortización francesa ---
        P = Decimal(amount)
        n = int(quotas)
        i = (Decimal(annual_interest_rate) / Decimal("100")) / Decimal("12")

        cuota = (P * (i * (1 + i) ** n) / ((1 + i) ** n - 1)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        amortization_table = []
        saldo = P

        for month in range(1, n + 1):
            interes = (saldo * i).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            capital = (cuota - interes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            saldo = (saldo - capital).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            amortization_table.append({
                "mes": month,
                "cuota": cuota,
                "interes": interes,
                "capital": capital,
                "saldo": saldo,
            })

    extra_context = site.each_context(request)
    extra_context.update({
        "opts": Credit._meta,
        "title": "Proyección del crédito",
        "form": form,
        "amortization_table": amortization_table,
        "cuota": cuota,
    })

    return render(request, "credit/credit_projection.html", extra_context)

