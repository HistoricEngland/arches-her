import json
from math import ceil
from datetime import datetime
from arches_her.data_access.common import get_resources, get_counts
from celery import shared_task
from arches.app.models.system_settings import settings
from django.db.models import Max, Min
from arches_her.services import (
    authenticate as authenticate_service,
    batch_submit as batch_submit_service,
    batch_create as batch_create_service,
    validate as validate_service,
    batch_finalise as batch_finalise_service
)
from arches_her.models import models
import logging
# from arches_her.models import HeritageApiLog
from django.utils import timezone
from .data_access.common import serialize

# logging.basicConfig(level=logging.DEBUG)


@shared_task
def add(x, y):
    z = x + y
    return z


@shared_task
def hapi_upload(self, *args, **kwargs) -> str:
  
    from arches_her.data_access.common import refresh_materialized_views
    logger = logging.getLogger(__name__)
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

        refresh_materialized_views(with_data=True)

        if not seed:
            max_batch_id = models.HeritageApiLog.objects.aggregate(
                max_batch_id=Max('batch_id')
            )['max_batch_id']

            if max_batch_id:
                latest_timestamp = models.HeritageApiLog.objects.filter(
                    batch_id=max_batch_id
                ).aggregate(
                    batch_id=Max('batch_id'),
                    start=Min('start')
                )

            if latest_timestamp:
                start_date = latest_timestamp['start']

        resources = get_resources(start_date=start_date, seed=seed)

        if not resources:
            models.HeritageApiLog.objects.create(
                start=start_time,
                finish=timezone.now(),
                parameters={"from": start_date.isoformat()},
                run_type=run_type,
                messages={"get_resources": f"No resources found using start date {start_date.isoformat()}"}
            )
            return "No resources found"

        username = settings.HAPI_USERNAME
        password = settings.HAPI_PASSWORD
        max_batch_size = 5000
        max_submission_size = 100

        submission_total_count = len(resources)
        total_parts = ceil(submission_total_count / max_batch_size)
        total_count, published_count = get_counts()
        counts = {
            "total_count": total_count,
            "published_count": published_count,
            "submitted_count": submission_total_count
        }

        bearer_token = authenticate_service(
            username=username, password=password)
        if not bearer_token:
            return "Failed to authenticate with H.API"

        batch_id = batch_create_service(
            bearer_token=bearer_token, counts=counts)
        if not batch_id:
            return "Failed to create new batch"

        submission_count = 0

        for i in range(0, submission_total_count, max_batch_size):
            start_time = timezone.now()
            new_log = models.HeritageApiLog.objects.create(
                start=start_time,
                parameters={"from": start_date.isoformat()},
                run_type=run_type
            )

            log_id = new_log.id
            batch_resources = resources[i:i + max_batch_size]
            submission_count += 1

            models.HeritageApiLog.objects.filter(
                id=log_id).update(totals=counts)

            models.HeritageApiLog.objects.filter(
                id=log_id).update(batch_id=batch_id)

            update_log_messages(log_id, "part", f"{submission_count} of {total_parts}")

            models.HeritageApiLog.objects.filter(
                id=log_id).update(resources=serialize(batch_resources))

            part = 1
            
            for s in range(0, len(batch_resources), max_submission_size):
                submission_batch = batch_resources[s:s + max_submission_size]
                resource_instance_ids = [
                    str(resource['resource_instance_id']) for resource in submission_batch]
                resource_instance_ids = ",".join(resource_instance_ids)

                results, status_code = validate_service(resource_object=submission_batch)

                if not results:
                    return f"No records generated for {resource_instance_ids}"

                models.HeritageApiData.objects.create(
                    hapi_log_id=log_id,
                    batch_id=batch_id,
                    part=part,
                    validation=serialize(results['response']),
                    data=serialize(results['data'])
                )

                status_code, reason, text = batch_submit_service(
                    bearer_token=bearer_token, batch_id=batch_id, records=results['data']['records'])
                
                # Append the current batch result to the batch_results list
                batch_results.append({
                    "status_code": status_code,
                    "batch": batch_id,
                    "resources": len(submission_batch),
                    "records": len(results['data']['records']),
                    "reason": reason,
                    "text": json.loads(text)
                })

                part += 1

        models.HeritageApiLog.objects.filter(id=log_id).update(messages=serialize(batch_results))
        
        batch_finalise_service(
            bearer_token=bearer_token, batch_id=batch_id)

        models.HeritageApiLog.objects.filter(
            id=log_id).update(finish=timezone.now())

        # Return the complete collection of batch results
        return {"status": "completed", "results": batch_results, "task_id": self.request.id}

    except Exception as e:
        logger.error(f"Error running H.API upload: {e.with_traceback}")
        models.HeritageApiLog.objects.filter(
            id=log_id).update(exceptions=e.with_traceback)
        return e.with_traceback
    finally:
        refresh_materialized_views(with_data=False)


def update_log_messages(log_id, key, value):
    # Retrieve the current messages field
    log_entry = models.HeritageApiLog.objects.get(id=log_id)
    current_messages = log_entry.messages or {}

    # Update the messages field with the new key/value pair
    current_messages[key] = value

    # Save the updated messages field back to the database
    log_entry.messages = current_messages
    log_entry.save()
