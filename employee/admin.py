from django.contrib import admin
from .models import CreditAdvisor

@admin.register(CreditAdvisor)
class CreditAdvisorAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'first_name',
        'last_name',
        'dui',
        'institution',
        'commission',
    )
    list_filter = ('institution',)
    search_fields = ('code', 'first_name', 'last_name', 'dui', 'institution__name')
    readonly_fields = ('code',)
    ordering = ('code',)
    fieldsets = (
        ('Información del Asesor', {
            'fields': (
                'code',
                ('first_name', 'last_name'),
                'dui',
                'institution',
                'commission',
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Evita que el campo código se edite al modificar un registro existente.
        """
        if obj:
            return self.readonly_fields + ('institution',)
        return self.readonly_fields
