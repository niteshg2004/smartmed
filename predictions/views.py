import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.models import User
from inventory.models import Inventory, InventoryHistory
from ml.predict import predict_stock


def _build_daily_history(pharmacy_id, medicine_id, days=30):
    rows = list(
        InventoryHistory.objects.filter(
            pharmacy_id=pharmacy_id,
            medicine_id=medicine_id,
            timestamp__gte=timezone.now() - timedelta(days=days),
        )
        .values("timestamp", "quantity")
        .order_by("timestamp")
    )
    if not rows:
        return []

    daily = {}
    for row in rows:
        day = timezone.localtime(row["timestamp"]).date().isoformat()
        daily[day] = row["quantity"]

    labels = sorted(daily.keys())
    quantities = [daily[label] for label in labels]
    demands = [0]
    for idx in range(1, len(quantities)):
        demands.append(max(0, quantities[idx - 1] - quantities[idx]))

    return [
        {"label": label, "quantity": qty, "demand": demand}
        for label, qty, demand in zip(labels, quantities, demands)
    ]


def _inventory_queryset_for_user(user):
    qs = Inventory.objects.select_related("pharmacy", "medicine").order_by(
        "pharmacy__name",
        "medicine__brand_name",
    )
    if user.role == User.Role.PHARMACY:
        qs = qs.filter(pharmacy__owner=user)
    return qs


@login_required
def analytics_view(request):
    inventory_qs = _inventory_queryset_for_user(request.user)
    selected_inventory = None
    prediction = None
    history_rows = []

    pharmacy_id = request.GET.get("pharmacy_id")
    medicine_id = request.GET.get("medicine_id")
    if pharmacy_id and medicine_id:
        selected_inventory = get_object_or_404(
            inventory_qs,
            pharmacy_id=pharmacy_id,
            medicine_id=medicine_id,
        )
        history_rows = _build_daily_history(selected_inventory.pharmacy_id, selected_inventory.medicine_id)
        try:
            prediction = predict_stock(
                pharmacy_id=selected_inventory.pharmacy_id,
                medicine_id=selected_inventory.medicine_id,
            )
        except FileNotFoundError:
            messages.warning(
                request,
                "The stock prediction model has not been trained yet. Run `python manage.py train_stock_model` to enable analytics predictions.",
            )

    avg_daily_demand = 0.0
    if prediction:
        avg_daily_demand = float(prediction.avg_daily_demand_7d)
    elif history_rows:
        demand_points = [row["demand"] for row in history_rows[1:]]  # first day has no delta
        if demand_points:
            tail = demand_points[-7:]
            avg_daily_demand = round(sum(tail) / max(1, len(tail)), 2)

    stockout_probability_pct = None
    predicted_stockout_in_days = None
    if prediction:
        stockout_probability_pct = round(float(prediction.stockout_probability) * 100.0, 1)
        if prediction.predicted_stockout_date:
            try:
                stockout_date = date.fromisoformat(prediction.predicted_stockout_date)
                predicted_stockout_in_days = max(0, (stockout_date - timezone.now().date()).days)
            except ValueError:
                predicted_stockout_in_days = None

    # Chart payloads: historical series + optional predicted "next-day" points.
    history_labels = [row["label"] for row in history_rows]
    history_stock = [row["quantity"] for row in history_rows]
    history_demand = [row["demand"] for row in history_rows]

    chart_labels = list(history_labels)
    stock_history_series = list(history_stock)
    stock_pred_series = []
    demand_history_series = list(history_demand)
    demand_pred_series = []
    demand_bar_series = list(history_demand)

    if prediction:
        if history_labels:
            next_day = date.fromisoformat(history_labels[-1]) + timedelta(days=1)
        else:
            today = timezone.localtime(timezone.now()).date()
            next_day = today + timedelta(days=1)

        if history_labels:
            chart_labels = list(history_labels) + [next_day.isoformat()]
            stock_history_series = list(history_stock) + [None]
            demand_history_series = list(history_demand) + [None]

            stock_pred_series = [None] * max(0, len(history_stock) - 1) + [
                history_stock[-1],
                prediction.predicted_remaining_stock,
            ]

            demand_pred_series = [None] * len(history_demand) + [prediction.predicted_demand]
            demand_bar_series = list(history_demand) + [prediction.predicted_demand]
        else:
            current_stock = float(selected_inventory.quantity) if selected_inventory else 0.0
            chart_labels = [today.isoformat(), next_day.isoformat()]
            stock_history_series = [current_stock, None]
            stock_pred_series = [current_stock, prediction.predicted_remaining_stock]
            demand_history_series = [0.0, None]
            demand_pred_series = [None, prediction.predicted_demand]
            demand_bar_series = [0.0, prediction.predicted_demand]
    else:
        stock_pred_series = []
        demand_pred_series = []

    inventory_options = [
        {
            "pharmacy_id": item.pharmacy_id,
            "medicine_id": item.medicine_id,
            "label": f"{item.pharmacy.name} • {item.medicine.brand_name} {item.medicine.strength}",
        }
        for item in inventory_qs[:500]
    ]

    context = {
        "inventory_options": inventory_options,
        "selected_inventory": selected_inventory,
        "prediction": prediction,
        "avg_daily_demand": avg_daily_demand,
        "stockout_probability_pct": stockout_probability_pct,
        "predicted_stockout_in_days": predicted_stockout_in_days,
        "chart_labels_json": json.dumps(chart_labels),
        "chart_stock_history_json": json.dumps(stock_history_series),
        "chart_stock_pred_json": json.dumps(stock_pred_series),
        "chart_demand_history_json": json.dumps(demand_history_series),
        "chart_demand_pred_json": json.dumps(demand_pred_series),
        "chart_demand_bar_json": json.dumps(demand_bar_series),
        "is_demo_data": bool(
            selected_inventory
            and (
                selected_inventory.is_demo_data
                or selected_inventory.pharmacy.is_demo_data
                or selected_inventory.medicine.is_demo_data
            )
        ),
    }
    return render(request, "predictions/analytics.html", context)
