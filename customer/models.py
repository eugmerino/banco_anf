from django.db import models
from django.utils import timezone
from organization.models import Institution
from employee.models import CreditAdvisor
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe


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
    marital_status = models.CharField("Estado civil", max_length=1, choices=MARITAL_STATUS_CHOICES)
    address = models.TextField("Dirección")
    income = models.DecimalField("Ingresos", max_digits=12, decimal_places=2, default=0.00)
    expenses = models.DecimalField("Egresos", max_digits=12, decimal_places=2, default=0.00)
    phone_number = models.CharField("Teléfono", max_length=15, unique=True)
    email = models.EmailField("Correo electrónico", blank=True, null=True)

    class Meta:
        abstract = True


# Base para datos comunes de un cliente
class CustomerBase(models.Model):
    CLASSIFICATION_CHOICES = [
        ('X', 'Cliente sin clasificar'),
        ('A', 'Cliente A'),
        ('B', 'Cliente B'),
        ('C', 'Cliente C'),
        ('D', 'Cliente D'),
        ('E', 'Cliente E'),
    ]
    code = models.CharField(
        "Código de cliente",
        max_length=20,
        unique=True,
        editable=False,
        help_text="El código se genera automáticamente."
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        verbose_name="Institución",
        help_text="Sucursal donde se registra el cliente."
    )
    adviser = models.ForeignKey(
        CreditAdvisor,
        on_delete=models.CASCADE,
        verbose_name="Asesor de crédito",
        help_text="Asesor de crédito asignado al cliente."
    )
    phone_number = models.CharField("Teléfono", max_length=15)
    email = models.EmailField("Correo electrónico")
    address = models.TextField("Dirección")
    classification = models.CharField("Clasificación del cliente",
        max_length=1,
        choices=CLASSIFICATION_CHOICES,
        default = "X",
        help_text = mark_safe("""
            Clasificación en base a evaluación de su información financiera para nuevos clientes.<br>
            <strong>No se podrá editar manualmente después de clasificarlo.</strong>
        """)
    )

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
        self.full_clean()
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
    company_name = models.CharField("Nombre de la empresa", max_length=200)
    pdf_financial_information = models.FileField(
        "Información financiera (PDF)",
        upload_to="customer/financial_info/",
        help_text="Archivo PDF con la información financiera de la empresa."
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

