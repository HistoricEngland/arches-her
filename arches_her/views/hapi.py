from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from ..services import (
    validate as validate_service, 
    generate as generate_service
)


def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, "user") or not request.user.is_authenticated or not request.user.is_superuser:
            return HttpResponse(status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@method_decorator(superuser_required, name='dispatch')
class ValidateResourceView(View):
    def get(self, request, resource_uuid):
        data = generate_service(resource_uuid)
        result, response = validate_service(data["data"])
        if result is True:
            return JsonResponse({"status": "success", "message": "Validation passed"}, status=response)
        
        error_response = {"status": "failure", "message": "Validation failed"}
        if isinstance(result, dict):
            error_response.update(result)
        else:
            error_response["reason"] = result

        return JsonResponse(error_response, status=response)
    
@method_decorator(superuser_required, name='dispatch')
class GenerateResourceView(View):
    def get(self, request, resource_uuid):
        result = generate_service(resource_uuid)
        return JsonResponse(result)