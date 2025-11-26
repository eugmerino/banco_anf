# admin.py
from django.contrib import admin
from django import forms
from .models import FixedAssetType

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