from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivatePrescriptionStorage(FileSystemStorage):
    """
    Stores prescription uploads outside MEDIA_ROOT so they are never served via
    Django's DEBUG static/media handler (and are not publicly addressable).

    Access must be mediated through authenticated, owner-checked views that
    stream the file (see prescriptions/views.py).
    """

    def __init__(self, location: str | Path | None = None):
        if location is None:
            location = Path(settings.BASE_DIR) / "private_uploads"
        super().__init__(location=str(location), base_url=None)


private_prescription_storage = PrivatePrescriptionStorage()

