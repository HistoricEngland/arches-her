import json
import logging
import traceback
from arches.app.models.system_settings import settings
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from arches_her.models import models
from arches_her.data_access.common import filtered_string
from arches_her.hapi.helper import email_error
from ..services import (
    validate as validate_service,
    generate as generate_service,
    authenticate as authenticate_service,
    batch_create as batch_create_service,
    batch_finalise as batch_finalise_service,
    batch_submit as batch_submit_service,
)
from arches_her.tasks import hapi_upload
from django.db import connection
from django.core.management import call_command
from django.core.cache import cache
from celery.result import AsyncResult
from arches_her.tasks import data_refresh_task


# Set up logger for this module
logger = logging.getLogger(__name__)


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
                resource_uuids = body.get("resource_uuids")
                resource_uuids = filtered_string(resource_uuids)
                if not resource_uuids:
                    return JsonResponse({"status": "failure", "message": "No resource_uuids provided"}, status=400)
                resource_uuid = ",".join(resource_uuids)
            except json.JSONDecodeError:
                return JsonResponse({"status": "failure", "message": "Invalid JSON in request body"}, status=400)

        result, status_code = validate_service(resource_uuid=resource_uuid)
        if status_code == 200:
            return JsonResponse({
                "status": "success",
                "message": "Validation passed"
            }, status=status_code)

        error_response = {
            "status": "failure",
            "message": "Validation failed"
        }

        if isinstance(result, dict):
            error_response.update(result)
        else:
            error_response["reason"] = result

        return JsonResponse(error_response, status=status_code)


@method_decorator(superuser_required, name='dispatch')
class GenerateResourceView(View):
    def get(self, request, resource_uuid=None):
        try:
            if not resource_uuid:
                try:
                    body = json.loads(request.body)
                    resource_uuids = body.get("resource_uuids", [])
                    resource_uuids = filtered_string(resource_uuids)
                    if not resource_uuids:
                        return JsonResponse({
                            "status": "failure",
                            "message": "No resource_uuids provided"
                        }, status=400)
                    resource_uuid = ",".join(resource_uuids)
                except json.JSONDecodeError:
                    return JsonResponse({
                        "status": "failure",
                        "message": "Invalid JSON in request body"
                    }, status=400)

            result = generate_service(resource_uuid)
            response_data = {
                "status": "success"
            }
            if isinstance(result, dict):
                response_data.update(result)
            else:
                response_data["data"] = result
            return JsonResponse(response_data, status=200)

        except Exception as e:
            tb_str = ''.join(traceback.format_exception(
                type(e), e, e.__traceback__))
            message = "Error in GenerateResourceView:"
            logger.error(f"{message} {tb_str}")
            email_error(
                body=message,
                error=tb_str
            )
            return JsonResponse({
                "status": "failure",
                "error": tb_str
            }, status=500)


@method_decorator(superuser_required, name='dispatch')
class AuthenticateView(View):
    def get(self, request):

        try:
            body = json.loads(request.body)
            username = body.get("username")
            password = body.get("password")
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "failure",
                "message": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "status": "failure",
                "message": str(e)
            }, status=400)

        token = authenticate_service(username, password)
        if not token:
            return JsonResponse({
                "status": "failure",
                "message": "Authentication failed"
            }, status=401)
        return JsonResponse({
            "status": "success",
            "token": token
        }, status=200)


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
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "failure",
                "message": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "status": "failure",
                "message": str(e)
            }, status=401)

        batch_number = batch_create_service(
            bearer_token=token,
            username=username,
            password=password,
            counts=counts
        )

        if not batch_number:
            return JsonResponse({
                "status": "failure",
                "message": "Failed to create batch"
            }, status=401)
        return JsonResponse({
            "status": "success",
            "batch_number": batch_number
        }, status=200)


@method_decorator(superuser_required, name='dispatch')
class BatchFinaliseView(View):
    def get(self, request):
        try:
            body = json.loads(request.body)
            token = body.get("token")
            username = body.get("username")
            password = body.get("password")
            batch_id = body.get("batch_id")
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "failure",
                "message": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "status": "failure",
                "message": str(e)
            }, status=400)

        status_code = batch_finalise_service(
            bearer_token=token, username=username, password=password, batch_id=batch_id
        )

        return JsonResponse({
            "status": "success" if status_code == 200 else "failure",
            "message": "Batch finalised successfully" if status_code == 200 else "Failed to finalise batch"
        }, status=status_code)


@method_decorator(superuser_required, name='dispatch')
class BatchSubmitView(View):
    def get(self, request):
        try:
            request_data = json.loads(request.body)
            bearer_token = request_data.get("bearer_token", None)
            username = request_data.get("username", None)
            password = request_data.get("password", None)
            batch_id = request_data.get("batch_id", None)
            records = request_data.get("records", None)
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "failure",
                "message": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "status": "failure",
                "message": str(e)
            }, status=400)

        status_code, reason, text = batch_submit_service(
            bearer_token=bearer_token,
            username=username,
            password=password,
            batch_id=batch_id,
            records=records
        )

        if text is None or text == '':
            text = {}
        else:
            try:
                text = json.loads(text)
            except json.JSONDecodeError:
                text = {"text": text}

        response_data = {
            "reason": reason, **text
        }

        return JsonResponse(response_data, status=status_code)


