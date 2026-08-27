from __future__ import annotations

from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import PrescriptionUploadForm
from .models import Prescription
from .services import (
    get_prescription_detected_rows,
    process_prescription,
    save_prescription_confirmations,
)


def _get_prescription_for_user_or_404(*, request, pk: int) -> Prescription:
    prescription = get_object_or_404(Prescription.objects.select_related("user"), pk=pk)
    if prescription.user_id != request.user.id and not request.user.is_admin_role:
        raise Http404("Prescription not found.")
    return prescription


@login_required
def prescription_list_view(request):
    qs = Prescription.objects.select_related("user")
    if not request.user.is_admin_role:
        qs = qs.filter(user=request.user)
    return render(request, "prescriptions/list.html", {"prescriptions": qs[:100]})


@login_required
@require_http_methods(["GET", "POST"])
def prescription_upload_view(request):
    if request.method == "POST":
        form = PrescriptionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            prescription = Prescription.objects.create(user=request.user, uploaded_file=uploaded)
            process_prescription(prescription)
            if prescription.processing_status == Prescription.ProcessingStatus.PROCESSED:
                messages.success(request, "Prescription uploaded and processed successfully.")
            else:
                messages.warning(
                    request,
                    prescription.processing_error
                    or "Prescription uploaded, but OCR could not be completed on this machine.",
                )
            return redirect("prescriptions:detail", pk=prescription.pk)
    else:
        form = PrescriptionUploadForm()
    return render(request, "prescriptions/upload.html", {"form": form})


@login_required
def prescription_file_view(request, pk: int):
    prescription = _get_prescription_for_user_or_404(request=request, pk=pk)
    if not prescription.uploaded_file:
        raise Http404("No file.")
    try:
        return FileResponse(
            prescription.uploaded_file.open("rb"),
            as_attachment=False,
            filename=prescription.uploaded_file.name.rsplit("/", 1)[-1],
        )
    except FileNotFoundError:
        raise Http404("File not found.")


@login_required
@require_http_methods(["GET", "POST"])
def prescription_detail_view(request, pk: int):
    prescription = _get_prescription_for_user_or_404(request=request, pk=pk)

    if request.method == "GET" and prescription.processing_status == Prescription.ProcessingStatus.PENDING:
        process_prescription(prescription)
        if prescription.processing_status == Prescription.ProcessingStatus.FAILED and prescription.processing_error:
            messages.warning(request, prescription.processing_error)

    if request.method == "POST":
        selections = {}
        for item in prescription.detected_medicines.all():
            selections[item.pk] = {
                "confirmed": bool(request.POST.get(f"confirm_{item.pk}")),
                "medicine_id": (request.POST.get(f"medicine_{item.pk}") or "").strip() or None,
            }
        save_prescription_confirmations(prescription, selections)
        messages.success(request, "Saved confirmation choices.")
        return redirect("prescriptions:detail", pk=prescription.pk)

    detected_rows = get_prescription_detected_rows(prescription)

    return render(
        request,
        "prescriptions/detail.html",
        {
            "prescription": prescription,
            "detected_rows": detected_rows,
            "file_ext": Path(prescription.uploaded_file.name).suffix.lower() if prescription.uploaded_file else "",
        },
    )
