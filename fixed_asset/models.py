from django.db import models
from organization.models import Department
from django.db import transaction
from django.db.models import Max

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

class FixedAsset(models.Model):

    code = models.CharField(
        max_length=10,
        verbose_name="Código del activo fijo",
        blank=True,
        null=True,
        help_text="Se autogenera por departamento como 0001, 0002, ..."
    )

    asset_type = models.ForeignKey(
        FixedAssetType, 
        on_delete=models.CASCADE,
        verbose_name="Tipo de activo fijo"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        verbose_name="Departamento"
    )
    
    name = models.CharField(
        max_length=100, 
        verbose_name="Nombre del activo fijo",
        null=False, 
        blank=False
    )
    
    acquisition_date = models.DateField(
        verbose_name="Fecha de adquisición"
    )
    
    acquisition_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Costo de adquisición"
    )
    
    class Meta:
        verbose_name = "Activo Fijo"
        verbose_name_plural = "Activos Fijos"
        constraints = [
            models.UniqueConstraint(
                fields=["department", "code"],
                name="uniq_fixedasset_department_code"
            )
        ]
        indexes = [
            models.Index(fields=["department", "code"]),
        ]

    def __str__(self):
        dept_code = self.department.code if self.department_id else "----"
        asset_code = self.code or "----"
        return f"{asset_code}-{dept_code} - {self.name}"

    def _next_code_for_department(self) -> str:
        """
        Obtiene el siguiente código de 4 dígitos para el departamento dado.
        Busca el código máximo existente (como cadena), lo convierte a int
        y suma 1. Si no hay registros, retorna '0001'.
        """
        max_code = (
            FixedAsset.objects
            .filter(department=self.department)
            .aggregate(mx=Max("code"))
            .get("mx")
        )

        if not max_code:
            return "0001"

        try:
            nxt = int(max_code) + 1
        except ValueError:
            # Si por alguna razón el código máximo no es numérico, reiniciamos.
            nxt = 1

        # 4 dígitos; si algún día quieres más, cambia 4 por 6 u otro valor
        return f"{nxt:04d}"[:4]

    def save(self, *args, **kwargs):
        # Usamos una transacción para reducir condiciones de carrera
        with transaction.atomic():
            creating = self.pk is None
            if creating and not self.code:
                self.code = self._next_code_for_department()
            super().save(*args, **kwargs)


class FixedAssetCharacteristics(models.Model):
    fixed_asset = models.ForeignKey(
        FixedAsset,
        on_delete=models.CASCADE,
        verbose_name="Activo fijo",
        related_name="characteristics"
    )

    characteristics = models.TextField(
        verbose_name="Características del activo fijo",
        help_text="Describa las características específicas del activo fijo."
    )

    class Meta:
        verbose_name = "Característica"
        verbose_name_plural = "Características"

    def __str__(self):
        return f"Características del Activo Fijo: {self.fixed_asset}"
    
class Reportes(models.Model):
    class Meta:
        managed = False
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"

    def __str__(self):
        return "Reportes"