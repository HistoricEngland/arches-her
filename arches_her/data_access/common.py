from django.db import connection
from typing import List, Optional
import uuid


def call_hapi_get_resources(
    interval_param: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resource_instance_ids: Optional[List[uuid.UUID]] = None
):
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_resources("
        params = []
        if interval_param:
            query += "interval_param := %s, "
            params.append(f"interval '{interval_param}'")

        if start_date and end_date:
            query += "start_date := %s, end_date := %s, "
            params.extend([start_date, end_date])

        if resource_instance_ids:
            resource_ids_str = ','.join([str(rid)
                                        for rid in resource_instance_ids])
            query += "resource_instance_ids := %s, "
            params.append(resource_ids_str)

        # Remove the trailing comma and space, and close the function call
        query = query.rstrip(', ') + ");"
        # Execute the query
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return results

# sql_to_create_hapi_get_resources_function = """
# CREATE OR REPLACE FUNCTION hapi_get_resources(
#     interval_param INTERVAL DEFAULT NULL,
#     start_date TIMESTAMPTZ DEFAULT NULL,
#     end_date TIMESTAMPTZ DEFAULT NULL,
#     resource_instance_ids TEXT DEFAULT NULL
# )
# RETURNS TABLE(
#     resourceinstanceid UUID,
#     resource_type TEXT,
#     resource_name TEXT,
#     primary_reference_number NUMERIC,
#     most_recent_timestamp TIMESTAMPTZ
# )
# LANGUAGE plpgsql
# AS $$
# BEGIN
#     -- Create temporary table for edit_log_cte
#     CREATE TEMP TABLE temp_edit_log_cte AS
#     SELECT DISTINCT ON (e.resourceinstanceid) e.resourceinstanceid::uuid, g.name, e.timestamp
#     FROM edit_log e
#     JOIN graphs g ON e.resourceclassid = g.graphid::text
#     WHERE
#         (resource_instance_ids IS NOT NULL AND e.resourceinstanceid = ANY(string_to_array(resource_instance_ids, ',')::text[]))
#         OR (resource_instance_ids IS NULL AND start_date IS NOT NULL AND end_date IS NOT NULL AND e.timestamp BETWEEN start_date AND end_date)
#         OR (resource_instance_ids IS NULL AND start_date IS NULL AND end_date IS NULL AND (interval_param IS NOT NULL AND e.timestamp >= NOW() - interval_param OR interval_param IS NULL AND e.timestamp >= '0001-01-01'))  -- Only consider logs from the specified interval or from the beginning of time
#       AND e.resourceinstanceid NOT IN (
#         SELECT e2.resourceinstanceid
#         FROM edit_log e2
#         WHERE e2.edittype = 'delete'
#         AND ((resource_instance_ids IS NOT NULL AND e2.resourceinstanceid = ANY(string_to_array(resource_instance_ids, ',')::text[]))
#              OR (resource_instance_ids IS NULL AND start_date IS NOT NULL AND end_date IS NOT NULL AND e2.timestamp BETWEEN start_date AND end_date)
#              OR (resource_instance_ids IS NULL AND start_date IS NULL AND end_date IS NULL AND (interval_param IS NOT NULL AND e2.timestamp >= NOW() - interval_param OR interval_param IS NULL AND e2.timestamp >= '0001-01-01')))
#       )
#       AND e.edittype IN ('create', 'bulk_create', 'tile edit', 'tile delete', 'tile create')
#       AND g.name in ('Monument', 'Maritime Vessel', 'Historic Aircraft')
#     ORDER BY e.resourceinstanceid, e.timestamp DESC;

#     -- Create temporary table for resource_names
#     CREATE TEMP TABLE temp_resource_names AS
#     SELECT mn.resourceinstanceid, mn.monument_name AS resource_name
#     FROM monument.monument_names mn
#     UNION ALL
#     SELECT ha.resourceinstanceid, ha.name AS resource_name
#     FROM historic_aircraft.names ha
#     UNION ALL
#     SELECT mv.resourceinstanceid, mv.name AS resource_name
#     FROM maritime_vessel.names mv;

#     -- Create temporary table for system_reference_numbers
#     CREATE TEMP TABLE temp_system_reference_numbers AS
#     SELECT ms.resourceinstanceid, ms.primary_reference_number
#     FROM monument.system_reference_numbers ms
#     UNION ALL
#     SELECT has.resourceinstanceid, has.primary_reference_number
#     FROM historic_aircraft.system_reference_numbers has
#     UNION ALL
#     SELECT mvs.resourceinstanceid, mvs.primary_reference_number
#     FROM maritime_vessel.system_reference_numbers mvs;

#     -- Main query using temporary tables
#     RETURN QUERY
#     SELECT el.resourceinstanceid, el.name AS resource_type, rn.resource_name, srn.primary_reference_number, el.timestamp AS most_recent_timestamp
#     FROM temp_edit_log_cte el
#     INNER JOIN temp_resource_names rn ON el.resourceinstanceid = rn.resourceinstanceid
#     INNER JOIN temp_system_reference_numbers srn ON el.resourceinstanceid = srn.resourceinstanceid;

#     -- Drop temporary tables
#     DROP TABLE IF EXISTS temp_edit_log_cte;
#     DROP TABLE IF EXISTS temp_system_reference_numbers;
#     DROP TABLE IF EXISTS temp_resource_names;

# END;
# $$;
# """

# -- Get resources that have been created/updated in the last day. For the last week, use '1 week', or '7 days' etc.
# SELECT * FROM hapi_get_resources(interval_param := interval '1 day');

# -- Get the specific resource(s), irrespective of created/update date/time
# SELECT * FROM hapi_get_resources(resource_instance_ids := '28d72e6d-272a-4556-99dc-eef27a680acc,a57feb62-6b26-45cc-91a6-3cc4884592c5,bdc4e3e9-d208-42e7-8162-4e9f62b0b124');

# -- Get resources that were created/last updated between start_date and end_date
# SELECT * FROM hapi_get_resources(start_date := '2024-10-24 20:28:32.826939+01', end_date :=  '2024-10-25 19:38:37.746652+01')

# -- Get all resources
# select * from hapi_get_resources();
