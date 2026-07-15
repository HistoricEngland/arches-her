import json
import logging
import os
import tempfile
import threading
import traceback
from datetime import datetime
from math import ceil
from multiprocessing.connection import Client, Listener
from pathlib import Path

from django.utils import timezone
from django.db.models import Max, Min

from arches_her.data_access.common import get_counts, get_resources
from arches_her.models import models
from arches_her.services import (
    authenticate as authenticate_service,
    batch_create as batch_create_service,
    batch_finalise as batch_finalise_service,
    batch_submit as batch_submit_service,
    validate as validate_service,
)
from arches.app.models.system_settings import settings
from arches_her.data_access.common import serialize
from arches_her.hapi.helper import email_error

MAX_BATCH_SIZE = 5000
MAX_SUBMISSION_SIZE = 100

if os.name == "nt":
    IPC_FAMILY = "AF_PIPE"
else:
    IPC_FAMILY = "AF_UNIX"


def _build_ipc_address(name):
    if IPC_FAMILY == "AF_PIPE":
        return rf"\\.\pipe\keystone_hapi_{name}_runtime"
    return str(Path(tempfile.gettempdir()) / f"keystone_hapi_{name}_runtime.sock")


IPC_ADDRESS = _build_ipc_address("seed")
CRON_IPC_ADDRESS = _build_ipc_address("cron")


class RuntimeTerminationRequested(Exception):
    """Raised when a terminate command is issued while a runtime is running."""

    def __init__(self, message, termination_type="terminate"):
        super().__init__(message)
        self.termination_type = termination_type


class SeedRuntimeState:
    def __init__(
        self,
        task_id,
        clean_monument_sources,
        seed_limit_count,
        refresh_data=True,
        clear_data_on_complete=True,
        operation=None,
    ):
        self.task_id = task_id
        self.clean_monument_sources = clean_monument_sources
        self.seed_limit_count = seed_limit_count
        self.refresh_data = refresh_data
        self.clear_data_on_complete = clear_data_on_complete
        self.operation = operation
        self.state = "PENDING"
        self.info = {}
        self.result = None
        self.error = None
        self.terminate_requested = False
        self.termination_type = None
        self.lock = threading.Lock()

    def set_progress(self, meta):
        with self.lock:
            self.state = "PROGRESS"
            self.info = meta or {}

    def set_success(self, result):
        with self.lock:
            self.state = "SUCCESS"
            self.result = result

    def set_failure(self, error):
        with self.lock:
            self.state = "FAILURE"
            self.error = error

    def set_terminated(self, result):
        with self.lock:
            self.state = "TERMINATED"
            self.result = result

    def request_terminate(self, termination_type="terminate"):
        with self.lock:
            self.terminate_requested = True
            self.termination_type = termination_type

    def should_terminate(self):
        with self.lock:
            return self.terminate_requested

    def get_termination_type(self):
        with self.lock:
            return self.termination_type

    def get_status_payload(self):
        controls = {
            "operation": self.operation,
            "refresh_data": self.refresh_data,
            "clear_data_on_complete": self.clear_data_on_complete,
        }

        with self.lock:
            state = self.state
            info = dict(self.info)
            result = self.result
            error = self.error

        if state == "PENDING":
            payload = {"status": "pending",
                       "message": "Please wait...", "task_id": self.task_id}
            payload.update(controls)
            return payload

        if state == "PROGRESS":
            message = info.get("message", "Task is in progress.")
            progress_data = {
                "status": "progress",
                "message": message,
                "processed_resources": info.get("processed_resources", 0),
                "total_resources": info.get("total_resources", 0),
                "processed_records": info.get("processed_records", 0),
                "percentage": info.get("percentage", 0),
                "current_phase": info.get("current_phase", "processing"),
                "batch_id": info.get("batch_id"),
                "current_batch": info.get("current_batch"),
                "total_batches": info.get("total_batches"),
                "task_id": self.task_id,
            }

            if info.get("total_batches") and info.get("current_batch"):
                batch_percentage = round(
                    (info.get("current_batch", 0) /
                     info.get("total_batches", 1)) * 100, 1
                )
                progress_data["batch_percentage"] = batch_percentage
                progress_data["batch_progress"] = f"{info.get('current_batch', 0)}/{info.get('total_batches', 0)}"

            for field in (
                "valid_records",
                "invalid_records",
                "valid_records_including_monument_sources",
                "monument_source_only_records",
                "invalid_records_excluding_monument_sources",
                "total_passed_validation_records",
            ):
                if field in info:
                    progress_data[field] = info[field]

            progress_data.update(controls)
            return progress_data

        if state == "SUCCESS":
            if isinstance(result, dict):
                payload = dict(result)
                payload.update(controls)
                return payload
            payload = {"status": "success",
                       "result": result, "task_id": self.task_id}
            payload.update(controls)
            return payload

        if state == "TERMINATED":
            if isinstance(result, dict):
                payload = dict(result)
                payload.update(controls)
                return payload
            payload = {"status": "terminated",
                       "message": "Seed operation was terminated.", "task_id": self.task_id}
            payload.update(controls)
            return payload

        if state == "FAILURE":
            payload = {
                "status": "failure",
                "message": "An error occurred during task execution",
                "error": str(error),
                "task_id": self.task_id,
            }
            payload.update(controls)
            return payload

        payload = {"status": state.lower(), "message": "Unknown task state",
                   "task_id": self.task_id}
        payload.update(controls)
        return payload


def _ensure_socket_removed(ipc_address=IPC_ADDRESS):
    if IPC_FAMILY != "AF_UNIX":
        return
    try:
        socket_path = Path(ipc_address)
        if socket_path.exists():
            socket_path.unlink()
    except OSError:
        pass


