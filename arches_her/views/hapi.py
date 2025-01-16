import json
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
    def get(self, request, resource_uuid=None):
        if not resource_uuid:
            try:
                body = json.loads(request.body)
                resource_uuids = body.get("resource_uuids", [])
                if not resource_uuids:
                    return JsonResponse({"status": "failure", "message": "No resource_uuids provided"}, status=400)
                resource_uuid = ",".join(resource_uuids)
            except json.JSONDecodeError:
                return JsonResponse({"status": "failure", "message": "Invalid JSON in request body"}, status=400)

        result, status_code = validate_service(resource_uuid=resource_uuid)
        if result is True:
            return JsonResponse({"status": "success", "message": "Validation passed"}, status=status_code)

        error_response = {"status": "failure", "message": "Validation failed"}
        if isinstance(result, dict):
            error_response.update(result)
        else:
            error_response["reason"] = result

        return JsonResponse(error_response, status=status_code)


@method_decorator(superuser_required, name='dispatch')
class GenerateResourceView(View):
    def get(self, request, resource_uuid=None):
        if not resource_uuid:
            try:
                body = json.loads(request.body)
                resource_uuids = body.get("resource_uuids", [])
                if not resource_uuids:
                    return JsonResponse({"status": "failure", "message": "No resource_uuids provided"}, status=400)
                resource_uuid = ",".join(resource_uuids)
            except json.JSONDecodeError:
                return JsonResponse({"status": "failure", "message": "Invalid JSON in request body"}, status=400)

        result = generate_service(resource_uuid)
        return JsonResponse(result)
