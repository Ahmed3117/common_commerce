from rest_framework.permissions import BasePermission


class IsAdminOrHasEndpointPermission(BasePermission):
    """
    Custom permission class that allows access if:
    1. User is a superuser (full access)
    2. User is staff AND has a matching endpoint permission
    """
    
    def has_permission(self, request, _view):
        del _view
        # Allow access if user is not authenticated (handled by authentication classes)
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Non-staff users are denied
        if not request.user.is_staff:
            return False
        
        return self._check_endpoint_permission(request)
    
    def _check_endpoint_permission(self, request):
        """Check if the staff user has permission for this specific endpoint"""
        try:
            from .models import UserPermission

            user_permission = UserPermission.objects.get(user=request.user)
            allowed_endpoints = user_permission.get_allowed_endpoints()
            current_url = request.path
            current_method = request.method

            for endpoint in allowed_endpoints:
                if self._url_matches(endpoint.url, current_url) and endpoint.method == current_method:
                    return True

            return False

        except ImportError:
            return False
        except UserPermission.DoesNotExist:
            return False
        except Exception:
            return False
    
    def _url_matches(self, pattern_url, request_url):
        """
        Check if the request URL matches the pattern URL.
        This supports both exact matches and basic wildcard patterns.
        """
        normalized_pattern = self._normalize_url(pattern_url)
        normalized_request = self._normalize_url(request_url)

        if normalized_pattern == normalized_request:
            return True

        if normalized_pattern.endswith('*'):
            pattern_base = normalized_pattern[:-1]
            return normalized_request.startswith(pattern_base)

        if '{' in normalized_pattern and '}' in normalized_pattern:
            return self._match_parameterized_url(normalized_pattern, normalized_request)

        return False

    def _normalize_url(self, url):
        if url == '/':
            return url
        return url.rstrip('/')
    
    def _match_parameterized_url(self, pattern_url, request_url):
        """
        Match URLs with parameters like /api/products/{id}/
        """
        pattern_parts = pattern_url.strip('/').split('/')
        request_parts = request_url.strip('/').split('/')

        if len(pattern_parts) != len(request_parts):
            return False

        for pattern_part, request_part in zip(pattern_parts, request_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue
            if pattern_part != request_part:
                return False

        return True


class IsStaffWithEndpointPermission(IsAdminOrHasEndpointPermission):
    """
    Alias for clarity where views explicitly want "staff with endpoint permission".
    This now uses the same explicit-permission behavior as IsAdminOrHasEndpointPermission.
    """
    pass


# Convenience function to easily apply permissions to views
def require_endpoint_permission(view_func):
    """
    Decorator to easily apply endpoint permissions to function-based views
    Usage:
    
    @api_view(['GET'])
    @require_endpoint_permission
    def my_view(request):
        return Response({'message': 'Hello'})
    """
    from rest_framework.decorators import permission_classes
    
    @permission_classes([IsAdminOrHasEndpointPermission])
    def wrapper(*args, **kwargs):
        return view_func(*args, **kwargs)
    
    return wrapper