def send_runtime_command(command, ipc_address=IPC_ADDRESS):
    if IPC_FAMILY == "AF_UNIX" and not Path(ipc_address).exists():
        return None
    try:
        conn = Client(ipc_address, family=IPC_FAMILY)
        conn.send({"command": command})
        response = conn.recv()
        conn.close()
        return response
    except (ConnectionRefusedError, FileNotFoundError, EOFError, OSError):
        return None


def send_cron_runtime_command(command):
    return send_runtime_command(command, ipc_address=CRON_IPC_ADDRESS)


def request_runtime_exit(ipc_address=IPC_ADDRESS):
    return send_runtime_command("EXIT", ipc_address=ipc_address)


def _check_for_termination(should_terminate, termination_type="terminate"):
    if should_terminate and should_terminate():
        resolved_termination_type = termination_type
        runtime_state = getattr(should_terminate, "__self__", None)
        if runtime_state is not None:
            tracker = getattr(runtime_state, "get_termination_type", None)
            if callable(tracker):
                tracked_type = tracker()
                if tracked_type in ("terminate", "shutdown"):
                    resolved_termination_type = tracked_type
        raise RuntimeTerminationRequested(
            "Runtime termination requested by user.",
            termination_type=resolved_termination_type,
        )


def _record_termination_status(log_id, termination_type):
    if not log_id:
        return
    from arches_her.tasks import update_log_messages
    status_value = "shutdown" if termination_type == "shutdown" else "terminated"
    update_log_messages(log_id, "completion_status", status_value)


def _build_hapi_log_parameters(from_date, operation):
    return {"from": from_date.isoformat(), "operation": operation}


def _classify_validation_response_records(validation_response):
    """Classify validation response records by error type, identifying monument-sources-only failures."""
    logger = logging.getLogger(__name__)
    MONUMENT_SOURCES_ERROR_PREFIX = "record.monumentSources"
    counts = {
        "invalid_records": 0,
        "non_monument_source_invalid_records": 0,
        "monument_sources_only_invalid_records": 0,
    }

    if not isinstance(validation_response, dict):
        return counts

    errors = validation_response.get("errors", [])
    if not errors:
        return counts

    def classify_record_errors(record_errors):
        counts["invalid_records"] += 1
        if isinstance(record_errors, dict) and record_errors:
            error_paths = [key for key in record_errors.keys()
                           if isinstance(key, str)]
            if error_paths and all(path.startswith(MONUMENT_SOURCES_ERROR_PREFIX) for path in error_paths):
                counts["monument_sources_only_invalid_records"] += 1
                return
        counts["non_monument_source_invalid_records"] += 1

    if isinstance(errors, dict):
        for record_errors in errors.values():
            classify_record_errors(record_errors)
    elif isinstance(errors, list):
        for error_entry in errors:
            if isinstance(error_entry, dict) and error_entry:
                for record_errors in error_entry.values():
                    classify_record_errors(record_errors)
            else:
                classify_record_errors(error_entry)

    return counts


