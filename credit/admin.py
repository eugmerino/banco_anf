from django.contrib import admin
from .models import CreditType, Guarantor, Guarantee, Credit, CreditAccount,LoanInstallment, LoanPayment
from django.utils.safestring import mark_safe
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.http import JsonResponse
from django.urls import path
from .forms import LoanPaymentForm


@admin.register(CreditType)
class CreditTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "name", "guarantee_type", "annual_interest_rate")
    list_filter = ("guarantee_type",)
    search_fields = ("code", "name")
    ordering = ("code",)

    fieldsets = (
        ("Identificación", {
            "fields": ("code", "name")
        }),
        ("Descripción", {
            "fields": ("description",)
        }),
        ("Condiciones del crédito", {
            "fields": ("guarantee_type", "annual_interest_rate", "category"),
        }),
    )


    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


# ----------------------------
# Admin para Fiador
# ----------------------------
@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "customer", "relationship")
    list_filter = ("customer",)
    search_fields = ("first_name", "last_name", "dui", "customer__code")

    fieldsets = (
        ("Datos Personales", {
            "fields": ("first_name", "last_name", "dui", "marital_status")
        }),
        ("Contacto", {
            "fields": ("phone_number", "email", "address")
        }),
        ("Información de la Garantía", {
            "fields": ("customer", "relationship")
        }),
        ("Finanzas", {
            "fields": ("income", "expenses")
        }),
    )


# Garantía
@admin.register(Guarantee)
class GuaranteeAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "description",
    )
    list_filter = ("customer",)
    search_fields = (
        "customer__code",
        "customer__first_name",
        "customer__last_name",
        "description",
    )

    fieldsets = (
        ("Datos del Cliente", {
            "fields": ("customer",)
        }),
        ("Información del Activo o Bien", {
            "fields": ("description",)
        }),
        ("Valores", {
            "fields": ("commercial_value", "forced_sale_value")
        }),
        ("Documentos", {
            "fields": ("documents",)
        }),
    )

    def get_short_description(self, obj):
        """Resumen corto para no saturar la tabla."""
        if not obj.description:
            return "-"
        return (obj.description[:60] + "...") if len(obj.description) > 60 else obj.description
    get_short_description.get_short_description = "Descripción"

    def get_documents_link(self, obj):
        """Muestra enlace al PDF si existe."""
        if obj.documents:
            return mark_safe(f'<a href="{obj.documents.url}" target="_blank">Ver PDF</a>')
        return "-"
    get_documents_link.get_short_description = "Documento"

    # ---------- Validación ----------
    def save_model(self, request, obj, form, change):
        """
        full_clean() garantiza que si agregas validaciones al modelo,
        aparecerán correctamente en el admin.
        """
        obj.full_clean()
        super().save_model(request, obj, form, change)


# Widget personalizado para agregar atributos data-*
class CreditTypeSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        guarantee_type = getattr(value, 'instance', None).guarantee_type if getattr(value, 'instance', None) else "NONE"
        option['attrs']['data-guarantee-type'] = guarantee_type
        return option


# Admin de Contrato de Crédito
@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ("customer", "credit_type", "amount", "status", "credit_date")
    list_filter = ("credit_type", "status")
    search_fields = ("customer__code", "credit_type__name")

    fieldsets = (
        ("Pronósticos y proyecciones", {
            "fields": ("projection", "forecast")
        }),
        ("Información del crédito", {
            "fields": ("credit_date", "customer", "credit_type", "amount", "quotas", "annual_default_interest_rate")
        }),
        ("Garantías", {
            "fields": ("guarantee", "guarantee_fiador"),
            "description": "Los campos se muestran según la garantía que requiere el tipo de crédito seleccionado."
        }),
        ("Documentos", {
            "fields": ("pdf_credit_contract",),
        }),
    )
    readonly_fields = ("forecast", "projection")


    class Media:
        js = ("js/credit_admin.js",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "credit_type":
            field.widget = CreditTypeSelect()
        return field

    # ---------- ENLACE DEL PRONÓSTICO ----------
    def forecast(self, obj):
        if not obj:  # Cuando estás agregando (obj aún no existe)
            return "El pronóstico estará disponible después de guardar."
        url = reverse("credit_forecast", args=[obj.id])
        return format_html(f"<a href='{url}'>Ver pronóstico</a>")

    forecast.short_description = "Pronóstico de amortización del crédito"
    
    # ---------- ENLACE A PROYECCIÓN ----------
    def projection(self, obj):
        if getattr(obj, "pk", None) is None:
            url = reverse("credit_projection")
            return format_html(f"<a href='{url}'>Ver proyección</a>")
        
        return ""

    projection.short_description = "Proyección de amortización del crédito"

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        new_fieldsets = []

        for name, data in fieldsets:
            fields = list(data.get("fields", []))

            # SOLO modificar el fieldset específico
            if name == "Pronósticos y proyecciones":
                if obj is None:
                    # Estamos agregando → mostrar solo projection
                    if "forecast" in fields:
                        fields.remove("forecast")
                    if "projection" not in fields:
                        fields.append("projection")
                else:
                    # Estamos editando → mostrar solo forecast
                    if "projection" in fields:
                        fields.remove("projection")
                    if "forecast" not in fields:
                        fields.append("forecast")

            new_fieldsets.append((name, {**data, "fields": fields}))

        return new_fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))

        if obj is None:
            # Estamos agregando → queremos que se muestre projection (que es un método)
            if "projection" not in ro:
                ro.append("projection")
            # Y quitamos forecast
            if "forecast" in ro:
                ro.remove("forecast")
        else:
            # Estamos editando → queremos forecast, no projection
            if "forecast" not in ro:
                ro.append("forecast")
            if "projection" in ro:
                ro.remove("projection")

        return ro

    

