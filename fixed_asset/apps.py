from django.apps import AppConfig


class FixedAssetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fixed_asset'
    verbose_name = "Activo Fijo"