def run_hapi_seed_upload(
    task_id,
    seed_limit_count=0,
    clean_monument_sources=True,
    refresh_data=True,
    clear_data_on_complete=True,
    should_terminate=None,
    progress_callback=None,
):
    from arches_her.data_access.common import refresh_materialized_views
    from arches_her.tasks import update_log_messages

    logger = logging.getLogger(__name__)
    logger.info(
        "HAPI_SEED STARTED - Task ID: %s, seed_limit_count=%s",
        task_id,
        seed_limit_count,
    )

    start_date = datetime(1, 1, 1)
    log_id = None
    resources = []
    run_type = models.HeritageApiLog.MANUAL
    seed = True

    try:
        _check_for_termination(should_terminate)
        start_time = timezone.now()

        if refresh_data:
            if progress_callback:
                progress_callback(
                    {"message": "Refreshing materialized views...", "current_phase": "data_refresh",
                        "processed_resources": 0, "total_resources": 0, "percentage": 0}
                )
            refresh_materialized_views(with_data=True)
            _check_for_termination(should_terminate)

        resources = get_resources(
            start_date=start_date, seed=seed, seed_limit_count=int(seed_limit_count))

        if not resources:
            message = f"No resources found using start date {start_date.isoformat()}."
            log_id = models.HeritageApiLog.objects.create(
                start=start_time,
                finish=timezone.now(),
                parameters=_build_hapi_log_parameters(
                    start_date, operation="seed"),
                run_type=run_type,
                messages={"get_resources": message},
            ).id
            return {"status": "success", "message": message, "status_code": 200, "log_id": str(log_id), "count": 0, "task_id": task_id}

        username = settings.HAPI_USERNAME
        password = settings.HAPI_PASSWORD

        submission_total_count = len(resources)
        total_parts = ceil(submission_total_count / MAX_BATCH_SIZE)
        total_count, published_count = get_counts()
        counts = {"total_count": total_count, "published_count": published_count,
                  "submitted_count": submission_total_count}

        processed_resources = 0
        total_records_processed = 0

        if progress_callback:
            progress_callback(
                {"message": "Initializing batch upload...", "processed_resources": 0,
                    "total_resources": submission_total_count, "percentage": 0, "current_phase": "initialization"}
            )

        bearer_token = authenticate_service(
            username=username, password=password)
        _check_for_termination(should_terminate)

        batch_id = batch_create_service(
            bearer_token=bearer_token, counts=counts)

        submission_count = 0

        for i in range(0, submission_total_count, MAX_BATCH_SIZE):
            _check_for_termination(should_terminate)

            start_time = timezone.now()
            new_log = models.HeritageApiLog.objects.create(
                start=start_time,
                parameters=_build_hapi_log_parameters(
                    start_date, operation="seed"),
                run_type=run_type,
            )

            log_id = new_log.id
            batch_resources = resources[i: i + MAX_BATCH_SIZE]
            submission_count += 1

            models.HeritageApiLog.objects.filter(
                id=log_id).update(totals=counts, batch_id=batch_id)
            update_log_messages(
                log_id, "part", f"{submission_count} of {total_parts}")
            models.HeritageApiLog.objects.filter(id=log_id).update(
                resources=serialize(batch_resources))

            part = 1

            for s in range(0, len(batch_resources), MAX_SUBMISSION_SIZE):
                _check_for_termination(should_terminate)

                submission_batch = batch_resources[s: s + MAX_SUBMISSION_SIZE]
                resource_instance_ids = ",".join(
                    str(r["resource_instance_id"]) for r in submission_batch)

                processed_resources += len(submission_batch)
                percentage = round(
                    (processed_resources / submission_total_count) * 100, 1)

                if progress_callback:
                    progress_callback(
                        {"message": f"Processing batch {submission_count}/{total_parts}, part {part}", "processed_resources": processed_resources, "total_resources": submission_total_count,
                            "percentage": percentage, "current_phase": "validation", "batch_id": batch_id, "current_batch": submission_count, "total_batches": total_parts}
                    )

                results, status_code = validate_service(
                    resource_object=submission_batch)

                if not results:
                    return {"status": "failure", "message": f"No records generated for {resource_instance_ids}", "task_id": task_id}

                models.HeritageApiData.objects.create(
                    hapi_log_id=log_id,
                    batch_id=batch_id,
                    part=part,
                    validation=serialize(results["response"]),
                    data=serialize(results["data"]),
                )

                total_records_processed += len(results["data"]["records"])

                if progress_callback:
                    progress_callback(
                        {"message": f"Submitting batch {submission_count}/{total_parts}, part {part}", "processed_resources": processed_resources, "total_resources": submission_total_count,
                            "processed_records": total_records_processed, "percentage": percentage, "current_phase": "submission", "batch_id": batch_id, "current_batch": submission_count, "total_batches": total_parts}
                    )

                status_code, reason, text = batch_submit_service(
                    bearer_token=bearer_token,
                    batch_id=batch_id,
                    records=results["data"]["records"],
                )

                try:
                    submission_response = json.loads(text) if text else {}
                except (json.JSONDecodeError, TypeError):
                    submission_response = {
                        "raw_response": text, "parse_error": True}

                hapi_data_entry = models.HeritageApiData.objects.filter(
                    hapi_log_id=log_id, batch_id=batch_id, part=part).first()
                if hapi_data_entry:
                    hapi_data_entry.submission_response = serialize(
                        submission_response)
                    hapi_data_entry.save()

                batch_result = {
                    "status_code": status_code,
                    "batch": str(batch_id),
                    "resources": len(submission_batch),
                    "records": len(results["data"]["records"]),
                    "reason": reason,
                    "text": submission_response,
                }
                update_log_messages(
                    log_id, f"part_{submission_count}_{part}", batch_result)
                part += 1

        if progress_callback:
            progress_callback(
                {"message": "Finalizing batch submission...", "processed_resources": processed_resources, "total_resources": submission_total_count,
                    "processed_records": total_records_processed, "percentage": 100, "current_phase": "finalization", "batch_id": batch_id}
            )

        _check_for_termination(should_terminate)
        response = batch_finalise_service(
            bearer_token=bearer_token, batch_id=batch_id)

        if response == 200:
            update_log_messages(log_id, "summary", {
                                "count": submission_total_count, "records_processed": total_records_processed, "batch_id": batch_id})
            models.HeritageApiLog.objects.filter(
                id=log_id).update(finish=timezone.now())

        return {"status": "success", "status_code": response, "batch_id": batch_id, "log_id": str(log_id), "count": submission_total_count, "task_id": task_id}

    except RuntimeTerminationRequested as exc:
        termination_type = getattr(exc, "termination_type", "terminate")
        logger.warning("HAPI_SEED %s - Task ID: %s",
                       termination_type.upper(), task_id)
        if log_id:
            from arches_her.tasks import update_log_messages
            update_log_messages(
                log_id, "termination", f"Seed operation {termination_type} by user request")
            _record_termination_status(log_id, termination_type)
        return {"status": termination_type, "message": f"Seed operation {termination_type}.", "task_id": task_id, "log_id": str(log_id) if log_id else None}

    except Exception as exc:
        tb_str = "".join(traceback.format_exception(
            type(exc), exc, exc.__traceback__))
        logger.error("Error running HAPI seed upload: %s", tb_str)

        if not log_id:
            log_id = models.HeritageApiLog.objects.create(
                start=timezone.now(),
                run_type=run_type,
                parameters=_build_hapi_log_parameters(
                    start_date, operation="seed"),
                resources=serialize(resources) if resources else None,
            ).id

        models.HeritageApiLog.objects.filter(
            id=log_id).update(exceptions={"Exception": tb_str})
        email_error(
            body="An error occurred during the HAPI seed process:", error=tb_str)
        return {"status": "error", "status_code": 500, "error": tb_str, "task_id": task_id, "log_id": str(log_id)}

    finally:
        if clear_data_on_complete:
            if progress_callback:
                progress_callback({"message": "Finalizing materialized views...", "current_phase": "data_refresh_finalizing",
                                  "processed_resources": 0, "total_resources": 0, "percentage": 100})
            from arches_her.data_access.common import refresh_materialized_views
            refresh_materialized_views(with_data=False)


