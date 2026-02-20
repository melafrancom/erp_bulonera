# api/mixins.py
"""
Reusable ViewSet mixins for common API patterns.

AuditMixin       — Automatically sets created_by on create.
OwnerQuerysetMixin — Filters queryset by created_by for non-admin users.
"""


class AuditMixin:
    """
    Automatically injects `created_by=request.user` on create.

    Usage:
        class SaleViewSet(AuditMixin, ModelViewSet):
            ...
    """

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class OwnerQuerysetMixin:
    """
    Restricts queryset to objects owned by the current user,
    unless the user is superuser or has is_manager=True.

    Assumes the model has a `created_by` ForeignKey to User.

    Usage:
        class SaleViewSet(OwnerQuerysetMixin, ModelViewSet):
            queryset = Sale.objects.all()
            ...
    """

    owner_field = 'created_by'  # Override if the FK has a different name

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser or getattr(user, 'is_manager', False):
            return qs

        return qs.filter(**{self.owner_field: user})
