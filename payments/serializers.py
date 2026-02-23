from rest_framework import serializers
from users.serializers import UserSerializer
from module.serializers import CourseSerializer
from .models import Payment, Enrollment, Package, AddOn, Payout

class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    add_on_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'package', 'package_name',
            'add_ons', 'add_on_names',
            'total_amount', 'payment_option', 'transaction_id',
            'flutterwave_ref', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'transaction_id', 'flutterwave_ref',
            'status', 'created_at', 'updated_at', 'total_amount'
        ]

    def get_add_on_names(self, obj):
        """Return list of add-on names"""
        return [add_on.name for add_on in obj.add_ons.all()]

class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'

class AddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOn
        fields = '__all__'

class PaymentDetailSerializer(PaymentSerializer):
    package_description = serializers.CharField(source='package.description', read_only=True)
    package_duration = serializers.IntegerField(source='package.duration_weeks', read_only=True)
    package_features = serializers.JSONField(source='package.features', read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + [
            'package_description', 'package_duration', 'package_features'
        ]

class EnrollmentSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source='package.name', read_only=True)
    package_description = serializers.CharField(source='package.description', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payment_status = serializers.CharField(source='payment.status', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.total_amount', read_only=True, max_digits=10,
                                              decimal_places=2)
    add_on_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'package', 'package_name', 'package_description',
            'payment', 'payment_status', 'payment_amount',
            'add_ons', 'add_on_names',
            'enrolled_at', 'status', 'expires_at'
        ]
        read_only_fields = ['user', 'enrolled_at', 'expires_at']

    def get_add_on_names(self, obj):
        """Return list of add-on names"""
        return [add_on.name for add_on in obj.add_ons.all()]

class EnrollmentDetailSerializer(EnrollmentSerializer):
    package_duration = serializers.IntegerField(source='package.duration_weeks', read_only=True)
    package_features = serializers.JSONField(source='package.features', read_only=True)
    package_type = serializers.CharField(source='package.package_type', read_only=True)

    class Meta(EnrollmentSerializer.Meta):
        fields = EnrollmentSerializer.Meta.fields + [
            'package_duration', 'package_features', 'package_type'
        ]

class PackageSelectionSerializer(serializers.Serializer):
    package_id = serializers.IntegerField()
    add_on_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[]
    )

    def validate_package_id(self, value):
        try:
            package = Package.objects.get(id=value, is_active=True)
            return value
        except Package.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")

    def validate_add_on_ids(self, value):
        valid_add_ons = []
        for add_on_id in value:
            try:
                add_on = AddOn.objects.get(id=add_on_id, is_active=True)
                valid_add_ons.append(add_on_id)
            except AddOn.DoesNotExist:
                raise serializers.ValidationError(f"Add-on {add_on_id} not found or inactive")
        return valid_add_ons

class PaymentVerificationSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)

class FlutterwaveCallbackSerializer(serializers.Serializer):
    tx_ref = serializers.CharField()
    transaction_id = serializers.CharField(required=False)
    status = serializers.CharField()

class EnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['package', 'status']
        read_only_fields = ['user', 'enrolled_at']

class PaymentStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['status']

    def validate_status(self, value):
        valid_statuses = dict(Payment.STATUS_CHOICES)
        if value not in valid_statuses:
            raise serializers.ValidationError("Invalid status")
        return value


class EnrollmentStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['status']

    def validate_status(self, value):
        valid_statuses = dict(Enrollment.STATUS_CHOICES)
        if value not in valid_statuses:
            raise serializers.ValidationError("Invalid status")
        return value


class PayoutSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(
        source='recipient.email', read_only=True
    )

    class Meta:
        model = Payout
        fields = [
            'id',
            'recipient',
            'recipient_email',
            'amount',
            'payment_method',
            'status',
            'reference',
            'created_at',
            'completed_at',
            'notes',
            'account_number',
            'bank_code'
        ]
        read_only_fields = ['created_at', 'completed_at']


class AdminPayoutSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(
        source='recipient.email',
        read_only=True
    )

    class Meta:
        model = Payout
        fields = [
            'id',
            'reference',
            'recipient',
            'recipient_email',
            'amount',
            'payment_method',
            'status',
            'created_at',
            'completed_at',
            'notes',
        ]
        read_only_fields = [
            'status',
            'created_at',
            'completed_at'
        ]

