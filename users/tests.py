from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient, APITestCase, APIRequestFactory
from rest_framework import status
from django.urls import reverse
from django.dispatch import receiver
from .signals import email_confirmed
from users.models import CustomUser
from users.serializers import UserSerializer, CustomRegisterSerializer, CustomLoginSerializer


# Mock signal receiver for testing
@receiver(email_confirmed)
def mock_activate_user_and_mark_verified(request, email_address, **kwargs):
    user = email_address.user
    user.is_verified = True
    user.save()

class UserModelTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            email="student@test.com",
            first_name="John",
            last_name="Doe",
            password="testpass123"
        )
        self.admin = CustomUser.objects.create_superuser(
            email="admin@test.com",
            first_name="Jane",
            last_name="Admin",
            password="adminpass123"
        )

    def test_user_creation(self):
        self.assertEqual(self.student.email, "student@test.com")
        self.assertEqual(self.student.role, "student")
        self.assertFalse(self.student.is_staff)
        self.assertTrue(self.student.is_active)
        self.assertFalse(self.student.is_verified)

    def test_superuser_creation(self):
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_verified)

    def test_username_auto_generation(self):
        user = CustomUser.objects.create_user(
            email="newuser@test.com",
            first_name="New",
            last_name="User",
            password="newpass123"
        )
        self.assertTrue(user.username.startswith("new_user_"))
        self.assertEqual(CustomUser.objects.filter(username=user.username).count(), 1)

    def test_unique_email(self):
        CustomUser.objects.create_user(
            email="duplicate@test.com",
            first_name="Original",
            last_name="User",
            password="duppass123"
        )
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                email="duplicate@test.com",
                first_name="Duplicate",
                last_name="User",
                password="duppass123"
            )

class UserSerializerTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            email="student@test.com",
            first_name="John",
            last_name="Doe",
            role="student",
            password="testpass123"
        )
        self.serializer = UserSerializer(instance=self.student)

    def test_serializer_fields(self):
        data = self.serializer.data
        self.assertEqual(set(data.keys()), {'id', 'first_name', 'last_name', 'email', 'is_verified', 'username', 'role', 'cohort'})
        self.assertEqual(data['email'], "student@test.com")
        self.assertEqual(data['role'], "student")

    def test_read_only_fields(self):
        serializer = UserSerializer(data={'role': 'admin'}, instance=self.student, partial=True)
        self.assertTrue(serializer.is_valid())

class CustomRegisterSerializerTests(TestCase):
    def setUp(self):
        self.valid_data = {
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        self.serializer = CustomRegisterSerializer(data=self.valid_data)

    def test_valid_registration(self):
        self.assertTrue(self.serializer.is_valid(raise_exception=False))
        user = self.serializer.save(request=self.client)
        self.assertEqual(user.email, 'newuser@test.com')
        self.assertTrue(user.username.startswith('new_user'))
        self.assertFalse(user.is_verified)

    def test_duplicate_email(self):
        CustomUser.objects.create_user(email="newuser@test.com", first_name="Existing", last_name="User", password="testpass123")
        serializer = CustomRegisterSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid(raise_exception=False))
        self.assertIn('email', serializer.errors)

    def test_password_mismatch(self):
        invalid_data = self.valid_data.copy()
        invalid_data['password2'] = 'wrongpass123'
        serializer = CustomRegisterSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

class CustomLoginSerializerTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            email="student@test.com",
            first_name="John",
            last_name="Doe",
            role="student",
            password="testpass123"
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/login/', {'email': 'student@test.com', 'password': 'testpass123'})
        self.valid_data = {'email': 'student@test.com', 'password': 'testpass123'}
        self.serializer = CustomLoginSerializer(data=self.valid_data, context={'request': self.request})

    def test_valid_login(self):
        self.assertTrue(self.serializer.is_valid(raise_exception=False))
        self.assertEqual(self.serializer.validated_data['user'], self.student)

    def test_invalid_password(self):
        invalid_data = {'email': 'student@test.com', 'password': 'wrongpass'}
        request = self.factory.post('/login/', invalid_data)
        serializer = CustomLoginSerializer(data=invalid_data, context={'request': request})
        self.assertFalse(serializer.is_valid(raise_exception=False))
        self.assertIn('non_field_errors', serializer.errors)

    def test_missing_fields(self):
        incomplete_data = {'email': 'student@test.com'}
        request = self.factory.post('/login/', incomplete_data)
        serializer = CustomLoginSerializer(data=incomplete_data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

class UserSignalTests(TransactionTestCase):
    def setUp(self):
        self.student = CustomUser.objects.create(
            email="student@test.com",
            first_name="John",
            last_name="Doe",
            role="student",
            password="testpass123"
        )

    def test_email_confirmed_signal(self):
        # Simulate email confirmation signal
        from django.dispatch import receiver
        from .signals import email_confirmed
        email_address = self.student.emailaddress_set.create(email="student@test.com", verified=False)
        email_address.verified = True
        email_address.save()
        email_confirmed.send(sender=None, request=None, email_address=email_address)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_verified)

class UserViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = CustomUser.objects.create(
            email="student@test.com",
            first_name="John",
            last_name="Doe",
            role="student",
            password="testpass123"
        )
        self.admin = CustomUser.objects.create(
            email="admin@test.com",
            first_name="Jane",
            last_name="Admin",
            role="admin",
            is_staff=True,
            is_superuser=True,
            password="adminpass123"
        )
        self.student.set_password("testpass123")
        self.admin.set_password("adminpass123")
        self.student.save()
        self.admin.save()

    def test_user_list_unauthenticated(self):
        url = reverse('user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_student(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)  # Should see all users due to IsAuthenticatedOrReadOnly

    def test_user_list_admin(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_user_detail_student(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('user-detail', args=[self.student.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], "student@test.com")

    def test_user_update_admin(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-detail', args=[self.student.id])
        data = {'first_name': 'UpdatedJohn'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'UpdatedJohn')

    def test_user_delete_admin(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-detail', args=[self.student.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomUser.objects.filter(id=self.student.id).exists())

    def test_user_delete_self(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('user-detail', args=[self.student.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_delete_student(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('user-detail', args=[self.admin.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
