from rest_framework import serializers
from payments.models import Payment
from users.serializers import UserSerializer
from module.serializers import CourseSerializer

class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    class Meta:
        model = Payment
        fields = ['id', 'user', 'course', 'status', 'amount', 'created_at', 'updated_at']