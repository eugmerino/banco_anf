from django.contrib import admin
from .models import NaturalCustomer, JuridicalCustomer


# ----------------------------
# Admin para Cliente Natural
# ----------------------------
@admin.register(NaturalCustomer)
class NaturalCustomerAdmin(admin.ModelAdmin):
    list_display = ("code", "first_name", "last_name", "institution", "adviser")
    list_filter = ("institution", "adviser")
    search_fields = ("code", "first_name", "last_name", "dui")

    readonly_fields_base = ("code",)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.readonly_fields_base

        # Si fue creado y tiene clasificación = "X" → editable
        if obj.classification == "X":
            return self.readonly_fields_base

        # Si ya está clasificado con un valor real → readonly
        return self.readonly_fields_base + ("classification",)

    fieldsets = (
        ("Datos de Colocación", {
            "fields": ("institution", "adviser", "code")
        }),
        ("Información Personal", {
            "fields": ("first_name", "last_name", "dui", "marital_status")
        }),
        ("Contacto", {
            "fields": ("phone_number", "email", "address")
        }),
        ("Finanzas", {
            "fields": ("income", "expenses", "classification")
        }),

    )


# ----------------------------
# Admin para Cliente Jurídico
# ----------------------------
@admin.register(JuridicalCustomer)
class JuridicalCustomerAdmin(admin.ModelAdmin):
    list_display = ("code", "company_name", "institution", "adviser")
    list_filter = ("institution", "adviser")
    search_fields = ("code", "company_name")

    readonly_fields_base = ("code",)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return self.readonly_fields_base

        # Si fue creado y tiene clasificación = "X" → editable
        if obj.classification == "X":
            return self.readonly_fields_base

        # Si ya está clasificado con un valor real → readonly
        return self.readonly_fields_base + ("classification",)

    fieldsets = (
        ("Datos de Colocación", {
            "fields": ("institution", "adviser", "code")
        }),
        ("Información de la Empresa", {
            "fields": ("company_name", "phone_number", "email", "address")
        }),
        ("Información Financiera", {
            "fields": ("pdf_financial_information", "classification",)
        }),
    )