def run_hapi_validate_only_upload(
    task_id,
    seed_limit_count=0,
    clean_monument_sources=True,
    refresh_data=True,
    clear_data_on_complete=True,
    should_terminate=None,
    progress_callback=None,
    operation="validate",
):
    from arches_her.data_access.common import refresh_materialized_views
    from arches_her.tasks import update_log_messages

    logger = logging.getLogger(__name__)
    logger.info(
        "HAPI_VALIDATE_ONLY STARTED - Task ID: %s, seed_limit_count=%s",
        task_id,
        seed_limit_count,
    )

    start_date = datetime(1, 1, 1)
    log_id = None
    resources = []
    run_type = models.HeritageApiLog.MANUAL
    seed = True

    try:
        _check_for_termination(should_terminate)
        start_time = timezone.now()

        if refresh_data:
            if progress_callback:
                progress_callback(
                    {"message": "Refreshing materialized views...", "current_phase": "data_refresh",
                        "processed_resources": 0, "total_resources": 0, "percentage": 0}
                )
            refresh_materialized_views(with_data=True)
            _check_for_termination(should_terminate)

        resources = get_resources(
            start_date=start_date, seed=seed, seed_limit_count=int(seed_limit_count))

        if not resources:
            message = f"No resources found using start date {start_date.isoformat()}."
            log_id = models.HeritageApiLog.objects.create(
                start=start_time,
                finish=timezone.now(),
                parameters=_build_hapi_log_parameters(
                    start_date, operation=operation),
                run_type=run_type,
                messages={"get_resources": message},
            ).id
            return {"status": "success", "message": message, "status_code": 200, "log_id": str(log_id), "count": 0, "task_id": task_id, "validation_only": True}

        submission_total_count = len(resources)
        total_parts = ceil(submission_total_count / MAX_BATCH_SIZE)
        total_count, published_count = get_counts()
        counts = {"total_count": total_count, "published_count": published_count,
                  "submitted_count": submission_total_count}

        processed_resources = 0
        total_valid_records = 0
        total_invalid_records = 0
        total_valid_records_including_monument_sources = 0
        total_monument_source_only_records = 0
        total_invalid_records_excluding_monument_sources = 0

        if progress_callback:
            progress_callback(
                {"message": "Initializing validation process...", "processed_resources": 0, "total_resources": submission_total_count,
                    "percentage": 0, "current_phase": "initialization", "validation_only": True}
            )

        min_batch_id = models.HeritageApiData.objects.filter(
            batch_id__lt=0).aggregate(min_batch_id=Min("batch_id"))["min_batch_id"]
        validation_batch_id = -1 if min_batch_id is None else min_batch_id - 1

        submission_count = 0

        for i in range(0, submission_total_count, MAX_BATCH_SIZE):
            _check_for_termination(should_terminate)

            start_time = timezone.now()
            new_log = models.HeritageApiLog.objects.create(
                start=start_time,
                parameters=_build_hapi_log_parameters(
                    start_date, operation=operation),
                run_type=run_type,
            )

            log_id = new_log.id
            batch_resources = resources[i: i + MAX_BATCH_SIZE]
            submission_count += 1

            models.HeritageApiLog.objects.filter(id=log_id).update(
                totals=counts, batch_id=validation_batch_id)
            update_log_messages(
                log_id, "part", f"{submission_count} of {total_parts}")
            update_log_messages(log_id, "validation_only", True)
            models.HeritageApiLog.objects.filter(id=log_id).update(
                resources=serialize(batch_resources))

            part = 1

            for s in range(0, len(batch_resources), MAX_SUBMISSION_SIZE):
                _check_for_termination(should_terminate)

                submission_batch = batch_resources[s: s + MAX_SUBMISSION_SIZE]
                resource_instance_ids = ",".join(
                    str(r["resource_instance_id"]) for r in submission_batch)

                processed_resources += len(submission_batch)
                percentage = round(
                    (processed_resources / submission_total_count) * 100, 1)

                if progress_callback:
                    progress_callback(
                        {"message": f"Validating batch {submission_count}/{total_parts}, part {part}", "processed_resources": processed_resources, "total_resources": submission_total_count, "percentage": percentage, "current_phase": "validation", "batch_id": validation_batch_id, "current_batch": submission_count, "total_batches": total_parts, "valid_records": total_valid_records, "invalid_records": total_invalid_records_excluding_monument_sources,
                            "valid_records_including_monument_sources": total_valid_records_including_monument_sources, "monument_source_only_records": total_monument_source_only_records, "invalid_records_excluding_monument_sources": total_invalid_records_excluding_monument_sources, "total_passed_validation_records": total_valid_records_including_monument_sources, "validation_only": True}
                    )

                results, status_code = validate_service(
                    resource_object=submission_batch)

                if not results:
                    return {"status": "failure", "message": f"No records generated for {resource_instance_ids}", "task_id": task_id, "validation_only": True}

                models.HeritageApiData.objects.create(
                    hapi_log_id=log_id,
                    batch_id=validation_batch_id,
                    part=part,
                    validation=serialize(results["response"]),
                    data=serialize(results["data"]),
                )

                validation_counts = _classify_validation_response_records(
                    results["response"])
                invalid_records_in_batch = min(
                    max(validation_counts["invalid_records"], 0), len(submission_batch))
                valid_records_in_batch = len(
                    submission_batch) - invalid_records_in_batch
                non_monument_source_invalid_records_in_batch = min(max(
                    validation_counts["non_monument_source_invalid_records"], 0), len(submission_batch))
                monument_source_only_records_in_batch = min(max(
                    validation_counts["monument_sources_only_invalid_records"], 0), len(submission_batch))
                valid_records_including_monument_sources_in_batch = len(
                    submission_batch) - non_monument_source_invalid_records_in_batch

                total_invalid_records += invalid_records_in_batch
                total_valid_records += valid_records_in_batch
                total_valid_records_including_monument_sources += valid_records_including_monument_sources_in_batch
                total_monument_source_only_records += monument_source_only_records_in_batch
                total_invalid_records_excluding_monument_sources += non_monument_source_invalid_records_in_batch

                update_log_messages(
                    log_id,
                    f"part_{submission_count}_{part}",
                    {"status": "valid" if status_code == 200 else "invalid", "resources": len(submission_batch), "records": len(
                        results["data"]["records"]) if status_code == 200 else 0, "status_code": status_code},
                )

                part += 1

        if progress_callback:
            progress_callback(
                {"message": "Completing validation...", "processed_resources": processed_resources, "total_resources": submission_total_count, "percentage": 100, "current_phase": "completion", "batch_id": validation_batch_id, "valid_records": total_valid_records, "invalid_records": total_invalid_records_excluding_monument_sources,
                    "valid_records_including_monument_sources": total_valid_records_including_monument_sources, "monument_source_only_records": total_monument_source_only_records, "invalid_records_excluding_monument_sources": total_invalid_records_excluding_monument_sources, "total_passed_validation_records": total_valid_records_including_monument_sources, "validation_only": True}
            )

        _check_for_termination(should_terminate)
        update_log_messages(
            log_id,
            "summary",
            {"count": submission_total_count, "valid_records": total_valid_records, "invalid_records": total_invalid_records, "valid_records_including_monument_sources": total_valid_records_including_monument_sources,
                "monument_source_only_records": total_monument_source_only_records, "invalid_records_excluding_monument_sources": total_invalid_records_excluding_monument_sources, "total_passed_validation_records": total_valid_records_including_monument_sources},
        )
        models.HeritageApiLog.objects.filter(
            id=log_id).update(finish=timezone.now())

        return {"status": "success", "status_code": 200, "batch_id": validation_batch_id, "log_id": str(log_id), "count": submission_total_count, "task_id": task_id, "validation_only": True, "valid_records": total_valid_records, "invalid_records": total_invalid_records, "valid_records_including_monument_sources": total_valid_records_including_monument_sources, "monument_source_only_records": total_monument_source_only_records, "invalid_records_excluding_monument_sources": total_invalid_records_excluding_monument_sources, "total_passed_validation_records": total_valid_records_including_monument_sources}

    except RuntimeTerminationRequested as exc:
        termination_type = getattr(exc, "termination_type", "terminate")
        logger.warning("HAPI_VALIDATE_ONLY %s - Task ID: %s",
                       termination_type.upper(), task_id)
        if log_id:
            from arches_her.tasks import update_log_messages
            models.HeritageApiLog.objects.filter(
                id=log_id).update(finish=timezone.now())
            update_log_messages(
                log_id, "termination", f"Validation operation {termination_type} by user request")
            _record_termination_status(log_id, termination_type)
        return {"status": termination_type, "message": f"Validation operation {termination_type}.", "task_id": task_id, "log_id": str(log_id) if log_id else None, "validation_only": True}

    except Exception as exc:
        tb_str = "".join(traceback.format_exception(
            type(exc), exc, exc.__traceback__))
        logger.error("Error running HAPI validate-only upload: %s", tb_str)

        if not log_id:
            log_id = models.HeritageApiLog.objects.create(
                start=timezone.now(),
                run_type=run_type,
                parameters=_build_hapi_log_parameters(
                    start_date, operation=operation),
                resources=serialize(resources) if resources else None,
            ).id

        models.HeritageApiLog.objects.filter(
            id=log_id).update(exceptions={"Exception": tb_str})
        email_error(
            body="An error occurred during the HAPI validation-only process:", error=tb_str)
        return {"status": "error", "status_code": 500, "error": tb_str, "task_id": task_id, "log_id": str(log_id), "validation_only": True}

    finally:
        if clear_data_on_complete:
            if progress_callback:
                progress_callback({"message": "Finalizing materialized views...", "current_phase": "data_refresh_finalizing",
                                  "processed_resources": 0, "total_resources": 0, "percentage": 100})
            from arches_her.data_access.common import refresh_materialized_views
            refresh_materialized_views(with_data=False)


