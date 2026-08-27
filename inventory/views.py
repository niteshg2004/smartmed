from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import Inventory
from pharmacies.models import Pharmacy
from medicines.models import Medicine
from .forms import InventoryUpdateForm
from .services import update_inventory
from .models import AvailabilityRequest

@login_required
def inventory_list(request):
    if request.user.role != 'pharmacy':
        raise PermissionDenied
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user)
    except Pharmacy.DoesNotExist:
        messages.error(request, 'You need to create a pharmacy first.')
        return redirect('pharmacies:create')
        
    inventory = Inventory.objects.filter(pharmacy=pharmacy)
    return render(request, 'inventory/list.html', {'inventory': inventory, 'pharmacy': pharmacy})

@login_required
def inventory_update(request, medicine_id):
    if request.user.role != 'pharmacy':
        raise PermissionDenied
    
    pharmacy = get_object_or_404(Pharmacy, owner=request.user)
    medicine = get_object_or_404(Medicine, id=medicine_id)
    
    try:
        inventory = Inventory.objects.get(pharmacy=pharmacy, medicine=medicine)
        initial_data = {
            'quantity': inventory.quantity,
            'price': inventory.price,
            'batch_number': inventory.batch_number,
            'expiry_date': inventory.expiry_date
        }
    except Inventory.DoesNotExist:
        initial_data = {}

    if request.method == 'POST':
        form = InventoryUpdateForm(request.POST)
        if form.is_valid():
            update_inventory(
                pharmacy=pharmacy,
                medicine=medicine,
                quantity=form.cleaned_data['quantity'],
                price=form.cleaned_data.get('price'),
                batch_number=form.cleaned_data.get('batch_number'),
                expiry_date=form.cleaned_data.get('expiry_date')
            )
            messages.success(request, 'Inventory updated successfully.')
            return redirect('inventory:list')
    else:
        form = InventoryUpdateForm(initial=initial_data)
        
    return render(request, 'inventory/update.html', {'form': form, 'medicine': medicine})

@login_required
def inventory_add(request):
    if request.user.role != 'pharmacy':
        raise PermissionDenied
        
    pharmacy = get_object_or_404(Pharmacy, owner=request.user)
    
    if request.method == 'POST':
        medicine_id = request.POST.get('medicine_id')
        return redirect('inventory:update', medicine_id=medicine_id)
        
    medicines = Medicine.objects.exclude(inventory__pharmacy=pharmacy)
    return render(request, 'inventory/add.html', {'medicines': medicines})


@login_required
def availability_requests_my(request):
    if request.user.role != "patient":
        raise PermissionDenied
    requests_qs = (
        AvailabilityRequest.objects.filter(user=request.user)
        .select_related("pharmacy", "medicine")
        .order_by("-created_at")[:200]
    )
    return render(request, "inventory/availability_requests_my.html", {"requests": requests_qs})


@login_required
def availability_request_new(request):
    if request.user.role != "patient":
        raise PermissionDenied

    prefill_medicine_id = request.GET.get("medicine_id")
    prefill_pharmacy_id = request.GET.get("pharmacy_id")

    if request.method == "POST":
        medicine_id = request.POST.get("medicine_id")
        pharmacy_id = request.POST.get("pharmacy_id")
        if not medicine_id or not pharmacy_id:
            messages.error(request, "Please select both a medicine and a pharmacy.")
            return redirect("inventory:request-new")

        medicine = get_object_or_404(Medicine, pk=medicine_id)
        pharmacy = get_object_or_404(Pharmacy, pk=pharmacy_id)
        AvailabilityRequest.objects.create(user=request.user, medicine=medicine, pharmacy=pharmacy)
        messages.success(request, "Availability request sent to the pharmacy.")
        return redirect("inventory:requests-my")

    medicines = Medicine.objects.all().order_by("brand_name")[:500]
    pharmacies = Pharmacy.objects.filter(verification_status="verified").order_by("name")[:500]
    return render(
        request,
        "inventory/availability_request_new.html",
        {
            "medicines": medicines,
            "pharmacies": pharmacies,
            "prefill_medicine_id": int(prefill_medicine_id) if prefill_medicine_id and prefill_medicine_id.isdigit() else None,
            "prefill_pharmacy_id": int(prefill_pharmacy_id) if prefill_pharmacy_id and prefill_pharmacy_id.isdigit() else None,
        },
    )


@login_required
def availability_requests_inbox(request):
    if request.user.role not in ("pharmacy", "admin"):
        raise PermissionDenied

    if request.user.role == "admin":
        inbox = (
            AvailabilityRequest.objects.select_related("pharmacy", "medicine", "user")
            .order_by("-created_at")[:300]
        )
        pharmacy = None
    else:
        pharmacy = get_object_or_404(Pharmacy, owner=request.user)
        inbox = (
            AvailabilityRequest.objects.filter(pharmacy=pharmacy)
            .select_related("medicine", "user")
            .order_by("-created_at")[:300]
        )

    status_choices = [
        (AvailabilityRequest.Status.AVAILABLE, "Available"),
        (AvailabilityRequest.Status.LOW_STOCK, "Low Stock"),
        (AvailabilityRequest.Status.OUT_OF_STOCK, "Out of Stock"),
        (AvailabilityRequest.Status.DENIED, "Denied"),
        (AvailabilityRequest.Status.CONFIRMED, "Confirmed (legacy)"),
    ]
    return render(
        request,
        "inventory/availability_requests_inbox.html",
        {"requests": inbox, "pharmacy": pharmacy, "status_choices": status_choices},
    )


@login_required
def availability_request_respond(request, pk: int):
    if request.method != "POST":
        raise PermissionDenied
    if request.user.role not in ("pharmacy", "admin"):
        raise PermissionDenied

    availability_request = get_object_or_404(
        AvailabilityRequest.objects.select_related("pharmacy"),
        pk=pk,
    )
    if request.user.role == "pharmacy":
        pharmacy = get_object_or_404(Pharmacy, owner=request.user)
        if availability_request.pharmacy_id != pharmacy.id:
            raise PermissionDenied

    status_value = (request.POST.get("status") or "").strip()
    response_text = (request.POST.get("response") or "").strip()
    allowed_statuses = {choice[0] for choice in AvailabilityRequest.Status.choices}
    if status_value not in allowed_statuses:
        messages.error(request, "Invalid status value.")
        return redirect("inventory:requests-inbox")

    availability_request.status = status_value
    availability_request.response = response_text
    availability_request.save(update_fields=["status", "response", "updated_at"])
    messages.success(request, "Availability response saved.")
    return redirect("inventory:requests-inbox")
