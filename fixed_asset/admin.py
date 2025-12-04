from urllib import request
from django.contrib import admin
from django import forms
from django.template.response import TemplateResponse
from django.contrib.admin.widgets import AutocompleteSelect
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

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
        fields = ["name", "treatment", "life_time"]


class FixedAssetTypeAdmin(admin.ModelAdmin):
    form = FixedAssetTypeAdminForm
    list_display = ("code", "name", "treatment", "percentage", "life_time")
    search_fields = ("code", "name", "treatment")
    ordering = ("code",)
    readonly_fields = ("code", "percentage") 

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
    search_fields = ("code", "name", "department__name", "asset_type__name")
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
    
    readonly_fields = ("code",)

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


class DepreciacionesFiltroForm(forms.Form):
    fixed_asset = forms.ModelChoiceField(
        queryset=FixedAsset.objects
            .filter(asset_type__treatment="DEP")
            .select_related("department", "asset_type")
            .order_by("department__name", "name"),
        required=False,
        label="Activo fijo",
        widget=forms.Select(
            attrs={
                "class": "vSelect",           # estilo admin
                "style": "min-width: 320px;", # que no quede enano
            }
        )
    )

class AmortizacionesFiltroForm(forms.Form):
    fixed_asset = forms.ModelChoiceField(
        queryset=FixedAsset.objects
            .filter(asset_type__treatment="AMO")  # ← SOLO activos con tratamiento AMO
            .select_related("department", "asset_type")
            .order_by("department__name", "name"),
        required=False,
        label="Activo / Intangible",
        widget=forms.Select(
            attrs={
                "class": "vSelect",           # estilo admin
                "style": "min-width: 320px;", # que no quede enano
            }
        )
    )


