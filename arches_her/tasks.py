import json
import traceback
import logging
import time
from math import ceil
from datetime import datetime
from uuid import UUID
from arches_her.data_access.common import get_resources, get_counts
from celery import shared_task
from arches.app.models.system_settings import settings
from django.db.models import Max, Min
from arches_her.services import (
    authenticate as authenticate_service,
    batch_submit as batch_submit_service,
    batch_create as batch_create_service,
    validate as validate_service,
    batch_finalise as batch_finalise_service,
)
from arches_her.models import models
from django.utils import timezone
from .hapi.helper import email_error
from .data_access.common import serialize
from django.core.cache import cache
from django.core.management import call_command
from celery.result import AsyncResult

MAX_BATCH_SIZE = 5000
MAX_SUBMISSION_SIZE = 100


@shared_task
def add(x, y):
    z = x + y
    return z


@shared_task(bind=True)
def hapi_upload(self, *args, **kwargs) -> str:

    logger = logging.getLogger(__name__)

    def progress_callback(message):
        self.update_state(state="PROGRESS", meta={"message": message})

    def check_termination(log_id: UUID):
        if self.request.id and AsyncResult(self.request.id).state == "REVOKED":
            logger.info(f"H.API Upload task {self.request.id} was terminated by user.")
            update_log_messages(log_id, "termination", "Task was terminated by user.")
            return {"status": "terminated", "message": "Task was terminated by user."}

    self.update_state(
        state="PROGRESS", meta={"message": "Starting H.API upload task..."}
    )

    from arches_her.data_access.common import refresh_materialized_views

    start_date = datetime(1, 1, 1)
    latest_timestamp = None
    log_id = None

    # Initialize a list to store results from all batches
    batch_results = []

    run_type = kwargs.get("run_type", models.HeritageApiLog.AUTOMATIC)
    if run_type not in [models.HeritageApiLog.AUTOMATIC, models.HeritageApiLog.MANUAL]:
        raise ValueError(f"Invalid run type: {run_type}")

    seed = kwargs.get("seed", False) or False

    if seed not in [True, False]:
        raise ValueError(f"Invalid seed value: {seed}")

    try:
        start_time = timezone.now()

        self.update_state(
            state="PROGRESS", meta={"message": "Refreshing materialized views..."}
        )

        refresh_materialized_views(with_data=True)

        if not seed:
            start_date_dict = (
                models.HeritageApiLog.objects.filter(finish__isnull=False)
                .order_by("-finish")
                .values("start")
                .first()
            )
            start_date = (
                start_date_dict["start"] if start_date_dict else datetime(1, 1, 1)
            )

        resources = get_resources(start_date=start_date, seed=seed)

        if not resources:
            message = f"No resources found using start date {start_date.isoformat()}"
            log_id = models.HeritageApiLog.objects.create(
                start=start_time,
                finish=timezone.now(),
                parameters={"from": start_date.isoformat()},
                run_type=run_type,
                messages={"get_resources": message},
            ).id
            self.update_state(
                state="SUCCESS",
                meta={
                    "message": message,
                },
            )
            return {
                "status": "success",
                "message": message,
                "status_code": 200,
                "log_id": str(log_id),
                "count": 0,
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

        bearer_token = authenticate_service(username=username, password=password)

        batch_id = batch_create_service(bearer_token=bearer_token, counts=counts)

        submission_count = 0
        processed_resources = 0

        for i in range(0, submission_total_count, MAX_BATCH_SIZE):
            start_time = timezone.now()
            new_log = models.HeritageApiLog.objects.create(
                start=start_time,
                parameters={"from": start_date.isoformat()},
                run_type=run_type,
            )

            log_id = new_log.id
            batch_resources = resources[i : i + MAX_BATCH_SIZE]
            submission_count += 1

            models.HeritageApiLog.objects.filter(id=log_id).update(totals=counts)

            models.HeritageApiLog.objects.filter(id=log_id).update(batch_id=batch_id)

            update_log_messages(log_id, "part", f"{submission_count} of {total_parts}")

            models.HeritageApiLog.objects.filter(id=log_id).update(
                resources=serialize(batch_resources)
            )

            part = 1

            for s in range(0, len(batch_resources), MAX_SUBMISSION_SIZE):
                submission_batch = batch_resources[s : s + MAX_SUBMISSION_SIZE]
                resource_instance_ids = [
                    str(resource["resource_instance_id"])
                    for resource in submission_batch
                ]
                resource_instance_ids = ",".join(resource_instance_ids)

                results, status_code = validate_service(
                    resource_object=submission_batch
                )

                if not results:
                    return f"No records generated for {resource_instance_ids}"

                models.HeritageApiData.objects.create(
                    hapi_log_id=log_id,
                    batch_id=batch_id,
                    part=part,
                    validation=serialize(results["response"]),
                    data=serialize(results["data"]),
                )

                status_code, reason, text = batch_submit_service(
                    bearer_token=bearer_token,
                    batch_id=batch_id,
                    records=results["data"]["records"],
                )

                # Append the current batch result to the batch_results list
                batch_results.append(
                    {
                        "status_code": status_code,
                        "batch": str(batch_id),
                        "resources": len(submission_batch),
                        "records": len(results["data"]["records"]),
                        "reason": reason,
                        "text": json.loads(text),
                    }
                )

                processed_resources += len(submission_batch)
                percent_complete = (processed_resources / submission_total_count) * 100
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "message": f"Processing resources {percent_complete:.2f}% ({processed_resources} of {submission_total_count})"
                    },
                )

                check_termination(log_id)

                part += 1

        models.HeritageApiLog.objects.filter(id=log_id).update(
            messages=serialize(batch_results)
        )

        response = batch_finalise_service(bearer_token=bearer_token, batch_id=batch_id)

        if response == 200:
            models.HeritageApiLog.objects.filter(id=log_id).update(
                finish=timezone.now()
            )

        # Return the complete collection of batch results
        return {
            "status": "success",
            "status_code": response,
            "batch_id": batch_id,
            "log_id": str(log_id),
            "count": submission_total_count,
        }

    except Exception as e:
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"Error running H.API upload: {tb_str}")
        if not log_id:
            log_id = models.HeritageApiLog.objects.create(
                start=timezone.now(),
                run_type=run_type,
                parameters={"from": start_date.isoformat()},
                resources=serialize(resources) if resources else None,
            ).id

        models.HeritageApiLog.objects.filter(id=log_id).update(
            exceptions={"Exception": tb_str}
        )

        email_error(
            body="An error occurred during the HAPI upload process:", error=tb_str
        )

        return {"status": "error", "status_code": 500, "error": tb_str}
    finally:
        refresh_materialized_views(with_data=False)


@shared_task(bind=True)
def data_refresh_task(self):
    try:
        start_time = time.time()

        def progress_callback(message):
            self.update_state(state="PROGRESS", meta={"message": message})

        self.update_state(
            state="PROGRESS", meta={"message": "Applying database migrations..."}
        )
        call_command("apply_hapi_database_migration")
        self.update_state(state="PROGRESS", meta={"message": "Refreshing data..."})
        call_command(
            "apply_hapi_database_migration",
            "--with_data",
            progress_callback=progress_callback,
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)
        elapsed_time_formatted = f"{minutes}m {seconds}s"
        return {"status": "success", "message": f"Data refresh completed successfully in {elapsed_time}"}
    except Exception as e:
        return {"status": "failure", "message": str(e)}


def update_log_messages(log_id, key, value):
    # Retrieve the current messages field
    log_entry = models.HeritageApiLog.objects.get(id=log_id)
    current_messages = log_entry.messages or {}

    # Update the messages field with the new key/value pair
    current_messages[key] = value

    # Save the updated messages field back to the database
    log_entry.messages = current_messages
    log_entry.save()