def run_hapi_dry_run_upload(
    task_id,
    seed_limit_count=0,
    clean_monument_sources=True,
    refresh_data=True,
    clear_data_on_complete=True,
    should_terminate=None,
    progress_callback=None,
):
    """Run dry-run validation by reusing the validate-only runtime flow with dry-run markers."""

    def _dry_run_progress_callback(meta):
        if not progress_callback:
            return
        payload = dict(meta or {})
        payload["dry_run"] = True
        payload["validation_only"] = True
        progress_callback(payload)

    result = run_hapi_validate_only_upload(
        task_id=task_id,
        seed_limit_count=seed_limit_count,
        clean_monument_sources=clean_monument_sources,
        refresh_data=refresh_data,
        clear_data_on_complete=clear_data_on_complete,
        should_terminate=should_terminate,
        progress_callback=_dry_run_progress_callback,
        operation="dry-run",
    )

    if not isinstance(result, dict):
        return {"status": "failure", "message": "Dry-run operation failed", "task_id": task_id, "dry_run": True, "validation_only": True}

    payload = dict(result)
    payload["dry_run"] = True
    payload["validation_only"] = True

    if payload.get("status") == "terminated":
        payload["message"] = "Dry-run operation terminated."

    return payload


def _run_daemon(operation, worker_fn, task_id, seed_limit_count, clean_monument_sources, refresh_data, clear_data_on_complete, shutdown_on_complete):
    """Shared daemon loop used by all three operation modes."""
    logger = logging.getLogger(__name__)
    runtime = SeedRuntimeState(
        task_id=task_id,
        clean_monument_sources=clean_monument_sources,
        seed_limit_count=seed_limit_count,
        refresh_data=refresh_data,
        clear_data_on_complete=clear_data_on_complete,
        operation=operation,
    )

    _ensure_socket_removed(IPC_ADDRESS)
    listener = Listener(IPC_ADDRESS, family=IPC_FAMILY)

    def _worker():
        result = worker_fn(should_terminate=runtime.should_terminate,
                           progress_callback=runtime.set_progress)

        if isinstance(result, dict) and result.get("status") in ("terminated", "shutdown"):
            runtime.set_terminated(result)
        elif isinstance(result, dict) and result.get("status") in ("error", "failure"):
            runtime.set_failure(result.get("error") or result.get(
                "message") or f"{operation} operation failed")
        else:
            runtime.set_success(result)

        if shutdown_on_complete:
            request_runtime_exit(IPC_ADDRESS)

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()

    try:
        while True:
            conn = listener.accept()
            try:
                request = conn.recv()
                command = str((request or {}).get("command", "")).upper()

                if command == "STATUS":
                    conn.send(runtime.get_status_payload())
                elif command == "TERMINATE":
                    runtime.request_terminate("terminate")
                    conn.send(
                        {"status": "terminating", "message": f"{operation.capitalize()} task {task_id} is being terminated.", "task_id": task_id})
                elif command == "PING":
                    conn.send({"status": "ok", "task_id": task_id})
                elif command == "SHUTDOWN":
                    runtime.request_terminate("shutdown")
                    conn.send({"status": "shutting_down", "task_id": task_id})
                    break
                elif command == "EXIT":
                    conn.send({"status": "shutting_down", "task_id": task_id})
                    break
                else:
                    conn.send(
                        {"status": "error", "message": f"Unknown command: {command}"})
            finally:
                conn.close()

            if runtime.state in ("SUCCESS", "FAILURE", "TERMINATED"):
                continue

    except Exception:
        logger.exception(
            "%s daemon encountered an unexpected error", operation)
    finally:
        listener.close()
        _ensure_socket_removed(IPC_ADDRESS)
        worker.join(timeout=60)


