from django.db import models
from customer.models import NaturalCustomer
from django.core.exceptions import ValidationError
from customer.models import NaturalPersonBase, NaturalCustomer
from django.utils.safestring import mark_safe
from django.core.validators import MaxValueValidator, MinValueValidator
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone

TWOPLACES = Decimal("0.01")


# Tipo de crédito
class CreditType(models.Model):
    CATEGORY_CHOICES = [
        ('A', 'Cat. A'),
        ('B', 'Cat. B'),
        ('C', 'Cat. C'),
        ('D', 'Cat. D'),
        ('E', 'Cat. E'),
    ]
    GUARANTEE_TYPE_CHOICES = [
        ("NONE", "Sin respaldo"),
        ("GUARANTOR", "Fiador"),
        ("GUARANTEE", "Activo o bien"),
    ]

    code = models.CharField(
        "Código",
        max_length=20,
        unique=True,
        help_text = mark_safe("""
            Código único del crédito.<br>
            Ej: PERSONAL, HIPOTECARIO, EMPRESARIAL...
        """)
    )
    category = models.CharField("Categoría del crédito",
        max_length=1,
        choices=CATEGORY_CHOICES,
        help_text = mark_safe("""
            La categoría del crédito determina qué clientes pueden acceder a él.<br>
            Ejemplo: <strong>un cliente con clasificación B no puede optar a créditos de categoría A.</strong>
        """)

    )
    name = models.CharField(
        "Nombre del crédito",
        max_length=100,
        help_text="Nombre comercial del producto."
    )
    description = models.TextField("Descripción del crédito", blank=True, null=True)
    guarantee_type = models.CharField(
        "Garantía",
        max_length=10,
        choices=GUARANTEE_TYPE_CHOICES,
        default="NONE",
        help_text="Respaldo requerido para el crédito"
    )
    annual_interest_rate = models.PositiveIntegerField(
        "Tasa de interés anual",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=mark_safe("""
            Tasa de interés anual expresada en porcentaje.<br>
            Ejemplo: <strong>24</strong> para una tasa del 24%.
        """)
    )


    class Meta:
        verbose_name = "Tipo de Crédito"
        verbose_name_plural = "Tipos de Crédito"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name}"


