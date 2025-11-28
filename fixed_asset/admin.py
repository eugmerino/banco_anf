# admin.py
from django.contrib import admin
from django import forms
from .models import FixedAssetType, FixedAsset

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

class FixedAssetAdminForm(forms.ModelForm):
    class Meta:
        fields = ["asset_type", "department", "name", "acquisition_date", "acquisition_cost"]

class FixedAssetAdmin(admin.ModelAdmin):
    form = FixedAssetAdminForm
    list_display = ("full_code", "name", "asset_type", "department", "acquisition_date", "acquisition_cost")
    search_fields = ("full_code", "name")
    ordering = ("name","code")

    def get_fields(self, request, obj=None):
        # Al crear: no mostramos el código
        if obj is None:
            return ("asset_type", "department", "name", "acquisition_date", "acquisition_cost")
        
        return ("code", "asset_type", "department", "name", "acquisition_date", "acquisition_cost")
    
    def full_code(self, obj):
        asset_code = obj.code or "----"
        dept_code = obj.department.code if obj.department_id and obj.department.code else "----"
        typ_code = obj.asset_type.code if obj.asset_type_id and obj.asset_type.code else "----"
        inst_code = obj.department.institution.code if obj.department_id and obj.department.institution and obj.department.institution.code else "----"
        return f"{asset_code}-{dept_code}-{typ_code}-{inst_code}"

    full_code.short_description = "Código completo del activo fijo"


admin.site.register(FixedAsset, FixedAssetAdmin)