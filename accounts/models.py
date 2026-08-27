from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager: email is the unique login identifier (no username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.PATIENT)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("name", extra_fields.get("name", "Administrator"))

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Core account model shared by all three roles (patient, pharmacy owner,
    admin/pharmacist). Role-specific data lives in related models
    (e.g. pharmacies.Pharmacy.owner -> User) rather than on this model,
    to keep it minimal per the data-minimization requirement.
    """

    class Role(models.TextChoices):
        PATIENT = "patient", "Patient"
        PHARMACY = "pharmacy", "Pharmacy"
        ADMIN = "admin", "Admin / Pharmacist"

    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["role"])]
        permissions = [
            ("can_verify_alternatives", "Can approve/reject alternative medicine candidates"),
            ("can_manage_medicines", "Can create/edit the medicine master database"),
            ("can_manage_users", "Can manage user and pharmacy accounts"),
            ("can_import_data", "Can bulk-import inventory/medicine CSV data"),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}> [{self.role}]"

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_pharmacy_role(self):
        return self.role == self.Role.PHARMACY

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser
