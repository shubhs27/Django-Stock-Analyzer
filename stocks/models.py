from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.symbol})"

    class Meta:
        verbose_name_plural = "Companies"
        db_table = "stocks_company"


class StockData(models.Model):
    id = models.AutoField(primary_key=True)
    company_symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField()
    open = models.DecimalField(max_digits=10, decimal_places=2)
    high = models.DecimalField(max_digits=10, decimal_places=2)
    low = models.DecimalField(max_digits=10, decimal_places=2)
    close = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()
    file_source = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def company_name(self):
        try:
            company = Company.objects.get(symbol=self.company_symbol)
            return company.name
        except Company.DoesNotExist:
            return self.company_symbol

    def __str__(self):
        return f"{self.company_symbol} - {self.date}"

    class Meta:
        db_table = "ohlc_data"
        unique_together = ("company_symbol", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["company_symbol", "date"]),
            models.Index(fields=["date"]),
        ]
