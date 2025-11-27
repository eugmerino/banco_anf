from django.db import models
from django.utils import timezone
from organization.models import Institution
from employee.models import CreditAdvisor


class Customer(models.Model):
    TIPO_CHOICES = [
        ('CN', 'Natural'),
        ('CJ', 'Jurídico'),
    ]
    MARITAL_STATUS_CHOICES = [
        ('S', 'Soltero/a'),
        ('C', 'Casado/a'),
        ('D', 'Divorciado/a'),
        ('V', 'Viudo/a'),
    ]

    #Datos generales principales
    code = models.CharField(
        "Código", 
        max_length=20, 
        unique=True,
        editable=False,
        help_text="El código se genera automáticamente"   
    )
    type = models.CharField(max_length=1, choices=TIPO_CHOICES)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='customers',
        verbose_name="Institución"
    )
    adviser = models.ForeignKey(
        CreditAdvisor,
        on_delete=models.CASCADE,
        related_name='customers',
        verbose_name="Asesor de Crédito"
    )

    #Datos comunes
    phone_number = models.CharField("Teléfono", max_length=15, blank=True, null=True)
    email = models.EmailField("Correo Electrónico", blank=True, null=True)
    address = models.TextField("Dirección", blank=True, null=True)
    company_name = models.CharField("Nombre de la Empresa", max_length=200, blank=True, null=True)

    #Datos específicos para cliente natural
    first_name = models.CharField("Nombres", max_length=200)
    last_name = models.CharField("Apellidos", max_length=200)
    dui = models.CharField(max_length=10, unique=True, verbose_name="DUI")
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS_CHOICES)
    income = models.DecimalField(
        "Ingresos", 
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        help_text="Ingreso del cliente"
    )
    expenses = models.DecimalField(
        "Egresos", 
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        help_text="Egreso del cliente"
    )

    #Datos específicos para cliente jurídico
    pdf_financial_information = models.FileField(
        "Información Financiera (PDF)", 
        upload_to='customer/financial_info/', 
        blank=True, 
        null=True
    )