def run_seed_daemon(task_id, seed_limit_count=0, clean_monument_sources=True, refresh_data=True, clear_data_on_complete=True, shutdown_on_complete=False):
    def worker_fn(**kwargs):
        return run_hapi_seed_upload(
            task_id=task_id,
            seed_limit_count=seed_limit_count,
            clean_monument_sources=clean_monument_sources,
            refresh_data=refresh_data,
            clear_data_on_complete=clear_data_on_complete,
            **kwargs,
        )

    _run_daemon("seed", worker_fn, task_id, seed_limit_count, clean_monument_sources,
                refresh_data, clear_data_on_complete, shutdown_on_complete)


def run_validate_daemon(task_id, seed_limit_count=0, clean_monument_sources=True, refresh_data=True, clear_data_on_complete=True, shutdown_on_complete=False):
    def worker_fn(**kwargs):
        return run_hapi_validate_only_upload(
            task_id=task_id,
            seed_limit_count=seed_limit_count,
            clean_monument_sources=clean_monument_sources,
            refresh_data=refresh_data,
            clear_data_on_complete=clear_data_on_complete,
            **kwargs,
        )

    _run_daemon("validate", worker_fn, task_id, seed_limit_count, clean_monument_sources,
                refresh_data, clear_data_on_complete, shutdown_on_complete)


def run_dry_run_daemon(task_id, seed_limit_count=0, clean_monument_sources=True, refresh_data=True, clear_data_on_complete=True, shutdown_on_complete=False):
    def worker_fn(**kwargs):
        return run_hapi_dry_run_upload(
            task_id=task_id,
            seed_limit_count=seed_limit_count,
            clean_monument_sources=clean_monument_sources,
            refresh_data=refresh_data,
            clear_data_on_complete=clear_data_on_complete,
            **kwargs,
        )

    _run_daemon("dry-run", worker_fn, task_id, seed_limit_count, clean_monument_sources,
                refresh_data, clear_data_on_complete, shutdown_on_complete)


