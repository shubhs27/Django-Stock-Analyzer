from django.urls import path
from . import views

app_name = "stocks"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/chart-data/", views.get_chart_data, name="chart_data"),
]
