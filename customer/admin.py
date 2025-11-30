from django.contrib import admin
from .models import NaturalCustomer, JuridicalCustomer, Guarantor


# ----------------------------
# Admin para Cliente Natural
# ----------------------------
@admin.register(NaturalCustomer)
class NaturalCustomerAdmin(admin.ModelAdmin):
    list_display = ("code", "first_name", "last_name", "institution", "adviser")
    list_filter = ("institution", "adviser")
    search_fields = ("code", "first_name", "last_name", "dui")

    fieldsets = (
        ("Datos de Colocación", {
            "fields": ("institution", "adviser")
        }),
        ("Información Personal", {
            "fields": ("first_name", "last_name", "dui", "marital_status")
        }),
        ("Contacto", {
            "fields": ("phone_number", "email", "address")
        }),
        ("Finanzas", {
            "fields": ("income", "expenses")
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

    fieldsets = (
        ("Datos de Colocación", {
            "fields": ("institution", "adviser")
        }),
        ("Información de la Empresa", {
            "fields": ("company_name", "phone_number", "email", "address")
        }),
        ("Información Financiera", {
            "fields": ("pdf_financial_information",)
        }),
    )


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