def run_hapi_cron_upload(
    task_id,
    clean_monument_sources=True,
    refresh_data=True,
    clear_data_on_complete=True,
    run_type=models.HeritageApiLog.MANUAL,
    should_terminate=None,
    progress_callback=None,
):
    from arches_her.data_access.common import refresh_materialized_views
    from arches_her.tasks import update_log_messages

    logger = logging.getLogger(__name__)
    logger.info(
        "HAPI_CRON STARTED - Task ID: %s, clean_monument_sources=%s, refresh_data=%s",
        task_id,
        clean_monument_sources,
        refresh_data,
    )

    start_date = datetime(1, 1, 1)
    latest_timestamp = None
    log_id = None
    resources = []

    if run_type not in (models.HeritageApiLog.AUTOMATIC, models.HeritageApiLog.MANUAL):
        raise ValueError(f"Invalid run type: {run_type}")

    seed = False

    try:
        _check_for_termination(should_terminate)
        start_time = timezone.now()

        if refresh_data:
            if progress_callback:
                progress_callback(
                    {
                        "message": "Refreshing materialized views...",
                        "current_phase": "data_refresh",
                        "processed_resources": 0,
                        "total_resources": 0,
                        "percentage": 0,
                    }
                )
            refresh_materialized_views(with_data=True)
            _check_for_termination(should_terminate)

        max_batch_id = models.HeritageApiLog.objects.filter(
            batch_id__gt=0).aggregate(max_batch_id=Max("batch_id"))["max_batch_id"]
        positive_batch_start = None

        if max_batch_id is not None:
            latest_timestamp = models.HeritageApiLog.objects.filter(
                batch_id=max_batch_id).aggregate(start=Min("start"))
            positive_batch_start = latest_timestamp.get("start")

        null_batch_start = (
            models.HeritageApiLog.objects.filter(batch_id__isnull=True).order_by(
                "-start").values_list("start", flat=True).first()
        )

        candidate_starts = [dt for dt in [
            positive_batch_start, null_batch_start] if dt is not None]
        if candidate_starts:
            start_date = max(candidate_starts)

        resources = get_resources(
            start_date=start_date, seed=seed, seed_limit_count=0)

        if not resources:
            message = f"No resources found using start date {start_date.isoformat()}."
            log_id = models.HeritageApiLog.objects.create(
                start=start_time,
                finish=timezone.now(),
                parameters=_build_hapi_log_parameters(
                    start_date, operation="cron"),
                run_type=run_type,
                messages={"get_resources": message},
            ).id
            return {
                "status": "success",
                "message": message,
                "status_code": 200,
                "log_id": str(log_id),
                "count": 0,
                "task_id": task_id,
            }

        username = settings.HAPI_USERNAME
        password = settings.HAPI_PASSWORD

        submission_total_count = len(resources)
        total_parts = ceil(submission_total_count / MAX_BATCH_SIZE)
        total_count, published_count = get_counts()
        counts = {
            "total_count": total_count,
            "published_count": published_count,
            "submitted_count": submission_total_count,
        }

        processed_resources = 0
        total_records_processed = 0

        if progress_callback:
            progress_callback(
                {
                    "message": "Initializing batch upload...",
                    "processed_resources": 0,
                    "total_resources": submission_total_count,
                    "percentage": 0,
                    "current_phase": "initialization",
                }
            )

        bearer_token = authenticate_service(
            username=username, password=password)
        _check_for_termination(should_terminate)

        batch_id = batch_create_service(
            bearer_token=bearer_token, counts=counts)

        submission_count = 0

        for i in range(0, submission_total_count, MAX_BATCH_SIZE):
            _check_for_termination(should_terminate)

            start_time = timezone.now()
            new_log = models.HeritageApiLog.objects.create(
                start=start_time,
                parameters=_build_hapi_log_parameters(
                    start_date, operation="cron"),
                run_type=run_type,
            )

            log_id = new_log.id
            batch_resources = resources[i: i + MAX_BATCH_SIZE]
            submission_count += 1

            models.HeritageApiLog.objects.filter(
                id=log_id).update(totals=counts, batch_id=batch_id)
            update_log_messages(
                log_id, "part", f"{submission_count} of {total_parts}")
            models.HeritageApiLog.objects.filter(id=log_id).update(
                resources=serialize(batch_resources))

            part = 1

            for s in range(0, len(batch_resources), MAX_SUBMISSION_SIZE):
                _check_for_termination(should_terminate)

                submission_batch = batch_resources[s: s + MAX_SUBMISSION_SIZE]
                resource_instance_ids = ",".join(
                    str(r["resource_instance_id"]) for r in submission_batch)

                processed_resources += len(submission_batch)
                percentage = round(
                    (processed_resources / submission_total_count) * 100, 1)

                if progress_callback:
                    progress_callback(
                        {
                            "message": f"Processing batch {submission_count}/{total_parts}, part {part}",
                            "processed_resources": processed_resources,
                            "total_resources": submission_total_count,
                            "percentage": percentage,
                            "current_phase": "validation",
                            "batch_id": batch_id,
                            "current_batch": submission_count,
                            "total_batches": total_parts,
                        }
                    )

                results, status_code = validate_service(
                    resource_object=submission_batch)

                if not results:
                    return {
                        "status": "failure",
                        "message": f"No records generated for {resource_instance_ids}",
                        "task_id": task_id,
                    }

                models.HeritageApiData.objects.create(
                    hapi_log_id=log_id,
                    batch_id=batch_id,
                    part=part,
                    validation=serialize(results["response"]),
                    data=serialize(results["data"]),
                )

                total_records_processed += len(results["data"]["records"])

                if progress_callback:
                    progress_callback(
                        {
                            "message": f"Submitting batch {submission_count}/{total_parts}, part {part}",
                            "processed_resources": processed_resources,
                            "total_resources": submission_total_count,
                            "processed_records": total_records_processed,
                            "percentage": percentage,
                            "current_phase": "submission",
                            "batch_id": batch_id,
                            "current_batch": submission_count,
                            "total_batches": total_parts,
                        }
                    )

                status_code, reason, text = batch_submit_service(
                    bearer_token=bearer_token,
                    batch_id=batch_id,
                    records=results["data"]["records"],
                )

                try:
                    submission_response = json.loads(text) if text else {}
                except (json.JSONDecodeError, TypeError):
                    submission_response = {
                        "raw_response": text, "parse_error": True}

                hapi_data_entry = models.HeritageApiData.objects.filter(
                    hapi_log_id=log_id, batch_id=batch_id, part=part).first()
                if hapi_data_entry:
                    hapi_data_entry.submission_response = serialize(
                        submission_response)
                    hapi_data_entry.save()

                batch_result = {
                    "status_code": status_code,
                    "batch": str(batch_id),
                    "resources": len(submission_batch),
                    "records": len(results["data"]["records"]),
                    "reason": reason,
                    "text": submission_response,
                }
                update_log_messages(
                    log_id, f"part_{submission_count}_{part}", batch_result)
                part += 1

        if progress_callback:
            progress_callback(
                {
                    "message": "Finalizing batch submission...",
                    "processed_resources": processed_resources,
                    "total_resources": submission_total_count,
                    "processed_records": total_records_processed,
                    "percentage": 100,
                    "current_phase": "finalization",
                    "batch_id": batch_id,
                }
            )

        _check_for_termination(should_terminate)
        response = batch_finalise_service(
            bearer_token=bearer_token, batch_id=batch_id)

        if response == 200:
            update_log_messages(
                log_id,
                "summary",
                {
                    "count": submission_total_count,
                    "records_processed": total_records_processed,
                    "batch_id": batch_id,
                },
            )
            models.HeritageApiLog.objects.filter(
                id=log_id).update(finish=timezone.now())

        return {
            "status": "success",
            "status_code": response,
            "batch_id": batch_id,
            "log_id": str(log_id),
            "count": submission_total_count,
            "task_id": task_id,
        }

    except RuntimeTerminationRequested as exc:
        termination_type = getattr(exc, "termination_type", "terminate")
        logger.warning("HAPI_CRON %s - Task ID: %s",
                       termination_type.upper(), task_id)
        if log_id:
            update_log_messages(
                log_id, "termination", f"Batch upload {termination_type} by user request")
            _record_termination_status(log_id, termination_type)

        return {
            "status": termination_type,
            "message": f"Batch upload {termination_type}.",
            "task_id": task_id,
            "log_id": str(log_id) if log_id else None,
        }

    except Exception as exc:
        tb_str = "".join(traceback.format_exception(
            type(exc), exc, exc.__traceback__))
        logger.error("Error running HAPI cron upload: %s", tb_str)

        if not log_id:
            log_id = models.HeritageApiLog.objects.create(
                start=timezone.now(),
                run_type=run_type,
                parameters=_build_hapi_log_parameters(
                    start_date, operation="cron"),
                resources=serialize(resources) if resources else None,
            ).id

        models.HeritageApiLog.objects.filter(
            id=log_id).update(exceptions={"Exception": tb_str})
        email_error(
            body="An error occurred during the HAPI cron process:", error=tb_str)

        return {
            "status": "error",
            "status_code": 500,
            "error": tb_str,
            "task_id": task_id,
            "log_id": str(log_id),
        }

    finally:
        if clear_data_on_complete:
            if progress_callback:
                progress_callback(
                    {
                        "message": "Finalizing materialized views...",
                        "current_phase": "data_refresh_finalizing",
                        "processed_resources": 0,
                        "total_resources": 0,
                        "percentage": 100,
                    }
                )
            from arches_her.data_access.common import refresh_materialized_views
            refresh_materialized_views(with_data=False)


