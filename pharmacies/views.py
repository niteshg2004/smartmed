from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import Pharmacy
from .forms import PharmacyForm
from inventory.models import Inventory
from medicines.models import Medicine

@login_required
def pharmacy_dashboard(request):
    if request.user.role != 'pharmacy':
        raise PermissionDenied
    try:
        pharmacy = Pharmacy.objects.get(owner=request.user)
    except Pharmacy.DoesNotExist:
        return redirect('pharmacies:create')
        
    inventory = Inventory.objects.filter(pharmacy=pharmacy)
    low_stock = inventory.filter(quantity__lt=10)
    
    context = {
        'pharmacy': pharmacy,
        'inventory_count': inventory.count(),
        'low_stock': low_stock,
    }
    return render(request, 'pharmacies/dashboard.html', context)

@login_required
def pharmacy_create(request):
    if request.user.role != 'pharmacy':
        raise PermissionDenied
        
    if Pharmacy.objects.filter(owner=request.user).exists():
        return redirect('pharmacies:dashboard')
        
    if request.method == 'POST':
        form = PharmacyForm(request.POST)
        if form.is_valid():
            pharmacy = form.save(commit=False)
            pharmacy.owner = request.user
            pharmacy.save()
            messages.success(request, 'Pharmacy created successfully.')
            return redirect('pharmacies:dashboard')
    else:
        form = PharmacyForm()
        
    return render(request, 'pharmacies/form.html', {'form': form, 'title': 'Create Pharmacy'})

@login_required
def pharmacy_edit(request, pk):
    pharmacy = get_object_or_404(Pharmacy, pk=pk)
    if pharmacy.owner != request.user and request.user.role != 'admin':
        raise PermissionDenied
        
    if request.method == 'POST':
        form = PharmacyForm(request.POST, instance=pharmacy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pharmacy updated successfully.')
            return redirect('pharmacies:dashboard')
    else:
        form = PharmacyForm(instance=pharmacy)
        
    return render(request, 'pharmacies/form.html', {'form': form, 'title': 'Edit Pharmacy'})

def pharmacy_list(request):
    pharmacies = Pharmacy.objects.filter(verification_status='verified')
    return render(request, 'pharmacies/list.html', {'pharmacies': pharmacies})


def nearby_pharmacies(request, medicine_id: int):
    """
    Patient-facing page that shows a Leaflet (OpenStreetMap) map and a ranked
    list of nearby pharmacies for a selected medicine.
    The heavy lifting (distance + availability confidence) is computed by
    `/api/v1/pharmacies/nearby/`.
    """
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    # Pune default; user location is requested by the browser (Geolocation API).
    default_center = {"lat": 18.5204, "lng": 73.8567}
    return render(
        request,
        "pharmacies/nearby_medicine.html",
        {"medicine": medicine, "default_center": default_center},
    )


def pharmacy_public_detail(request, pk: int):
    """Public (patient) pharmacy profile page."""
    pharmacy = get_object_or_404(Pharmacy, pk=pk, verification_status=Pharmacy.VerificationStatus.VERIFIED)
    inventory = (
        Inventory.objects.filter(pharmacy=pharmacy)
        .select_related("medicine")
        .order_by("medicine__brand_name")
    )
    return render(
        request,
        "pharmacies/public_detail.html",
        {"pharmacy": pharmacy, "inventory": inventory},
    )
