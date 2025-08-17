from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from module.permissions import IsAdminUser, IsStudent, IsOwnerOrAdmin
from users.models import CustomUser
from payments.models import Payment
from payments.serializers import PaymentSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_permissions(self):
        """Apply permissions based on action."""
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin()]
        return [AllowAny()]

    def get_queryset(self):
        """Filter payment records based on user access."""
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return Payment.objects.filter(user=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Payment.objects.all()
        return Payment.objects.none()

    def get_serializer_context(self):
        """Add additional context to serializer if needed."""
        context = super().get_serializer_context()
        return context