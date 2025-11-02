from django.db import models
from django.utils import timezone
from organization.models import Institution

class CreditAdvisor(models.Model):
    code = models.CharField(
        "Código", 
        max_length=20, 
        unique=True,
        editable=False,
        help_text="El código se genera automáticamente"   
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='credit_advisors',
        verbose_name="Institución"
    )
    first_name = models.CharField("Nombres", max_length=200)
    last_name = models.CharField("Apellidos", max_length=200)
    dui = models.CharField(max_length=10, unique=True, verbose_name="DUI")
    commission = models.DecimalField(
        "Comisión (%)", 
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="% de comisión sobre colocación o recuperación"
    )

    class Meta:
        verbose_name = "Asesor de Crédito"
        verbose_name_plural = "Asesores de Crédito"
        ordering = ["code"]

    def __str__(self):
        return f"({self.code}) - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.code:
            today = timezone.localtime().date()
            year = str(today.year)[-2:]
            month = f"{today.month:02d}"

            count_today = CreditAdvisor.objects.filter(
                institution=self.institution,
            ).count() + 1

            correlativo = f"{count_today:03d}"

            self.code = f"AC-{self.institution.code}-{year}{month}-{correlativo}"

        super().save(*args, **kwargs)

    