@method_decorator(superuser_required, name='dispatch')
class BatchSubmitCronView(View):
    run_type = None
    seed = None
    CACHE_KEY = "batch_submit_cron_task_id"

    def get(self, request, run_type=None, seed=None):
        try:
            task_id = cache.get(self.CACHE_KEY)

            if task_id:
                result = AsyncResult(task_id)
                if result.state in ("PENDING", "STARTED", "PROGRESS"):
                    return JsonResponse({
                        "status": "running",
                        "message": "Batch upload is already in progress. Please wait.",
                        "task_id": task_id
                    }, status=429)
                # If finished, allow new task and clear cache
                cache.delete(self.CACHE_KEY)

            # Start new task and store its ID
            # For debug purposes, you may want to call task = hapi_upload.apply(...)
            # which will run the task in a blocking manner which can be debugged
            task = hapi_upload.apply_async(kwargs={
                'run_type': run_type or models.HeritageApiLog.AUTOMATIC,
                'seed': seed or False
            })
            cache.set(self.CACHE_KEY, task.id)

            return JsonResponse({
                "status": "pending",
                "message": "Batch upload started. Please check status.",
                "task_id": task.id
            }, status=202)

        except Exception as e:
            tb_str = ''.join(traceback.format_exception(
                type(e), e, e.__traceback__))
            logger.error(f"Error in BatchSubmitCronView: {tb_str}")
            return JsonResponse({
                "status": "failure",
                "message": "An error occurred during batch upload",
                "error": tb_str
            }, status=500)


@method_decorator(superuser_required, name='dispatch')
class BatchSubmitCronStatusView(View):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        if result.state == 'PENDING':
            return JsonResponse({"status": "pending", "message": "Please wait..."}, status=202)
        elif result.state == 'PROGRESS':
            return JsonResponse({
                "status": "progress",
                "message": result.info.get('message', 'Task is in progress.')
            }, status=202)
        elif result.state == 'SUCCESS':
            return JsonResponse(result.result)
        elif result.state == 'FAILURE':
            return JsonResponse({
                "status": "failure",
                "message": "An error occurred during data refresh",
                "error": str(result.result)
            }, status=500)
        else:
            return JsonResponse({"status": result.state.lower(), "message": "Task is processing."})


@method_decorator(superuser_required, name='dispatch')
class DataRefreshView(View):
    CACHE_KEY = "data_refresh_task_id"

    def get(self, request):
        task_id = cache.get(self.CACHE_KEY)
        if task_id:
            result = AsyncResult(task_id)
            if result.state in ("PENDING", "STARTED", "PROGRESS"):
                return JsonResponse({
                    "status": "running",
                    "message": "Data refresh is already in progress. Please wait.",
                    "task_id": task_id
                }, status=429)
            # If finished, allow new task and clear cache
            cache.delete(self.CACHE_KEY)

        # Start new task and store its ID
        task = data_refresh_task.delay()
        cache.set(self.CACHE_KEY, task.id)
        return JsonResponse({
            "status": "pending",
            "message": "Data refresh started. Please check status.",
            "task_id": task.id
        }, status=202)


@method_decorator(superuser_required, name='dispatch')
class DataRefreshStatusView(View):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        if result.state == 'PENDING':
            return JsonResponse({"status": "pending", "message": "Please wait..."}, status=202)
        elif result.state == 'PROGRESS':
            return JsonResponse({
                "status": "progress",
                "message": result.info.get('message', 'Task is in progress.')
            }, status=202)
        elif result.state == 'SUCCESS':
            return JsonResponse(result.result)
        elif result.state == 'FAILURE':
            return JsonResponse({
                "status": "failure",
                "message": "An error occurred during data refresh",
                "error": str(result.result)
            }, status=500)
        else:
            return JsonResponse({"status": result.state.lower(), "message": "Task is processing."})


@method_decorator(superuser_required, name='dispatch')
class DataRemoveView(View):
    def get(self, request):
        try:
            call_command("apply_hapi_database_migration")
            return JsonResponse({
                "status": "success",
                "message": "H.API data removed. Schema deleted and recreated."
            }, status=200)
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(
                type(e), e, e.__traceback__))
            logger.error(f"Error in DataRemoveView: {tb_str}")
            return JsonResponse({
                "status": "failure",
                "message": "An error occurred during data removal",
                "error": tb_str
            }, status=500)


@method_decorator(superuser_required, name='dispatch')
class BatchSubmitCronTerminateView(View):
    CACHE_KEY = "batch_submit_cron_task_id"

    def get(self, request):
        task_id = cache.get(self.CACHE_KEY)
        if not task_id:
            return JsonResponse({
                "status": "not_running",
                "message": "No batch upload task is currently running."
            }, status=404)

        result = AsyncResult(task_id)
        if result.state in ("PENDING", "STARTED", "PROGRESS"):
            result.revoke(terminate=True, signal="SIGTERM")
            cache.delete(self.CACHE_KEY)
            return JsonResponse({
                "status": "terminated",
                "message": f"Batch upload task {task_id} has been terminated."
            }, status=200)
        else:
            cache.delete(self.CACHE_KEY)
            return JsonResponse({
                "status": "not_running",
                "message": "No batch upload task is currently running."
            }, status=404)
