from django.db import models

# Create your models here.
class FixedAssetType(models.Model):
    TREATMENT_CHOICES = [
        ('DEP', 'Depreciación'),
        ('AMO', 'Amortización'),
        ('NA',  'No aplica'),
    ]
    
    code = models.CharField(
        max_length=4, 
        unique=True, 
        verbose_name="Código del tipo de activo fijo"
    )
    
    name = models.CharField(
        max_length=100, 
        verbose_name="Nombre del tipo de activo fijo",
        null=False, 
        blank=False
    )
    
    treatment = models.CharField(
        max_length=3,
        choices=TREATMENT_CHOICES,
        verbose_name="Tratamiento contable",
        default='DEP'
    )

    percentage = models.DecimalField(
        max_digits=5,          
        decimal_places=2,
        verbose_name="Porcentaje a aplicar",
        null=True,
        blank=True,
        help_text="Porcentaje anual, por ejemplo 10.00 para 10%."
    )

    life_time = models.PositiveIntegerField(
        verbose_name="Vida útil (en años)",
        null=True,
        blank=True,
        help_text="Número de años de vida útil; requerido si hay depreciación o amortización."
    )
    
    class Meta:
        verbose_name = "Tipo de Activo Fijo"
        verbose_name_plural = "Tipos de Activos Fijos"

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def set_code(self):
        if not self.code and self.id:
            self.code = f"{self.id:04d}"
    
    def save(self, *args, **kwargs):

        creating = self.pk is None
        super().save(*args, **kwargs)
        
        if creating and not self.code:
            self.set_code()
            super().save(update_fields=["code"])
