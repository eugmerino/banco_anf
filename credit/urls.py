from django.urls import path
from . import views

urlpatterns = [
    path('credito/pronostico/<int:credit_id>/', views.credit_forecast_view, name="credit_forecast"),
    path('credito/proyeccion/', views.credit_projection_view, name="credit_projection"),
]