def run_cron_daemon(
    task_id,
    clean_monument_sources=True,
    refresh_data=True,
    clear_data_on_complete=True,
    shutdown_on_complete=False,
    run_type=models.HeritageApiLog.MANUAL,
):
    logger = logging.getLogger(__name__)
    runtime = SeedRuntimeState(
        task_id=task_id,
        clean_monument_sources=clean_monument_sources,
        seed_limit_count=0,
        refresh_data=refresh_data,
        clear_data_on_complete=clear_data_on_complete,
        operation="cron",
    )

    _ensure_socket_removed(CRON_IPC_ADDRESS)
    listener = Listener(CRON_IPC_ADDRESS, family=IPC_FAMILY)

    def _worker():
        result = run_hapi_cron_upload(
            task_id=task_id,
            clean_monument_sources=clean_monument_sources,
            refresh_data=refresh_data,
            clear_data_on_complete=clear_data_on_complete,
            run_type=run_type,
            should_terminate=runtime.should_terminate,
            progress_callback=runtime.set_progress,
        )

        if isinstance(result, dict) and result.get("status") in ("terminated", "shutdown"):
            runtime.set_terminated(result)
        elif isinstance(result, dict) and result.get("status") in ("error", "failure"):
            runtime.set_failure(result.get("error") or result.get(
                "message") or "Batch upload failed")
        else:
            runtime.set_success(result)

        if shutdown_on_complete:
            request_runtime_exit(CRON_IPC_ADDRESS)

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()

    try:
        while True:
            conn = listener.accept()
            try:
                request = conn.recv()
                command = str((request or {}).get("command", "")).upper()

                if command == "STATUS":
                    conn.send(runtime.get_status_payload())
                elif command == "TERMINATE":
                    runtime.request_terminate("terminate")
                    conn.send(
                        {
                            "status": "terminating",
                            "message": f"Batch upload task {task_id} is being terminated.",
                            "task_id": task_id,
                        }
                    )
                elif command == "PING":
                    conn.send({"status": "ok", "task_id": task_id})
                elif command == "SHUTDOWN":
                    runtime.request_terminate("shutdown")
                    conn.send({"status": "shutting_down", "task_id": task_id})
                    break
                elif command == "EXIT":
                    conn.send({"status": "exiting", "task_id": task_id})
                    break
                else:
                    conn.send(
                        {"status": "error", "message": f"Unknown command: {command}"})
            finally:
                conn.close()

            if runtime.state in ("SUCCESS", "FAILURE", "TERMINATED"):
                continue

    except Exception:
        logger.exception("Cron daemon encountered an unexpected error")
    finally:
        listener.close()
        _ensure_socket_removed(CRON_IPC_ADDRESS)
        worker.join(timeout=60)
