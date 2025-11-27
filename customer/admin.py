from django.contrib import admin
from django import forms
from .models import Customer


class CustomerAdminForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'

    class Media:
        js = ("admin/js/customer_type_toggle.js",)  # archivo JS opcional para ocultar campos visualmente


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    list_display = ("code", "first_name", "last_name", "type", "institution", "adviser")
    list_filter = ("type", "institution")
    search_fields = ("code", "first_name", "last_name", "dui")

    # ----------------------------
    # FIELDSETS DINÁMICOS
    # ----------------------------
    def get_fieldsets(self, request, obj=None):
        """
        Este método define qué campos mostrar dependiendo del valor del tipo
        cuando se edita o crea el objeto.
        """

        # campos siempre visibles (primera parte del form)
        main_fields = (
            "type",
            "institution",
            "adviser",
        )

        common_fields = (
            "phone_number",
            "email",
            "address",
            "company_name",
        )

        natural_fields = (
            "first_name",
            "last_name",
            "dui",
            "marital_status",
            "income",
            "expenses",
        )

        juridico_fields = (
            "pdf_financial_information",
        )

        # Si estamos editando un cliente existente
        if obj:
            if obj.type == "CN":  # Natural
                return [
                    ("Datos principales", {"fields": main_fields}),
                    ("Datos comunes", {"fields": common_fields}),
                    ("Datos del cliente natural", {"fields": natural_fields}),
                ]

            else:  # Jurídico
                return [
                    ("Datos principales", {"fields": main_fields}),
                    ("Datos comunes", {"fields": common_fields}),
                    ("Datos del cliente jurídico", {"fields": juridico_fields}),
                ]

        # Si estamos creando un cliente → solo mostrar la primera parte
        return [
            ("Datos principales", {"fields": main_fields}),
        ]

    # ----------------------------
    # HABILITAR CAMPOS DINÁMICOS AL CREAR
    # ----------------------------
    def get_fields(self, request, obj=None):
        """Evita que Django use el orden estándar y respeta los fieldsets."""
        return [field for fs in self.get_fieldsets(request, obj) for field in fs[1]["fields"]]

