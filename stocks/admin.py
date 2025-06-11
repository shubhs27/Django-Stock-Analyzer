from django.contrib import admin
from .models import Company, StockData


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "symbol", "created_at")
    search_fields = ("name", "symbol")
    list_filter = ("created_at",)
    ordering = ("name",)


@admin.register(StockData)
class StockDataAdmin(admin.ModelAdmin):
    list_display = (
        "company_symbol",
        "company_name",
        "date",
        "open",
        "close",
        "volume",
        "file_source",
    )
    list_filter = ("company_symbol", "date", "file_source")
    search_fields = ("company_symbol",)
    date_hierarchy = "date"
    ordering = ("-date", "company_symbol")

    # Limit the number of objects per page for performance
    list_per_page = 50

    # Read-only fields to prevent accidental modification
    readonly_fields = ("created_at",)

    def company_name(self, obj):
        return obj.company_name

    company_name.short_description = "Company Name"

    def get_queryset(self, request):
        return super().get_queryset(request)