def calcular_depreciacion_linea_recta(activo: FixedAsset, fecha_corte: date | None = None) -> dict:
    """
    Calcula depreciación en línea recta para un activo fijo.

    Retorna un dict con:
    - annual_depr
    - monthly_depr
    - daily_depr
    - accumulated_depr
    - book_value
    - elapsed_days
    - life_days
    """
    if fecha_corte is None:
        fecha_corte = date.today()

    tipo = activo.asset_type
    vida_anios = tipo.life_time

    # Si no tiene vida útil o el tratamiento no es depreciación, todo 0
    if not vida_anios or tipo.treatment != "DEP":
        return {
            "annual_depr": Decimal("0.00"),
            "monthly_depr": Decimal("0.00"),
            "daily_depr": Decimal("0.00"),
            "accumulated_depr": Decimal("0.00"),
            "book_value": activo.acquisition_cost,
            "elapsed_days": 0,
            "life_days": 0,
        }

    costo = activo.acquisition_cost
    base_depreciable = costo  # si luego quieres valor residual, aquí se resta
    vida_dias = vida_anios * 365

    # Depreciación anual: costo / vida útil
    annual_depr = (base_depreciable / Decimal(vida_anios)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Depreciación mensual
    monthly_depr = (annual_depr / Decimal("12")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Depreciación diaria
    daily_depr = (base_depreciable / Decimal(vida_dias)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Días transcurridos desde la adquisición hasta la fecha de corte (capados a la vida útil)
    if fecha_corte <= activo.acquisition_date:
        elapsed_days = 0
    else:
        elapsed_days = (fecha_corte - activo.acquisition_date).days
        if elapsed_days > vida_dias:
            elapsed_days = vida_dias

    # Depreciación acumulada
    accumulated_depr = (daily_depr * Decimal(elapsed_days)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # No dejar que la acumulada supere el costo
    if accumulated_depr > base_depreciable:
        accumulated_depr = base_depreciable

    # Valor en libros = costo - depreciación acumulada
    book_value = (base_depreciable - accumulated_depr).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "annual_depr": annual_depr,
        "monthly_depr": monthly_depr,
        "daily_depr": daily_depr,
        "accumulated_depr": accumulated_depr,
        "book_value": book_value,
        "elapsed_days": elapsed_days,
        "life_days": vida_dias,
    }

def calcular_amortizacion_linea_recta(activo: FixedAsset, fecha_corte: date | None = None) -> dict:
    """
    Calcula amortización en línea recta para un activo intangible (tratamiento AMO).

    Retorna un dict con:
    - annual_amo
    - monthly_amo
    - daily_amo
    - accumulated_amo
    - book_value
    - elapsed_days
    - life_days
    """
    if fecha_corte is None:
        fecha_corte = date.today()

    tipo = activo.asset_type
    vida_anios = tipo.life_time

    # Si no tiene vida útil o el tratamiento no es AMO, todo 0
    if not vida_anios or tipo.treatment != "AMO":
        return {
            "annual_amo": Decimal("0.00"),
            "monthly_amo": Decimal("0.00"),
            "daily_amo": Decimal("0.00"),
            "accumulated_amo": Decimal("0.00"),
            "book_value": activo.acquisition_cost,
            "elapsed_days": 0,
            "life_days": 0,
        }

    costo = activo.acquisition_cost
    base_amortizable = costo
    vida_dias = vida_anios * 365

    # Amortización anual: costo / vida útil
    annual_amo = (base_amortizable / Decimal(vida_anios)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Amortización mensual
    monthly_amo = (annual_amo / Decimal("12")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Amortización diaria
    daily_amo = (base_amortizable / Decimal(vida_dias)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Días transcurridos
    if fecha_corte <= activo.acquisition_date:
        elapsed_days = 0
    else:
        elapsed_days = (fecha_corte - activo.acquisition_date).days
        if elapsed_days > vida_dias:
            elapsed_days = vida_dias

    # Amortización acumulada
    accumulated_amo = (daily_amo * Decimal(elapsed_days)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if accumulated_amo > base_amortizable:
        accumulated_amo = base_amortizable

    # Valor en libros
    book_value = (base_amortizable - accumulated_amo).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "annual_amo": annual_amo,
        "monthly_amo": monthly_amo,
        "daily_amo": daily_amo,
        "accumulated_amo": accumulated_amo,
        "book_value": book_value,
        "elapsed_days": elapsed_days,
        "life_days": vida_dias,
    }

@admin.register(Reportes)
class ReportesAdmin(admin.ModelAdmin):
    """
    Admin que muestra un menú de reportes y dos vistas internas:
    - Depreciaciones
    - Amortizaciones
    Todo se mantiene dentro del admin.
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
        Devolvemos un queryset vacío solo para que el admin no intente
        listar registros reales (el modelo es solo 'virtual').
        """
        return Reportes.objects.none()

    # ---- URLs personalizadas dentro del admin ----
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        custom_urls = [
            path(
                "depreciaciones/",
                self.admin_site.admin_view(self.depreciaciones_view),
                name=f"{app_label}_{model_name}_depreciaciones",
            ),
            path(
                "amortizaciones/",
                self.admin_site.admin_view(self.amortizaciones_view),
                name=f"{app_label}_{model_name}_amortizaciones",
            ),
        ]
        # Nuestras URLs primero, luego las estándar del admin
        return custom_urls + urls

    # ---- Vista principal: menú de reportes ----
    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        depreciaciones_url = reverse(
            f"admin:{app_label}_{model_name}_depreciaciones"
        )
        amortizaciones_url = reverse(
            f"admin:{app_label}_{model_name}_amortizaciones"
        )

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Reportes",
            "depreciaciones_url": depreciaciones_url,
            "amortizaciones_url": amortizaciones_url,
        }

        return TemplateResponse(request, self.change_list_template, context)

    # ---- Vista de DEPRECIACIONES ----
    def depreciaciones_view(self, request):
        selected_asset = None
        table_data = None

        if request.method == "POST":
            form = DepreciacionesFiltroForm(request.POST)
            if form.is_valid():
                selected_asset = form.cleaned_data.get("fixed_asset")
                if selected_asset:
                    # 👉 Calculamos la depreciación a la fecha de hoy (puedes cambiarla a una fecha de corte)
                    info_dep = calcular_depreciacion_linea_recta(selected_asset, date.today())

                    code_fixedAsset = selected_asset.code or "----"
                    dept_code = selected_asset.department.code if selected_asset.department_id and getattr(selected_asset.department, "code", None) else "----"
                    typ_code = selected_asset.asset_type.code if selected_asset.asset_type_id and getattr(selected_asset.asset_type, "code", None) else "----"
                    inst_code = (
                        selected_asset.department.institution.code if selected_asset.department_id and selected_asset.department.institution_id and getattr(selected_asset.department.institution, "code", None) else "----"
                    )

                    code_full = f"{inst_code}-{dept_code}-{typ_code}-{code_fixedAsset}"

                    table_data = [
                        {
                            "code": code_full,
                            "name": selected_asset.name,
                            "department": selected_asset.department.name,
                            "cost": selected_asset.acquisition_cost,
                            "life_time": selected_asset.asset_type.life_time,
                            "acquisition_date": selected_asset.acquisition_date,
                            "annual_depr": info_dep["annual_depr"],
                            "monthly_depr": info_dep["monthly_depr"],
                            "daily_depr": info_dep["daily_depr"],
                            "accum_depr": info_dep["accumulated_depr"],
                            "book_value": info_dep["book_value"],
                            "elapsed_days": info_dep["elapsed_days"],
                            "life_days": info_dep["life_days"],
                        }
                    ]
        else:
            form = DepreciacionesFiltroForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Reporte de Depreciaciones",
            "form": form,
            "selected_asset": selected_asset,
            "table_data": table_data,
        }
        return TemplateResponse(
            request,
            "admin/reportes_depreciaciones.html",
            context,
        )



    # ---- Vista de AMORTIZACIONES ----
    def amortizaciones_view(self, request):
        selected_asset = None
        table_data = None

        if request.method == "POST":
            form = AmortizacionesFiltroForm(request.POST)
            if form.is_valid():
                selected_asset = form.cleaned_data.get("fixed_asset")
                if selected_asset:
                    info_amo = calcular_amortizacion_linea_recta(selected_asset, date.today())

                    code_fixedAsset = selected_asset.code or "----"
                    dept_code = selected_asset.department.code if selected_asset.department_id and getattr(selected_asset.department, "code", None) else "----"
                    typ_code = selected_asset.asset_type.code if selected_asset.asset_type_id and getattr(selected_asset.asset_type, "code", None) else "----"
                    inst_code = (
                        selected_asset.department.institution.code
                        if selected_asset.department_id
                        and selected_asset.department.institution_id
                        and getattr(selected_asset.department.institution, "code", None)
                        else "----"
                    )

                    code_full = f"{inst_code}-{dept_code}-{typ_code}-{code_fixedAsset}"

                    table_data = [
                        {
                            "code": code_full,
                            "name": selected_asset.name,
                            "department": selected_asset.department.name,
                            "cost": selected_asset.acquisition_cost,
                            "life_time": selected_asset.asset_type.life_time,
                            "acquisition_date": selected_asset.acquisition_date,
                            "annual_amo": info_amo["annual_amo"],
                            "monthly_amo": info_amo["monthly_amo"],
                            "daily_amo": info_amo["daily_amo"],
                            "accum_amo": info_amo["accumulated_amo"],
                            "book_value": info_amo["book_value"],
                            "elapsed_days": info_amo["elapsed_days"],
                            "life_days": info_amo["life_days"],
                        }
                    ]
        else:
            form = AmortizacionesFiltroForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Reporte de Amortizaciones",
            "form": form,
            "selected_asset": selected_asset,
            "table_data": table_data,
        }
        return TemplateResponse(
            request,
            "admin/reportes_amortizaciones.html",
            context,
        )