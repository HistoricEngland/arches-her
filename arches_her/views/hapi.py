import json
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from ..services import (
    validate as validate_service,
    generate as generate_service,
    authenticate as authenticate_service,
    batch_create as batch_create_service,
    batch_submit as batch_submit_service,
)
from arches.app.models.system_settings import settings
import requests
from arches_her.tasks import hapi_upload
from arches_her.management.commands.hapi import Command


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


@method_decorator(superuser_required, name='dispatch')
class AuthenticateView(View):
    def get(self, request):
        try:
            body = json.loads(request.body)
            username = body.get("username")
            password = body.get("password")
        except:
            return HttpResponse(status=401)

        token = authenticate_service(username, password)
        if not token:
            return HttpResponse(status=401)
        return HttpResponse(token, status=200)


@method_decorator(superuser_required, name='dispatch')
class BatchCreateView(View):
    def get(self, request):
        try:
            body = json.loads(request.body)
            token = body.get("token")
            username = body.get("username")
            password = body.get("password")
            counts = {
                "total_count": body.get("total_count", 0),
                "published_count": body.get("published_count", 0),
                "submitted_count": body.get("submitted_count", 0),
            }
        except:
            return HttpResponse(status=400)

        batch_number = batch_create_service(
            bearer_token=token,
            username=username,
            password=password,
            counts=counts
        )
        if not batch_number:
            return HttpResponse(status=401)
        return HttpResponse(batch_number, status=200)


@method_decorator(superuser_required, name='dispatch')
class BatchSubmitView(View):
    def get(self, request):
        try:
            request_data = json.loads(request.body)
            bearer_token = request_data.get("bearer_token", None)
            batch_id = request_data.get("batch_id", None)
            records = request_data.get("records", None)
        except:
            return HttpResponse(status=400)

        status_code, reason, text = batch_submit_service(
            bearer_token,
            batch_id, records
        )

        text = json.loads(text)
        return JsonResponse({"reason": reason, **text}, status=status_code)


@method_decorator(superuser_required, name='dispatch')
class BatchSubmitCronView(View):
    run_type = None
    seed = None

    def get(self, request, run_type=None, seed=None):
        try:
            self.run_type = self.kwargs.get('run_type',)
            self.seed = self.kwargs.get('run_type', False)
            hapi_upload(run_type=run_type, seed=seed)
            return HttpResponse(status=200)
        except:
            return HttpResponse(status=500)
