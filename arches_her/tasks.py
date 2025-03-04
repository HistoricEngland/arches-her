from datetime import datetime

import json
from arches_her.data_access.common import get_resources
from celery import shared_task
from arches.app.models.system_settings import settings
# from django.db.models import Max, F, Value
# from django.db.models.functions import Coalesce
from arches_her.services import (
    authenticate as authenticate_service,
    batch_submit as batch_submit_service,
    batch_create as batch_create_service,
    validate as validate_service,
    generate as generate_service,
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
def hapi_upload(*args, **kwargs) -> str:
  
    from arches_her.data_access.common import refresh_materialized_views
    logger = logging.getLogger(__name__)
    start_date = datetime(1, 1, 1)
  
    run_type = kwargs.get("run_type", models.HeritageApiLog.AUTOMATIC)
    if run_type not in [models.HeritageApiLog.AUTOMATIC, models.HeritageApiLog.MANUAL]:
        raise ValueError(f"Invalid run type: {run_type}")
    
    seed = kwargs.get("seed", False) or False
    if seed not in [True, False]:
        raise ValueError(f"Invalid seed value: {seed}")

    try:
        start_time = timezone.now()

        # refresh_materialized_views(with_data=True)

        if not seed:
            latest_timestamp = models.HeritageApiLog.objects.filter(
                finish__isnull=False
            ).order_by('-start').values('start').first()

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

        for i in range(0, len(resources), max_batch_size):
            start_time = timezone.now()
            new_log = models.HeritageApiLog.objects.create(
                start=start_time,
                parameters={"from": start_date.isoformat()},
                run_type=run_type
            )

            log_id = new_log.id
            batch_resources = resources[i:i + max_batch_size]

            bearer_token = authenticate_service(
                username=username, password=password)
            if not bearer_token:
                return "Failed to authenticate with H.API"

            update_log_messages(log_id, "bearer_token", bearer_token)

            total_count = len(batch_resources)

            # TODO Get the counts of the total and published records
            counts = {
                "total_count": 0,
                "published_count": 0,
                "submitted_count": total_count
            }

            models.HeritageApiLog.objects.filter(id=log_id).update(totals=counts)

            batch_id = batch_create_service(
                bearer_token=bearer_token, counts=counts)
            if not batch_id:
                return "Failed to create new batch"

            models.HeritageApiLog.objects.filter(
                id=log_id).update(batch_id=batch_id)

            update_log_messages(log_id, "batch_id", batch_id)

            models.HeritageApiLog.objects.filter(
                id=log_id).update(resources=serialize(batch_resources))

            part = 1
            
            for i in range(0, len(batch_resources), max_submission_size):
                submission_batch = batch_resources[i:i + max_submission_size]
            
                resource_instance_ids = [
                    str(resource['resource_instance_id']) for resource in submission_batch]
                resource_instance_ids = ",".join(resource_instance_ids)

                # results[0]['data'] is a string - need to convert it back in to a JSON object
                results = validate_service(resource_object=submission_batch) # response, data

                if not results:
                    return f"No records generated for {resource_instance_ids}"

                # data = results[0]['data']

                # validation = results[0]['response']
                # validation = serialize(validation)

                models.HeritageApiData.objects.create(
                    hapi_log_id=log_id,
                    batch_id=batch_id,
                    part=part,
                    validation=serialize(results[0]['response']),
                    data=serialize(results[0]['data'])
                )

                # records = json.loads(results[0]['data'])
                
                status_code, reason, text = batch_submit_service(
                    bearer_token=bearer_token, batch_id=batch_id, records=results[0]['data']['records'])
                
                # text = json.loads(text)
                # message = {"part": part, "result": reason, "status_code": status_code, **text}

                # messages = models.HeritageApiLog.objects.filter(
                #     id=log_id).values('messages').first()
                
                # # messages is an array
                # if not messages['messages']:
                #     messages = []
                # else:
                #     messages = messages['messages']
                # # messages = messages['messages']
                # # messages = serialize(messages)
                # # message = {**messages, **message}
                # messages.append(message)
                
                # models.HeritageApiLog.objects.filter(
                #     id=log_id).update(messages=serialize(messages))

                part += 1

        if True:
            models.HeritageApiLog.objects.filter(
                id=log_id).update(finish=timezone.now())

        return f"{'Success' if True else 'Failure'}, status code: {status_code}, resources: {len(resources)}, records: {len(results)}"

    except Exception as e:
        logger.error(f"Error running H.API upload: {e.with_traceback}")
        models.HeritageApiLog.objects.filter(
            id=log_id).update(exceptions=e.with_traceback)
        return e.with_traceback
    finally:
        pass
        # refresh_materialized_views(with_data=False)


def update_log_messages(log_id, key, value):
    return
    # Retrieve the current messages field
    log_entry = models.HeritageApiLog.objects.get(id=log_id)
    current_messages = log_entry.messages or {}

    # Update the messages field with the new key/value pair
    current_messages[key] = value

    # Save the updated messages field back to the database
    log_entry.messages = current_messages
    log_entry.save()
