from __future__ import annotations

from django import forms
from django.conf import settings


class PrescriptionUploadForm(forms.Form):
    file = forms.FileField(
        label="Prescription image",
        help_text="Upload a clear photo/scan (JPG or PNG). OCR results must be confirmed manually.",
    )

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if not uploaded:
            return uploaded

        max_bytes = int(settings.PRESCRIPTION_MAX_UPLOAD_MB) * 1024 * 1024
        if uploaded.size and uploaded.size > max_bytes:
            raise forms.ValidationError(
                f"File too large. Max allowed size is {settings.PRESCRIPTION_MAX_UPLOAD_MB}MB."
            )

        content_type = (getattr(uploaded, "content_type", "") or "").lower()
        allowed = set(getattr(settings, "PRESCRIPTION_ALLOWED_CONTENT_TYPES", []))
        if content_type and allowed and content_type not in allowed:
            raise forms.ValidationError("Unsupported file type. Please upload a JPG, JPEG, or PNG image.")

        # Secondary guard based on extension.
        filename = (uploaded.name or "").lower()
        if "." not in filename:
            raise forms.ValidationError("File must have a valid image extension: JPG, JPEG, or PNG.")

        ext = filename.rsplit(".", 1)[-1]
        if ext not in {"jpg", "jpeg", "png"}:
            raise forms.ValidationError("Unsupported file extension. Please upload a JPG, JPEG, or PNG image.")

        # Validate actual image content — never trust extension alone.
        try:
            from PIL import Image
        except Exception as exc:  # pragma: no cover
            raise forms.ValidationError("Image validation is not available right now.") from exc

        try:
            uploaded.seek(0)
            image = Image.open(uploaded)
            image.verify()
            detected_format = (image.format or "").upper()
        except Exception as exc:
            raise forms.ValidationError("Uploaded file is not a valid image or is corrupted.") from exc
        finally:
            uploaded.seek(0)

        if detected_format not in {"JPEG", "PNG"}:
            raise forms.ValidationError("Only JPEG and PNG prescription images are supported.")

        return uploaded
