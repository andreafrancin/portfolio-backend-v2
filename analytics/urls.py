from django.urls import path

from .views import ReportView, SettingsView

urlpatterns = [
    path("report/", ReportView.as_view(), name="analytics-report"),
    path("settings/", SettingsView.as_view(), name="analytics-settings"),
]
