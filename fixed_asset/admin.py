from django.contrib import admin
from django import forms
from django.template.response import TemplateResponse

from .models import (
    FixedAssetType,
    FixedAsset,
    FixedAssetCharacteristics,
    Reportes,
)


# =========================
#  FixedAssetType
# =========================

class FixedAssetTypeAdminForm(forms.ModelForm):
    class Meta:
        model = FixedAssetType
        # No pedimos 'code' al crear
        fields = ["name", "treatment", "percentage", "life_time"]


class FixedAssetTypeAdmin(admin.ModelAdmin):
    form = FixedAssetTypeAdminForm
    list_display = ("code", "name", "treatment", "percentage", "life_time")
    search_fields = ("code", "name")
    ordering = ("code",)

    def get_fields(self, request, obj=None):
        # Al crear: no mostramos el código
        if obj is None:
            return ("name", "treatment", "percentage", "life_time")
        return ("code", "name", "treatment", "percentage", "life_time")

    def save_model(self, request, obj, form, change):
        creating = obj.pk is None
        # 1) guardamos primero para obtener el ID
        super().save_model(request, obj, form, change)
        # 2) si es nuevo y no hay code, lo generamos
        if creating and not obj.code:
            obj.set_code()
            obj.save(update_fields=["code"])


admin.site.register(FixedAssetType, FixedAssetTypeAdmin)


# =========================
#  FixedAsset + Characteristics Inline
# =========================

class FixedAssetAdminForm(forms.ModelForm):
    # Campo extra SOLO de formulario, no del modelo
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        required=False,
        label="Cantidad",
        help_text="Número de activos iguales a crear con código correlativo."
    )

    class Meta:
        model = FixedAsset
        # Solo campos del modelo; 'cantidad' es un campo extra declarado arriba
        fields = ["asset_type", "department", "name", "acquisition_date", "acquisition_cost"]


class FixedAssetCharacteristicsInline(admin.StackedInline):
    model = FixedAssetCharacteristics
    extra = 1          # cuántos formularios vacíos aparecen por defecto
    min_num = 0
    can_delete = True


class FixedAssetAdmin(admin.ModelAdmin):
    form = FixedAssetAdminForm

    list_display = (
        "full_code",
        "name",
        "asset_type",
        "department",
        "acquisition_date",
        "acquisition_cost",
    )
    search_fields = ("code", "name")
    ordering = ("name", "code")

    inlines = [FixedAssetCharacteristicsInline]

    def get_fields(self, request, obj=None):
        """
        Al crear mostramos 'cantidad'; al editar ya no.
        """
        if obj is None:
            return (
                "asset_type",
                "department",
                "name",
                "acquisition_date",
                "acquisition_cost",
                "cantidad",   # campo extra del form
            )
        return (
            "code",
            "asset_type",
            "department",
            "name",
            "acquisition_date",
            "acquisition_cost",
        )

    def save_model(self, request, obj, form, change):
        """
        Aquí solo guardamos el activo "base".
        Los clones y sus características se manejan en save_related.
        """
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """
        1) Dejamos que Django guarde las inlines normalmente.
        2) Si es creación y cantidad > 1:
            - Clonamos el FixedAsset 'cantidad-1' veces.
            - Para cada clon, copiamos las características del original.
        """
        super().save_related(request, form, formsets, change)

        # Solo queremos lógica especial al CREAR, no al editar
        if change:
            return

        cantidad = form.cleaned_data.get("cantidad") or 1
        if cantidad <= 1:
            return

        original_asset = form.instance

        # Tomamos las características del activo original
        original_characteristics = list(original_asset.characteristics.all())

        # Crear activos adicionales
        for _ in range(cantidad - 1):
            new_asset = FixedAsset.objects.create(
                asset_type=original_asset.asset_type,
                department=original_asset.department,
                name=original_asset.name,
                acquisition_date=original_asset.acquisition_date,
                acquisition_cost=original_asset.acquisition_cost,
            )

            # Clonar las características para el nuevo activo
            for ch in original_characteristics:
                FixedAssetCharacteristics.objects.create(
                    fixed_asset=new_asset,
                    characteristics=ch.characteristics,
                )

    def full_code(self, obj):
        asset_code = obj.code or "----"
        dept_code = obj.department.code if obj.department_id and getattr(obj.department, "code", None) else "----"
        typ_code = obj.asset_type.code if obj.asset_type_id and getattr(obj.asset_type, "code", None) else "----"
        inst_code = (
            obj.department.institution.code
            if obj.department_id
            and getattr(obj.department, "institution", None)
            and getattr(obj.department.institution, "code", None)
            else "----"
        )
        return f"{inst_code}-{dept_code}-{typ_code}-{asset_code}"

    full_code.short_description = "Código completo del activo fijo"


admin.site.register(FixedAsset, FixedAssetAdmin)



@admin.register(Reportes)
class ReportesAdmin(admin.ModelAdmin):
    """
    Admin que no lista registros, sino una página con links a reportes.
    NO usa ChangeList, así evitamos que toque la base de datos.
    """
    change_list_template = "admin/reportes_changelist.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # No se permite editar nada, solo ver la página
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """
        Por seguridad, devolvemos un queryset vacío, pero en realidad
        nunca lo usamos porque no llamamos a super().changelist_view().
        """
        return Reportes.objects.none()

    def changelist_view(self, request, extra_context=None):
        """
        Renderizamos la plantilla directamente, sin pasar por la lógica
        estándar de ChangeList (que intenta leer la tabla en BD).
        """
        extra_context = extra_context or {}
        extra_context["reportes"] = [
            {
                "nombre": "Activos por Departamento (PDF)",
                "descripcion": "Listado de activos fijos agrupados por departamento.",
                "url": "/reportes/activos-por-departamento/",  # tu URL
            },
            {
                "nombre": "Activos depreciados este año",
                "descripcion": "Reporte de activos con depreciación en el año actual.",
                "url": "/reportes/depreciacion-actual/",
            },
            {
                "nombre": "Inventario de Activos",
                "descripcion": "Resumen general de todos los activos fijos.",
                "url": "/reportes/inventario-activos/",
            },
            # Agrega más reportes aquí...
        ]

        context = {
            **self.admin_site.each_context(request),  # contexto estándar del admin
            "opts": self.model._meta,
            "title": "Reportes",
            **extra_context,
        }

        return TemplateResponse(request, self.change_list_template, context)