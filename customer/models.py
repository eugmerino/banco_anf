from django.db import models
from django.utils import timezone
from organization.models import Institution
from employee.models import CreditAdvisor
from django.core.exceptions import ValidationError


# Base para datos comunes de un persona natural
class NaturalPersonBase(models.Model):
    MARITAL_STATUS_CHOICES = [
        ('S', 'Soltero/a'),
        ('C', 'Casado/a'),
        ('D', 'Divorciado/a'),
        ('V', 'Viudo/a'),
    ]

    first_name = models.CharField("Nombres", max_length=200)
    last_name = models.CharField("Apellidos", max_length=200)
    dui = models.CharField("DUI", max_length=10, unique=True)
    marital_status = models.CharField("Estado Civil", max_length=1, choices=MARITAL_STATUS_CHOICES)
    address = models.TextField("Dirección")
    income = models.DecimalField("Ingresos", max_digits=12, decimal_places=2, default=0.00)
    expenses = models.DecimalField("Egresos", max_digits=12, decimal_places=2, default=0.00)
    phone_number = models.CharField("Teléfono", max_length=15, unique=True)
    email = models.EmailField("Correo Electrónico", blank=True, null=True)

    class Meta:
        abstract = True


# Base para datos comunes de un cliente
class CustomerBase(models.Model):
    code = models.CharField(
        "Código de Cliente",
        max_length=20,
        unique=True,
        editable=False,
        help_text="El código se genera automáticamente"
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        verbose_name="Institución",
        help_text="Sucursal donde se registra el cliente"
    )
    adviser = models.ForeignKey(
        CreditAdvisor,
        on_delete=models.CASCADE,
        verbose_name="Asesor de Crédito",
        help_text="Asesor de crédito asignado al cliente"
    )
    phone_number = models.CharField("Teléfono", max_length=15)
    email = models.EmailField("Correo Electrónico")
    address = models.TextField("Dirección")

    class Meta:
        abstract = True


# Cliente natural
class NaturalCustomer(CustomerBase, NaturalPersonBase):

    class Meta:
        verbose_name = "Cliente Natural"
        verbose_name_plural = "Clientes Naturales"
        ordering = ["code"]

    def clean(self):
        # Validación de ingresos > egresos
        if self.income <= self.expenses:
            raise ValidationError({
                "income": "Los ingresos deben ser mayores a los egresos.",
                "expenses": "Los egresos no pueden ser mayores que los ingresos."
            })

    def save(self, *args, **kwargs):
        self.full_clean()  # llama a clean antes de guardar
        if not self.code:
            today = timezone.localtime().date()
            year = str(today.year)[-2:]
            month = f"{today.month:02d}"
            count = NaturalCustomer.objects.filter(institution=self.institution).count() + 1
            self.code = f"CN-{self.institution.code}-{year}{month}-{count:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.code}) {self.first_name} {self.last_name}"


# Cliente jurídico
class JuridicalCustomer(CustomerBase):
    company_name = models.CharField("Nombre de la Empresa", max_length=200)
    pdf_financial_information = models.FileField(
        "Información Financiera (PDF)",
        upload_to="customer/financial_info/",
        help_text="Archivo PDF con la información financiera de la empresa"
    )

    class Meta:
        verbose_name = "Cliente Jurídico"
        verbose_name_plural = "Clientes Jurídicos"
        ordering = ["code"]

    def save(self, *args, **kwargs):
        if not self.code:
            today = timezone.localtime().date()
            year = str(today.year)[-2:]
            month = f"{today.month:02d}"
            count = JuridicalCustomer.objects.filter(institution=self.institution).count() + 1
            self.code = f"CJ-{self.institution.code}-{year}{month}-{count:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.code}) {self.company_name}"


# Fiador
class Guarantor(NaturalPersonBase):
    customer = models.ForeignKey(
        NaturalCustomer,
        on_delete=models.CASCADE,
        related_name="guarantors",
        verbose_name="En Garantía de Cliente",
        help_text="Cliente al que respalda este fiador"
    )
    relationship = models.CharField(
        "Relación con el cliente",
        max_length=50,
    )

    class Meta:
        verbose_name = "Fiador"
        verbose_name_plural = "Fiadores"

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