# Cuenta de pagos de crédito
@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ("credit", "capital_paid", "interest_paid", "late_fees_paid", "overdue_events")
    list_filter = ("credit__credit_type__name", "credit__credit_type__category")
    search_fields = (
        "credit__credit_type__name",
        "credit__credit_type__category",
        "credit__customer__code",
        "credit__customer__first_name",
        "credit__customer__last_name")
    readonly_fields = ("credit", "capital_paid", "interest_paid", "late_fees_paid", "overdue_events")

    def has_add_permission(self, request):
        return False  # No permitir agregar manualmente

    def has_delete_permission(self, request, obj=None):
        return False  # No permitir eliminar

    def has_change_permission(self, request, obj=None):
        return False  # No permitir editar




# -------------------------------
# Inline para ver los pagos dentro de la cuota
# -------------------------------
class LoanPaymentInline(admin.TabularInline):
    model = LoanPayment
    extra = 0
    can_delete = False
    readonly_fields = ("payment_date", "amount")
    verbose_name = "Pago"
    verbose_name_plural = "Pagos de la cuota"

    def has_add_permission(self, request, obj=None):
        return False  # no permitir agregar pagos desde la cuota


# -------------------------------
# ADMIN de cuotas del crédito (solo lectura)
# -------------------------------
@admin.register(LoanInstallment)
class LoanInstallmentAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "id",
        "due_date",
        "capital",
        "interest",
        "late_fees",
        "total_to_pay",
        "paid",
    )

    list_filter = (
        "paid",
        "due_date",
        "account__credit__credit_type",
    )

    search_fields = (
        "account__credit__customer__name",
        "credit__id",
        "id",
    )

    readonly_fields = (
        "account",
        "due_date",
        "capital",
        "interest",
        "late_fees",
        "paid",
    )

    inlines = [LoanPaymentInline]

    def has_add_permission(self, request):
        return False  # no pueden crearse cuotas manualmente

    def has_change_permission(self, request, obj=None):
        return False  # no se pueden editar

    def has_delete_permission(self, request, obj=None):
        return False  # no se pueden eliminar
    
    def total_to_pay(self, obj):
        return obj.capital + obj.interest + obj.late_fees
    
    total_to_pay.short_description = "Total a pagar"



# -------------------------------
# ADMIN de pagos
# -------------------------------
@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    form = LoanPaymentForm
    list_display = ("installment", "payment_date", "amount")

    fieldsets = (
        ("Registro de pagos", {
            "description": "Registrar pagos a cuotas específicas del crédito.",
            "fields": ("installment", "payment_date", "amount")
        }),
    )

    class Media:
        js = ("js/credit_admin.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "get-installment-data/<int:pk>/",
                self.admin_site.admin_view(self.get_installment_data),
                name="get-installment-data",
            ),
        ]
        return custom_urls + urls

    def get_installment_data(self, request, pk):
        installment = LoanInstallment.objects.get(pk=pk)
        data = {
            "capital": float(installment.capital),
            "interest": float(installment.interest),
            "late_fees": float(installment.late_fees),
            "total": float(installment.capital + installment.interest + installment.late_fees),
            "due_date": installment.due_date,
        }
        return JsonResponse(data)
    

    
