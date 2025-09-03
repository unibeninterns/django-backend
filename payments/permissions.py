from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Permission to check if the user is a student (authenticated and not staff)
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and not request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to check if the user owns the object or is an admin
    Works with Payment and Enrollment models
    """
    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.is_staff:
            return True
        
        # Check if the object has a user attribute (Payment, Enrollment)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For other objects, allow only admin access
        return False


class IsPackageOwnerOrAdmin(permissions.BasePermission):
    """
    Specific permission for package-related actions
    Checks if user owns the package enrollment or is admin
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        # For Enrollment objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For Payment objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class ReadOnly(permissions.BasePermission):
    """
    Permission to allow only read operations (GET, HEAD, OPTIONS)
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow admins full access, others read-only
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user and request.user.is_staff