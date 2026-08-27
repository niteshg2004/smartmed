"""
Shared DRF permission classes used across every app's API views.
Kept in accounts/ since role checks are all based on accounts.User.role.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsPatient(BasePermission):
    message = "This action is only available to patient accounts."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_patient)


class IsPharmacyRole(BasePermission):
    message = "This action is only available to pharmacy accounts."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_pharmacy_role)


class IsAdminRole(BasePermission):
    message = "This action requires admin/pharmacist privileges."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsOwnerPharmacyOrAdmin(BasePermission):
    """
    Object-level check for Pharmacy / Inventory objects: the pharmacy's own
    owner may modify it, admins may modify anything, everyone authenticated
    may read it. Prevents pharmacy A editing pharmacy B's data (IDOR).
    """

    message = "You do not have permission to modify this pharmacy's data."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_admin_role:
            return True

        pharmacy = getattr(obj, "pharmacy", obj)  # obj may itself be a Pharmacy
        owner_id = getattr(pharmacy, "owner_id", None)
        return owner_id == user.id


class IsOwnerOrAdmin(BasePermission):
    """Generic: object has a `user` FK; only that user or an admin may access it."""

    message = "You do not have permission to access this record."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_admin_role:
            return True
        return getattr(obj, "user_id", None) == user.id