# Fiador
class Guarantor(NaturalPersonBase):
    customer = models.ForeignKey(
        NaturalCustomer,
        on_delete=models.CASCADE,
        related_name="guarantors",
        verbose_name="En garantía de cliente",
        help_text="Cliente al que respalda este fiador."
    )
    relationship = models.CharField(
        "Relación con el cliente",
        max_length=50,
    )


    class Meta:
        verbose_name = "Fiador"
        verbose_name_plural = "Fiadores"
        ordering = ["customer", "last_name"]

    def clean(self):
        if self.income <= self.expenses:
            raise ValidationError({
                "income": "Los ingresos deben ser mayores a los egresos.",
                "expenses": "Los egresos no pueden ser mayores que los ingresos."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - Fiador de {self.customer}"
    

# Garantía
class Guarantee(models.Model):

    customer = models.ForeignKey(
        NaturalCustomer,
        on_delete=models.CASCADE,
        related_name="real_guarantees",
        verbose_name="Cliente",
    )

    description = models.TextField(
        "Descripción de la garantía",
        help_text="Descripción detallada de la garantía aportada."
    )

    commercial_value = models.DecimalField(
        "Valor comercial",
        max_digits=12,
        decimal_places=2
    )

    forced_sale_value = models.DecimalField(
        "Valor de realización (remate)",
        max_digits=12,
        decimal_places=2,
        help_text="Valor estimado de venta rápida en caso de recuperación."
    )

    documents = models.FileField(
        "Documentación soporte (PDF)",
        upload_to="credit/real_guarantees/",
        blank=True,
        null=True,
        help_text="Suba documentos como escrituras, tarjeta de circulación, certificaciones, etc."
    )


    class Meta:
        verbose_name = "Garantía"
        verbose_name_plural = "Garantías"
        ordering = ["customer"]

    def __str__(self):
        return f"Garantía de {self.customer}"


# Contrato de credito
class Credit(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Activo"),
        ("WRITEOFF", "Incobrable"),
        ("PAID", "Liquidado"),
    ]

    credit_date = models.DateField("Fecha del crédito")
    customer = models.ForeignKey(
        NaturalCustomer,
        on_delete=models.CASCADE,
        verbose_name = "Cliente"
    )
    credit_type = models.ForeignKey(
        CreditType,
        on_delete=models.PROTECT,
        verbose_name = "Tipo de crédito"
    )
    amount = models.DecimalField(
        "Monto",
        max_digits=12,
        decimal_places=2,
    )
    quotas = models.PositiveIntegerField(
        "Número de cuotas",
        help_text = "Número de cuotas, ej: para <strong>12</strong> meses."
    )
    annual_default_interest_rate = models.PositiveIntegerField(
        "Tasa de interés moratoria anual",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=mark_safe("""
            Tasa de interés moratoria anual expresada en porcentaje.<br>
            Ejemplo: <strong>5</strong> para una tasa del 5%.
        """)
    )
    guarantee = models.ForeignKey(
        Guarantee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name = "Garantía",
        help_text = "Garantía correspondiente al tipo de crédito."
    )
    guarantee_fiador = models.ForeignKey(
        Guarantor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name = "Fiador"
    )
    pdf_credit_contract = models.FileField(
        "Contrato de crédito (PDF)",
        upload_to="credit/contract/",
        help_text="Archivo PDF con el contrato fisico firmado."
    )
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        editable=False
    )

    def fixed_installment(self):
        """
        Calcula la cuota fija mensual usando el método francés de amortización.
        Devuelve un Decimal redondeado a 2 decimales.
        """
        P = self.amount
        n = self.quotas
        annual_rate = self.credit_type.annual_interest_rate
        r = Decimal(annual_rate) / Decimal(12 * 100) 

        if r == 0:
            cuota = P / n
        else:
            cuota = P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

        return cuota.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    

    class Meta:
        verbose_name = "Contrato de Crédito"
        verbose_name_plural = "Contratos de Crédito"

    def clean(self):
        super().clean()

        if self.credit_type.guarantee_type == "GUARANTOR" and not self.guarantee_fiador:
            raise ValidationError({"guarantee_fiador": "Este crédito requiere un fiador."})

        if self.credit_type.guarantee_type == "GUARANTEE" and not self.guarantee:
            raise ValidationError({"guarantee": "Este crédito requiere una garantía."})

        if self.credit_type.guarantee_type == "NONE" and (self.guarantee or self.guarantee_fiador):
            raise ValidationError("Este crédito no debe tener garantías.")
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.credit_type.name} [Cat. {self.credit_type.category}] - {self.customer}"


# Cuenta de pagos de crédito
class CreditAccount(models.Model):
    credit = models.OneToOneField(
        Credit,  
        on_delete=models.CASCADE,
        related_name="account",
        verbose_name="Crédito"
    )

    capital_paid = models.DecimalField(
        "Abonos a capital",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    interest_paid = models.DecimalField(
        "Intereses pagados",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    late_fees_paid = models.DecimalField(
        "Mora pagada",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    overdue_events = models.PositiveIntegerField(
        "Número de caídas en mora",
        default=0,
        help_text="Cantidad de veces que el crédito entró en mora."
    )


    class Meta:
        verbose_name = "Cuenta de Crédito"
        verbose_name_plural = "Cuenta de Créditos"

    def __str__(self):
        return f"{self.credit.credit_type.name} - {self.credit.customer}"


# Cuotas del crédito
class LoanInstallment(models.Model):
    account = models.ForeignKey(
        CreditAccount,
        on_delete=models.CASCADE,
        related_name="installments",
        verbose_name="Cuenta de crédito",
    )
    due_date = models.DateField("Fecha de vencimiento")
    capital = models.DecimalField(
        "A capital",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    interest = models.DecimalField(
        "A intereses",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    late_fees = models.DecimalField(
        "A mora",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    accrued_interest = models.DecimalField(
        "Intereses acumulados",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    last_accrual_date = models.DateField("Última fecha de cálculo", null=True, blank=True)

    paid = models.BooleanField(
        "Pagado",
        default=False
    )

    @property
    def total_amount(self):
        return self.capital + self.interest + self.accrued_interest + self.late_fees
    
    def accrue_up_to(self, to_date: date):
        """
        Acumula intereses (ordinarios y moratorios) desde last_accrual_date+1 hasta to_date (inclusive).
        Idempotente: actualiza last_accrual_date a to_date.
        No actúa si paid == True.
        """
        if self.paid:
            return  # ya pagada, nada que hacer

        if self.last_accrual_date is None:
            # arrancar desde la due_date o desde la fecha de creación? 
            # Decidimos iniciar desde due_date - no acumular antes de vencimiento
            start_date = self.due_date
        else:
            start_date = self.last_accrual_date

        # queremos días *posteriores* al start_date
        current = start_date + timedelta(days=1)
        if current > to_date:
            return  # ya está actualizado

        # tasas diarias
        credit = self.account.credit
        # tasa ordinaria: usar credit.annual_interest_rate (si no hay, se puede calcular desde interest del installment)
        annual_rate = getattr(credit.credit_type, "annual_interest_rate", Decimal("0.00"))
        moratory_annual = getattr(credit, "annual_default_interest_rate", Decimal("0.00"))

        daily_rate = (Decimal(annual_rate) / Decimal("100")) / Decimal("365")
        daily_moratory_rate = (Decimal(moratory_annual) / Decimal("100")) / Decimal("365")

        # capital pendiente: aquí asumimos que self.capital representa la porción de capital de la cuota aún pendiente.
        # Si se desea considerar capital ya abonado parcial, hay que restar pagos aplicados.
        # Simplificaremos usando self.capital como base (por cuota).
        total_accrued_interest = Decimal("0.00")
        total_accrued_moratory = Decimal("0.00")

        while current <= to_date:
            # interés ordinario del día
            daily_interest = (Decimal(self.capital) * daily_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

            # si vencida (current > due_date) calculamos mora también
            if current > self.due_date:
                daily_moratory = (Decimal(self.capital) * daily_moratory_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            else:
                daily_moratory = Decimal("0.00")

            total_accrued_interest += daily_interest
            total_accrued_moratory += daily_moratory

            current += timedelta(days=1)

        # aplicar en transacción
        with transaction.atomic():
            inst = LoanInstallment.objects.select_for_update().get(pk=self.pk)

            inst.accrued_interest = (
                inst.accrued_interest + total_accrued_interest
            ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

            inst.late_fees = (
                inst.late_fees + total_accrued_moratory
            ).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

            inst.last_accrual_date = to_date

            inst.save(update_fields=["accrued_interest", "late_fees", "last_accrual_date"])



    class Meta:
        verbose_name = "Cuota de Crédito"
        verbose_name_plural = "Cuotas de Crédito"
        ordering = ["due_date"]

    def installment_number(self):
        """
        Retorna el número de esta cuota dentro del crédito, ordenado por due_date.
        """
        # Obtener todas las cuotas de este crédito ordenadas por due_date
        installments = self.account.installments.order_by("due_date")
        # Buscar el índice de esta cuota
        for idx, inst in enumerate(installments, start=1):
            if inst.pk == self.pk:
                return idx
        return "?"

    def __str__(self):
        total = self.account.installments.count()
        num = self.installment_number()
        return f"Cuota {num} - {self.account.credit}"
        return f"Cuota {num} de {total} - {self.account.credit}"

    

# Pagos de las cuotas
class LoanPayment(models.Model):
    installment = models.ForeignKey(
        LoanInstallment,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Cuota",
        help_text="Cuota a la que se aplica este pago."
    )
    payment_date = models.DateField("Fecha de pago")
    amount = models.DecimalField(
        "Monto pagado",
        max_digits=12,
        decimal_places=2,
        help_text=mark_safe("""
            Monto total pagado en esta transacción.<br>
            <strong>Si el pago excede la cuota se abona a capital, siempre y caundo no haya mas cuotas pendientes.</strong>
        """)
    )
    to_capital = models.DecimalField(
        "A capital",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    to_interest = models.DecimalField(
        "A intereses",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    to_late_fees = models.DecimalField(
        "A mora",
        max_digits=12,
        decimal_places=2,
        default=0
    )
    to_accrued_interest = models.DecimalField(
        "A ntereses acumulados",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        verbose_name = "Pago de Cuota"
        verbose_name_plural = "Pagos de Cuotas"
        ordering = ["payment_date"]       
        

    def __str__(self):
        return f"Pago {self.id} - {self.installment}"