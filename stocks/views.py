from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Max, Min, Sum
from datetime import datetime, timedelta
from .models import Company, StockData
import json
from collections import defaultdict


def index(request):
    # Get unique company symbols from stock data
    company_symbols = (
        StockData.objects.values_list("company_symbol", flat=True)
        .distinct()
        .order_by("company_symbol")
    )

    # Get companies from the database, create if they don't exist
    companies = []
    for symbol in company_symbols:
        try:
            company = Company.objects.get(symbol=symbol)
            companies.append(company)
        except Company.DoesNotExist:
            # Create company if it doesn't exist
            company = Company.objects.create(name=symbol, symbol=symbol)
            companies.append(company)

    # Get date range for the date picker
    earliest_date = StockData.objects.order_by("date").first()
    latest_date = StockData.objects.order_by("-date").first()

    context = {
        "companies": companies,
        "earliest_date": (
            earliest_date.date
            if earliest_date
            else datetime.now().date() - timedelta(days=3650)
        ),
        "latest_date": latest_date.date if latest_date else datetime.now().date(),
    }
    return render(request, "stocks/index.html", context)


@csrf_exempt
def get_chart_data(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            company_id = data.get("company_id")  # This will be company ID from frontend
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            aggregation = data.get("aggregation", "daily")

            if not all([company_id, start_date, end_date]):
                return JsonResponse(
                    {"error": "Missing required parameters"}, status=400
                )

            # Get company by ID and then get its symbol
            try:
                company = Company.objects.get(id=company_id)
                company_symbol = company.symbol
                company_name = company.name
            except Company.DoesNotExist:
                return JsonResponse({"error": "Company not found"}, status=404)

            # Get stock data for the date range using company_symbol
            stock_data_queryset = StockData.objects.filter(
                company_symbol=company_symbol,
                date__gte=start_date,
                date__lte=end_date,
            ).order_by("date")

            if not stock_data_queryset.exists():
                return JsonResponse(
                    {"error": "No data found for the selected range"}, status=404
                )

            # Aggregate data based on the specified level
            if aggregation == "monthly":
                aggregated_data = aggregate_monthly(stock_data_queryset)
            elif aggregation == "weekly":
                aggregated_data = aggregate_weekly(stock_data_queryset)
            else:  # daily
                aggregated_data = list(stock_data_queryset)

            if not aggregated_data:
                return JsonResponse(
                    {"error": "No data available after aggregation"}, status=404
                )

            # Prepare data for candlestick chart
            chart_data = {
                "dates": [item.date.strftime("%Y-%m-%d") for item in aggregated_data],
                "opens": [float(item.open) for item in aggregated_data],
                "highs": [float(item.high) for item in aggregated_data],
                "lows": [float(item.low) for item in aggregated_data],
                "closes": [float(item.close) for item in aggregated_data],
                "volumes": [item.volume for item in aggregated_data],
            }

            return JsonResponse(
                {
                    "chart_data": chart_data,
                    "data_points": len(aggregated_data),
                    "company_name": company_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "aggregation": aggregation,
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            print(f"Error in get_chart_data: {str(e)}")  # Debug print
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def aggregate_monthly(queryset):
    """Group records by year-month and aggregate OHLC data"""
    monthly_groups = defaultdict(list)

    for record in queryset:
        month_key = (record.date.year, record.date.month)
        monthly_groups[month_key].append(record)

    monthly_data = []

    for (year, month), records in sorted(monthly_groups.items()):
        if records:
            records.sort(key=lambda x: x.date)
            first_record = records[0]
            last_record = records[-1]

            class MonthlyRecord:
                def __init__(self, date, open_price, high, low, close, volume):
                    self.date = date
                    self.open = open_price
                    self.high = high
                    self.low = low
                    self.close = close
                    self.volume = volume

            monthly_record = MonthlyRecord(
                date=first_record.date.replace(day=1),
                open_price=first_record.open,
                high=max(record.high for record in records),
                low=min(record.low for record in records),
                close=last_record.close,
                volume=sum(record.volume for record in records),
            )

            monthly_data.append(monthly_record)

    return monthly_data


def aggregate_weekly(queryset):
    """Group records by week and aggregate OHLC data"""
    weekly_groups = defaultdict(list)

    for record in queryset:
        days_since_monday = record.date.weekday()
        week_start = record.date - timedelta(days=days_since_monday)
        weekly_groups[week_start].append(record)

    weekly_data = []

    for week_start, records in sorted(weekly_groups.items()):
        if records:
            records.sort(key=lambda x: x.date)
            weekly_data.append(create_weekly_record(records, week_start))

    return weekly_data


def create_weekly_record(week_records, week_start):
    """Create a weekly aggregated record"""

    class WeeklyRecord:
        def __init__(self, date, open_price, high, low, close, volume):
            self.date = date
            self.open = open_price
            self.high = high
            self.low = low
            self.close = close
            self.volume = volume

    first_record = week_records[0]
    last_record = week_records[-1]

    return WeeklyRecord(
        date=week_start,
        open_price=first_record.open,
        high=max(record.high for record in week_records),
        low=min(record.low for record in week_records),
        close=last_record.close,
        volume=sum(record.volume for record in week_records),
    )
