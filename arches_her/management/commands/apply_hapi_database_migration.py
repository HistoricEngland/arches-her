import re
import time
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Apply standalone migration for H.API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with_data',
            action='store_true',
            help='Refresh materialized views WITH DATA',
        )
        parser.add_argument(
            '--with_no_data',
            action='store_true',
            help='Refresh materialized views WITH NO DATA',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete H.API schema',
        )

    def handle(self, *args, **kwargs):
        with_data = kwargs.get('with_data', False)
        with_no_data = kwargs.get('with_no_data', False)
        delete = kwargs.get('delete', False)

        if with_data:
            refresh_option = 'WITH DATA'
        elif with_no_data:
            refresh_option = 'WITH NO DATA'
        else:
            refresh_option = None

        if refresh_option:
            try:
                self.refresh_materialized_views(
                    connection.cursor(), refresh_option, use_tqdm=True)
                self.stdout.write(self.style.SUCCESS(
                    'Materialized views refreshed ' + refresh_option))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Error refreshing materialized views {refresh_option} {e}'))
            return

        if delete:
            try:
                self.delete_schema(connection.cursor())
                self.stdout.write(self.style.SUCCESS('Schema deleted'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Error deleting schema {e}'))
            return

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DROP SCHEMA IF EXISTS hapi CASCADE;
                    """)
                    cursor.execute("""
                        CREATE SCHEMA hapi
                            AUTHORIZATION postgres;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.associated_resources_mv
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            amaa.resourceinstanceid,
                            jsonb_array_elements(amaa.monument_area_or_artefact) ->> 'resourceId'::text AS associated_resource,
                            amaa.association_type
                        FROM 
                            maritime_vessel.associated_monuments_areas_and_artefacts amaa
                        UNION ALL
                        SELECT 
                            amaa.resourceinstanceid,
                            jsonb_array_elements(amaa.associated_monument_area_or_artefact) ->> 'resourceId'::text AS associated_resource,
                            amaa.association_type
                        FROM 
                            monument.associated_monuments_areas_and_artefacts amaa
                        UNION ALL
                        SELECT 
                            amaa.resourceinstanceid,
                            jsonb_array_elements(amaa.associated_monument_area_or_artefact) ->> 'resourceId'::text AS associated_resource,
                            amaa.association_type
                        FROM 
                            historic_aircraft.associated_monuments_areas_and_artefacts amaa
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.associated_resources_mv
                        OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_associated_resources_mv_resourceinstanceid
                        ON hapi.associated_resources_mv USING btree
                        (resourceinstanceid)
                        TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.complex_geometry
                        TABLESPACE pg_default
                        AS
                        SELECT geometry.resourceinstanceid,
                            "left"("substring"(st_astext(geometry.geospatial_coordinates), 1, 20), "position"("substring"(st_astext(geometry.geospatial_coordinates), 1, 20), '('::text) - 1) AS "SpatialFeatureType",
                            st_astext(geometry.geospatial_coordinates, 6) AS "SpatialFeatureGeometry"
                        FROM monument.geometry
                        UNION ALL
                        SELECT geometry.resourceinstanceid,
                            "left"("substring"(st_astext(geometry.geospatial_coordinates), 1, 20), "position"("substring"(st_astext(geometry.geospatial_coordinates), 1, 20), '('::text) - 1) AS "SpatialFeatureType",
                            st_astext(geometry.geospatial_coordinates, 6) AS "SpatialFeatureGeometry"
                        FROM maritime_vessel.geometry
                        UNION ALL
                        SELECT geometry.resourceinstanceid,
                            "left"("substring"(st_astext(geometry.geospatial_coordinates), 1, 20), "position"("substring"(st_astext(geometry.geospatial_coordinates), 1, 20), '('::text) - 1) AS "SpatialFeatureType",
                            st_astext(geometry.geospatial_coordinates, 6) AS "SpatialFeatureGeometry"
                        FROM historic_aircraft.geometry
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.complex_geometry
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX complex_geometry_resourceinstanceid
                            ON hapi.complex_geometry USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.descriptions
                        TABLESPACE pg_default
                        AS
                        WITH descriptions AS
                        (
                            SELECT d.resourceinstanceid,
                                d.description,
                                d.description_type
                            FROM monument.descriptions d
                            UNION ALL
                            SELECT d.resourceinstanceid,
                                d.description,
                                d.description_type
                            FROM historic_aircraft.descriptions d
                            UNION ALL
                            SELECT d.resourceinstanceid,
                                d.description,
                                d.description_type
                            FROM maritime_vessel.descriptions d
                        )
                        SELECT 
                            d.resourceinstanceid,
                            d.description,
                            v.value as type
                        FROM descriptions d
                        JOIN public.values v ON d.description_type = v.valueid
                        WHERE lower(v.value) = ANY (ARRAY['full', 'summary'])
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.descriptions
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX descriptions_resourceinstanceid
                            ON hapi.descriptions USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.images_mv
                        TABLESPACE pg_default
                        AS
                        WITH images AS (
                                SELECT images.resourceinstanceid,
                                    images.caption,
                                    images.copyright_type,
                                    (images.images -> 0) ->> 'url'::text AS url
                                FROM monument.images
                                UNION ALL
                                SELECT images.resourceinstanceid,
                                    images.caption_note,
                                    images.copyright_type,
                                    (images.images -> 0) ->> 'url'::text AS url
                                FROM maritime_vessel.images
                                UNION ALL
                                SELECT images.resourceinstanceid,
                                    images.caption_note,
                                    images.copyright_type,
                                    (images.images -> 0) ->> 'url'::text AS url
                                FROM historic_aircraft.images
                                )
                        SELECT i.resourceinstanceid,
                            i.caption,
                            v.value AS copyright,
                            i.url
                        FROM images i
                            LEFT JOIN "values" v ON i.copyright_type = v.valueid
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.images_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX images_mv_resourceinstanceid
                            ON hapi.images_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.monument_and_area_primary_reference_numbers_mv
                        TABLESPACE pg_default
                        AS
                        SELECT srn.resourceinstanceid,
                            srn.primary_reference_number
                        FROM monument.system_reference_numbers srn
                        UNION ALL
                        SELECT srn.resourceinstanceid,
                            srn.primary_reference_number
                        FROM area.system_reference_numbers srn
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.monument_and_area_primary_reference_numbers_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX monument_and_area_prn_resourceinstanceid
                            ON hapi.monument_and_area_primary_reference_numbers_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.bibliographic_source_name_mv AS
                        SELECT
                            resourceinstanceid,
                            bibliographic_source_name
                        FROM bibliographic_source.bibliographic_source_names;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_bibliographic_source_name
                        ON hapi.bibliographic_source_name_mv(resourceinstanceid);
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.bibliographic_source_creation_mv AS
                        SELECT
                            resourceinstanceid,
                            statement_of_responsibility 
                        FROM bibliographic_source.bibliographic_source_creation
                        WHERE statement_of_responsibility IS NOT NULL;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_bibliographic_source_creation
                        ON hapi.bibliographic_source_creation_mv(resourceinstanceid);
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.bibliographic_source_citation_mv AS
                        SELECT
                            resourceinstanceid, 
                            ((bibliographic_source_citation->0)->>'resourceId'::text)::uuid as bibliographic_source_citation, 
                            source_number_value, 
                            page_s_, 
                            figs_, 
                            plate_s_   
                        FROM monument.bibliographic_source_citation
                        UNION ALL
                        SELECT
                            resourceinstanceid, 
                            ((bibliographic_source_citation->0)->>'resourceId'::text)::uuid as bibliographic_source_citation, 
                            source_number_value, 
                            page_s_, 
                            figs_, 
                            plate_s_   
                        FROM historic_aircraft.bibliographic_source_citation
                        UNION ALL
                        SELECT
                            resourceinstanceid, 
                            ((bibliographic_source_citation->0)->>'resourceId'::text)::uuid as bibliographic_source_citation, 
                            source_number_value, 
                            page_s_, 
                            figs_, 
                            plate_s_   
                        FROM maritime_vessel.bibliographic_source_citation;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_bibliographic_source_citation
                        ON hapi.bibliographic_source_citation_mv(resourceinstanceid);
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.bibliographic_source_publication_mv AS
                        SELECT
                            resourceinstanceid,
                            date_of_publication
                        FROM bibliographic_source.publication;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_bibliographic_source_publication
                        ON hapi.bibliographic_source_publication_mv(resourceinstanceid);
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.bibliographic_source_url_mv AS
                        SELECT
                            resourceinstanceid,
                            url ->> 'url'::text url
                        FROM bibliographic_source.external_cross_references
                        WHERE url ->> 'url' IS NOT NULL;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_bibliographic_source_url
                        ON hapi.bibliographic_source_url_mv(resourceinstanceid);
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.monument_sources_mv AS
                        SELECT bsc.resourceinstanceid,
                            bsn.bibliographic_source_name AS information_source_title,
                            ( SELECT jsonb_agg(statement_of_responsibility) AS jsonb_agg
                                FROM hapi.bibliographic_source_creation_mv bscr
                                WHERE bsc.bibliographic_source_citation = bscr.resourceinstanceid) AS statement_of_authority,
                            bsc.source_number_value AS source_no,
                            jsonb_strip_nulls(jsonb_build_object('pages', bsc.page_s_, 'figures', bsc.figs_, 'plates', bsc.plate_s_)) AS source_reference,
                            bsp.date_of_publication AS date_of_origination,
                            CASE
                                WHEN bsu.url LIKE '%doi.org%' THEN bsu.url
                                ELSE NULL
                            END AS source_digital_object_identifier,
                            CASE
                                WHEN bsu.url NOT LIKE '%doi.org%' THEN bsu.url
                                ELSE NULL
                            END AS source_url
                        FROM hapi.bibliographic_source_citation_mv bsc
                        LEFT JOIN hapi.bibliographic_source_name_mv bsn ON bsc.bibliographic_source_citation = bsn.resourceinstanceid
                        LEFT JOIN hapi.bibliographic_source_url_mv bsu ON bsc.bibliographic_source_citation = bsu.resourceinstanceid
                        LEFT JOIN hapi.bibliographic_source_publication_mv bsp ON bsc.bibliographic_source_citation = bsp.resourceinstanceid;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_monument_sources
                        ON hapi.monument_sources_mv(resourceinstanceid);
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.other_statuses_mv
                        TABLESPACE pg_default
                        AS
                        WITH other_statuses AS (
                                SELECT ecr.resourceinstanceid,
                                    ecr.external_cross_reference_source,
                                    ecr.external_cross_reference,
                                    ecr.external_cross_reference_description,
                                    ecr.url ->> 'url'::text AS url
                                FROM monument.external_cross_references ecr
                                UNION ALL
                                SELECT ecr.resourceinstanceid,
                                    ecr.external_cross_reference_source,
                                    ecr.external_cross_reference,
                                    ecr.external_cross_reference_description,
                                    ecr.url ->> 'url'::text AS url
                                FROM maritime_vessel.external_cross_references ecr
                                UNION ALL
                                SELECT ecr.resourceinstanceid,
                                    ecr.external_cross_reference_source,
                                    ecr.external_cross_reference,
                                    ecr.external_cross_reference_description,
                                    ecr.url ->> 'url'::text AS url
                                FROM historic_aircraft.external_cross_references ecr
                                )
                        SELECT os.resourceinstanceid,
                            v.value AS external_cross_reference_source,
                            os.external_cross_reference,
                            os.external_cross_reference_description,
                            os.url
                        FROM other_statuses os
                            LEFT JOIN "values" v ON os.external_cross_reference_source = v.valueid
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.other_statuses_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX os_resourceinstanceid
                            ON hapi.other_statuses_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.point_geometry
                        TABLESPACE pg_default
                        AS
                        SELECT resourceinstanceid,
                            round(st_x(st_centroid(st_convexhull(geospatial_coordinates)))::numeric, 6) AS x_coordinate,
                            round(st_y(st_centroid(st_convexhull(geospatial_coordinates)))::numeric, 6) AS y_coordinate
                        FROM monument.geometry
                        UNION ALL
                        SELECT resourceinstanceid,
                            round(st_x(st_centroid(st_convexhull(geospatial_coordinates)))::numeric, 6) AS x_coordinate,
                            round(st_y(st_centroid(st_convexhull(geospatial_coordinates)))::numeric, 6) AS y_coordinate
                        FROM maritime_vessel.geometry
                        UNION ALL
                        SELECT resourceinstanceid,
                            round(st_x(st_centroid(st_convexhull(geospatial_coordinates)))::numeric, 6) AS x_coordinate,
                            round(st_y(st_centroid(st_convexhull(geospatial_coordinates)))::numeric, 6) AS y_coordinate
                        FROM historic_aircraft.geometry
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.point_geometry
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX point_geometry_resourceinstanceid
                            ON hapi.point_geometry USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.protected_statuses_mv
                        TABLESPACE pg_default
                        AS
                        WITH designation_or_protection_type AS (
                                SELECT dpa.resourceinstanceid,
                                    dpa.designation_or_protection_type
                                FROM monument.designation_and_protection_assignment dpa
                                WHERE dpa.designation_or_protection_type IS NOT NULL
                                UNION ALL
                                SELECT dpa.resourceinstanceid,
                                    dpa.designation_or_protection_type
                                FROM maritime_vessel.designation_and_protection_assignment dpa
                                WHERE dpa.designation_or_protection_type IS NOT NULL
                                UNION ALL
                                SELECT dpa.resourceinstanceid,
                                    dpa.designation_or_protection_type
                                FROM historic_aircraft.designation_and_protection_assignment dpa
                                WHERE dpa.designation_or_protection_type IS NOT NULL
                                )
                        SELECT dpt.resourceinstanceid,
                            array_agg(v.value) AS protectedstatuses
                        FROM designation_or_protection_type dpt
                            LEFT JOIN "values" v ON dpt.designation_or_protection_type = v.valueid
                        GROUP BY dpt.resourceinstanceid
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.protected_statuses_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX ps_resourceinstanceid
                            ON hapi.protected_statuses_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    # If there is more than one Primary activity name, none are returned
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_activity_names
                        TABLESPACE pg_default
                        AS
                        WITH primary_names AS (
                                SELECT aan.resourceinstanceid AS resource_id,
                                    aan.activity_name AS name,
                                    count(*) OVER (PARTITION BY aan.resourceinstanceid) AS primary_count,
                                    row_number() OVER (PARTITION BY aan.resourceinstanceid ORDER BY aan.activity_name) AS rn
                                FROM activity.activity_names aan
                                    JOIN "values" v ON aan.activity_name_use_type = v.valueid
                                WHERE v.value = 'Primary'::text
                                )
                        SELECT primary_names.resource_id,
                            primary_names.name
                        FROM primary_names
                        WHERE primary_names.primary_count = 1 AND primary_names.rn = 1
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events_activity_names
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX rean_resource_id
                            ON hapi.related_events_activity_names USING btree
                            (resource_id)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_associated_activities
                        TABLESPACE pg_default
                        AS
                            SELECT resourceinstanceid,
                                jsonb_array_elements(associated_activities) AS activity
                            FROM monument.associated_activities
                        UNION ALL
                            SELECT resourceinstanceid,
                                jsonb_array_elements(associated_activities) AS activity
                            FROM maritime_vessel.associated_activities
                        UNION ALL
                            SELECT resourceinstanceid,
                                jsonb_array_elements(associated_activities) AS activity
                            FROM historic_aircraft.associated_activities
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events_associated_activities
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX reaa_resourceinstanceid
                            ON hapi.related_events_associated_activities USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_filtered_descriptions
                        TABLESPACE pg_default
                        AS
                        SELECT ad.resourceinstanceid,
                            ad.activity_description,
                            v.value,
                            row_number() OVER (PARTITION BY ad.resourceinstanceid, v.value ORDER BY ad.activity_description_type) AS rn
                        FROM activity.activity_descriptions ad
                            JOIN "values" v ON ad.activity_description_type = v.valueid
                        WHERE v.value = ANY (ARRAY['Full'::text, 'Summary'::text])
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events_filtered_descriptions
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX refd_resourceinstanceid
                            ON hapi.related_events_filtered_descriptions USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_descriptions
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            fd.resourceinstanceid AS resource_id,
                            fd.activity_description AS description
                        FROM 
                            hapi.related_events_filtered_descriptions fd
                        WHERE 
                            (fd.value = 'Summary'::text AND fd.rn = 1) 
                            OR 
                            (fd.value = 'Full'::text AND fd.rn = 1 AND NOT EXISTS (
                                SELECT 1
                                FROM hapi.related_events_filtered_descriptions fd_sub
                                WHERE fd_sub.value = 'Summary'::text 
                                AND fd_sub.resourceinstanceid = fd.resourceinstanceid
                            ))
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE IF EXISTS hapi.related_events_descriptions
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX red_resource_id
                            ON hapi.related_events_descriptions USING btree
                            (resource_id)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_activity_types
                        TABLESPACE pg_default
                        AS
                        SELECT (reaa.activity ->> 'resourceId'::text)::uuid AS resource_id,
                            unnest(activity_type.activity_type) AS type_id
                        FROM hapi.related_events_associated_activities reaa
                            JOIN activity.activity_type ON ((reaa.activity ->> 'resourceId'::text)::uuid) = activity_type.resourceinstanceid
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events_activity_types
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX reat_resource_id
                            ON hapi.related_events_activity_types USING btree
                            (resource_id)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_primary_reference_numbers
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            system_reference_numbers.resourceinstanceid AS resource_id,
                            system_reference_numbers.primary_reference_number
                        FROM 
                            activity.system_reference_numbers
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events_primary_reference_numbers
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX reprn_resource_id
                            ON hapi.related_events_primary_reference_numbers USING btree
                            (resource_id)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events_type_names
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            related_events_activity_types.resource_id,
                            array_agg("values".value) AS types
                        FROM 
                            hapi.related_events_activity_types
                        JOIN 
                            "values" ON related_events_activity_types.type_id = "values".valueid
                        GROUP BY 
                            related_events_activity_types.resource_id
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events_type_names
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX retn_resource_id
                            ON hapi.related_events_type_names USING btree
                            (resource_id)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.resource_names_mv
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            mn.resourceinstanceid,
                            mn.monument_name AS resource_name
                        FROM 
                            monument.monument_names mn
                        UNION ALL
                        SELECT 
                            ha.resourceinstanceid,
                            ha.name AS resource_name
                        FROM 
                            historic_aircraft.names ha
                        UNION ALL
                        SELECT 
                            mv.resourceinstanceid,
                            mv.name AS resource_name
                        FROM 
                            maritime_vessel.names mv
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.resource_names_mv
                        OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX resource_names_resourceinstanceid
                        ON hapi.resource_names_mv USING btree
                        (resourceinstanceid)
                        TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.system_reference_numbers_mv
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            ms.resourceinstanceid,
                            ms.primary_reference_number
                        FROM 
                            monument.system_reference_numbers ms
                        UNION ALL
                        SELECT 
                            has.resourceinstanceid,
                            has.primary_reference_number
                        FROM 
                            historic_aircraft.system_reference_numbers has
                        UNION ALL
                        SELECT 
                            mvs.resourceinstanceid,
                            mvs.primary_reference_number
                        FROM 
                            maritime_vessel.system_reference_numbers mvs
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.system_reference_numbers_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX system_reference_numbers_resourceinstanceid
                            ON hapi.system_reference_numbers_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.associated_monuments_areas_and_artefacts_mv
                        TABLESPACE pg_default
                        AS
                        SELECT amaa.resourceinstanceid,
                            (jsonb_array_elements(amaa.associated_monument_area_or_artefact) ->> 'resourceId'::text)::uuid AS associated_resourceid
                        FROM monument.associated_monuments_areas_and_artefacts amaa
                        UNION ALL
                        SELECT amaa.resourceinstanceid,
                            (jsonb_array_elements(amaa.monument_area_or_artefact) ->> 'resourceId'::text)::uuid AS associated_resourceid
                        FROM maritime_vessel.associated_monuments_areas_and_artefacts amaa
                        UNION ALL
                        SELECT amaa.resourceinstanceid,
                            (jsonb_array_elements(amaa.associated_monument_area_or_artefact) ->> 'resourceId'::text)::uuid AS associated_resourceid
                        FROM historic_aircraft.associated_monuments_areas_and_artefacts amaa
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.associated_monuments_areas_and_artefacts_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_amaa_resourceinstanceid
                            ON hapi.associated_monuments_areas_and_artefacts_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.resources_mv
                        TABLESPACE pg_default
                        AS
                        WITH edit_log_cte AS (
                            SELECT DISTINCT ON (e.resourceinstanceid) 
                                e.resourceinstanceid::uuid AS resourceinstanceid,
                                g.name,
                                e."timestamp"
                            FROM 
                                edit_log e
                            JOIN 
                                graphs g ON e.resourceclassid = g.graphid::text
                            WHERE 
                                e."timestamp" >= '0001-01-01 00:00:00+00'::timestamp with time zone 
                                AND NOT (e.resourceinstanceid IN (
                                    SELECT e2.resourceinstanceid
                                    FROM edit_log e2
                                    WHERE e2.edittype = 'delete'::text
                                )) 
                                AND NOT (e.resourceinstanceid IN (
                                    SELECT resource_id::text AS resource_id
                                    FROM hapi_exclusion
                                )) 
                                AND (e.edittype = ANY (ARRAY['create'::text, 'bulk_create'::text, 'tile edit'::text, 'tile delete'::text, 'tile create'::text])) 
                                AND (g.name = ANY (ARRAY['Monument'::text, 'Maritime Vessel'::text, 'Historic Aircraft'::text]))
                            ORDER BY 
                                e.resourceinstanceid, e."timestamp" DESC
                        )
                        SELECT 
                            el.resourceinstanceid,
                            el.name AS resource_type,
                            rn.resource_name,
                            srn.primary_reference_number,
                            el."timestamp" AS most_recent_timestamp
                        FROM 
                            edit_log_cte el
                        LEFT JOIN 
                            hapi.resource_names_mv rn ON el.resourceinstanceid = rn.resourceinstanceid
                        LEFT JOIN 
                            hapi.system_reference_numbers_mv srn ON el.resourceinstanceid = srn.resourceinstanceid
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.resources_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX resources_most_recent_timestamp
                            ON hapi.resources_mv USING btree
                            (most_recent_timestamp)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE INDEX resources_resourceinstanceid
                            ON hapi.resources_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.period_names_mv
                        TABLESPACE pg_default
                        AS
                        SELECT resourceinstanceid,
                            period_name
                        FROM period.period_names
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.period_names_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_period_names
                            ON hapi.period_names_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.historic_aircraft_mv
                        TABLESPACE pg_default
                        AS
                        WITH associated_historic_aircraft AS
                        (
                            SELECT
                                amaa.resourceinstanceid,
                                amaa.associated_resourceid
                            FROM hapi.associated_monuments_areas_and_artefacts_mv amaa
                            JOIN public.resource_instances ri ON amaa.associated_resourceId = ri.resourceinstanceid
                            JOIN public.graphs g ON ri.graphid = g.graphid
                            WHERE g.name = 'Historic Aircraft'
                        ),
                        aircraft_data AS
                        (
                            SELECT
                                aha.resourceinstanceid,
                                acp.aircraft_type,
                                acp.start_date AS from_date,
                                acp.end_date AS to_date,
                                acp.display_date,
                                ARRAY(
                                    SELECT (elem->>'resourceId')::uuid
                                    FROM jsonb_array_elements(acp.period) AS elem
                                ) AS cultural_periods,
                                acp.main_construction_material
                            FROM associated_historic_aircraft aha 
                            LEFT JOIN historic_aircraft.aircraft_construction_phase acp ON aha.associated_resourceId = acp.resourceinstanceid 
                        )
                        SELECT
                            ad.resourceinstanceid,
                            (
                                SELECT v.value
                                FROM public.values v
                                WHERE v.valueid = ad.aircraft_type
                            ) AS aircraft_type,
                            from_date,
                            to_date,
                            display_date,
                            ARRAY(
                                SELECT pn.period_name
                                FROM unnest(ad.cultural_periods) AS uuid
                                LEFT JOIN hapi.period_names_mv pn ON uuid = pn.resourceinstanceid
                            ) AS cultural_periods,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(ad.main_construction_material) AS uuid
                                LEFT JOIN public.values v ON uuid = v.valueid
                            ) AS materials
                        FROM aircraft_data ad
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.historic_aircraft_mv
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX historic_aircraft_resourceinstanceid
                            ON hapi.historic_aircraft_mv USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.maritime_craft AS
                        WITH associated_maritime_vessels AS
                        (
                            SELECT
                                amaa.resourceinstanceid,
                                amaa.associated_resourceid
                            FROM hapi.associated_monuments_areas_and_artefacts_mv amaa
                            JOIN public.resource_instances ri ON amaa.associated_resourceId = ri.resourceinstanceid
                            JOIN public.graphs g ON ri.graphid = g.graphid
                            WHERE g.name = 'Maritime Vessel'
                        ),
                        vessel_data AS
                        (
                            SELECT
                                amv.resourceinstanceid,
                                mvcp.maritime_vessel_type,
                                mvcp.construction_phase_start_date AS from_date,
                                mvcp.construction_phase_end_date AS to_date,
                                mvcp.construction_phase_display_date AS display_date,
                                ARRAY(
                                    SELECT (elem->>'resourceId')::uuid
                                    FROM jsonb_array_elements(mvcp.cultural_period) AS elem
                                ) AS cultural_periods,
                                mvcp.main_construction_material,
                                mvcp.covering_material
                            FROM associated_maritime_vessels amv 
                            LEFT JOIN maritime_vessel.construction_phases mvcp ON amv.associated_resourceId = mvcp.resourceinstanceid 
                        )
                        SELECT
                            vd.resourceinstanceid,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(vd.maritime_vessel_type) AS uuid
                                LEFT JOIN public.values v ON uuid = v.valueid
                            ) AS maritime_vessel_type,
                            vd.from_date,
                            vd.to_date,
                            vd.display_date,
                            ARRAY(
                                SELECT pn.period_name
                                FROM unnest(vd.cultural_periods) AS uuid
                                LEFT JOIN hapi.period_names_mv pn ON uuid = pn.resourceinstanceid
                            ) AS cultural_periods,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(vd.main_construction_material) AS uuid
                                LEFT JOIN public.values v ON uuid = v.valueid
                            ) AS main_construction_materials,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(vd.covering_material) AS uuid
                                LEFT JOIN public.values v ON uuid = v.valueid
                            ) AS covering_materials
                        FROM vessel_data vd
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.maritime_craft
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX maritime_craft_resourceinstanceid
                            ON hapi.maritime_craft USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.monument_dated_types
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            cp.resourceinstanceid,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.monument_type) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS monument_types,
                            cp.construction_phase_start_date AS start_date,
                            cp.construction_phase_end_date AS end_date,
                            cp.construction_phase_display_date AS display_date,
                            ARRAY(
                                SELECT pn.period_name
                                FROM unnest(
                                    (SELECT array_agg((elem.value ->> 'resourceId'::text)::uuid) AS array_agg
                                    FROM jsonb_array_elements(cp.cultural_period) elem(value))
                                ) cp_1(cp)
                                JOIN hapi.period_names_mv pn ON cp_1.cp = pn.resourceinstanceid
                            ) AS periods,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.main_construction_material) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                                UNION ALL
                                SELECT v.value
                                FROM unnest(cp.covering_material) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS materials,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.construction_phase_evidence_type) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS evidences
                        FROM monument.construction_phases cp
                        UNION ALL
                        SELECT 
                            cp.resourceinstanceid,
                            ARRAY(
                                SELECT v.value
                                FROM "values" v
                                WHERE cp.aircraft_type = v.valueid
                            ) AS monument_types,
                            to_char(cp.start_date, 'YYYY-MM-DD'::text) AS start_date,
                            to_char(cp.end_date, 'YYYY-MM-DD'::text) AS end_date,
                            cp.display_date,
                            ARRAY(
                                SELECT pn.period_name
                                FROM unnest(
                                    (SELECT array_agg((elem.value ->> 'resourceId'::text)::uuid) AS array_agg
                                    FROM jsonb_array_elements(cp.period) elem(value))
                                ) cp_1(cp)
                                JOIN hapi.period_names_mv pn ON cp_1.cp = pn.resourceinstanceid
                            ) AS periods,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.main_construction_material) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS materials,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.phase_evidence_type) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS evidences
                        FROM historic_aircraft.aircraft_construction_phase cp
                        UNION ALL
                        SELECT 
                            cp.resourceinstanceid,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.maritime_vessel_type) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS monument_types,
                            cp.construction_phase_start_date AS start_date,
                            cp.construction_phase_end_date AS end_date,
                            cp.construction_phase_display_date AS display_date,
                            ARRAY(
                                SELECT pn.period_name
                                FROM unnest(
                                    (SELECT array_agg((elem.value ->> 'resourceId'::text)::uuid) AS array_agg
                                    FROM jsonb_array_elements(cp.cultural_period) elem(value))
                                ) cp_1(cp)
                                JOIN hapi.period_names_mv pn ON cp_1.cp = pn.resourceinstanceid
                            ) AS periods,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.main_construction_material) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                                UNION ALL
                                SELECT v.value
                                FROM unnest(cp.covering_material) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS materials,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(cp.construction_phase_evidence_type) mt(mt)
                                JOIN "values" v ON mt.mt = v.valueid
                            ) AS evidences
                        FROM maritime_vessel.construction_phases cp
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.monument_dated_types
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX monument_dated_types_resourceinstanceid
                            ON hapi.monument_dated_types USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.object_finds
                        TABLESPACE pg_default
                        AS
                        WITH object_finds AS (
                            SELECT 
                                amaa.resourceinstanceid,
                                ap.resourceinstanceid AS associated_resourceid,
                                ap.artefact_type,
                                ap.from_date,
                                ap.to_date,
                                ARRAY(
                                    SELECT (elem.value ->> 'resourceId'::text)::uuid AS uuid
                                    FROM jsonb_array_elements(ap.cultural_period) elem(value)
                                ) AS cultural_periods,
                                ap.material
                            FROM artefact.production ap
                            JOIN hapi.associated_monuments_areas_and_artefacts_mv amaa 
                            ON ap.resourceinstanceid = amaa.associated_resourceid
                        )
                        SELECT 
                            of.resourceinstanceid,
                            of.associated_resourceid,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(of.artefact_type) uuid(uuid)
                                LEFT JOIN "values" v ON uuid.uuid = v.valueid
                            ) AS artefact_type,
                            of.from_date,
                            of.to_date,
                            ARRAY(
                                SELECT pn.period_name
                                FROM unnest(of.cultural_periods) uuid(uuid)
                                LEFT JOIN hapi.period_names_mv pn ON uuid.uuid = pn.resourceinstanceid
                            ) AS cultural_periods,
                            ARRAY(
                                SELECT v.value
                                FROM unnest(of.material) uuid(uuid)
                                LEFT JOIN "values" v ON uuid.uuid = v.valueid
                            ) AS materials
                        FROM object_finds of
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.object_finds
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX object_finds_resourceinstanceid
                            ON hapi.object_finds USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_events
                        TABLESPACE pg_default
                        AS
                        SELECT 
                            aa.resourceinstanceid,
                            prn.primary_reference_number AS primaryreferencenumber,
                            tn.types,
                            an.name,
                            d.description
                        FROM hapi.related_events_associated_activities aa
                        LEFT JOIN hapi.related_events_type_names tn ON ((aa.activity ->> 'resourceId'::text)::uuid) = tn.resource_id
                        LEFT JOIN hapi.related_events_activity_names an ON ((aa.activity ->> 'resourceId'::text)::uuid) = an.resource_id
                        LEFT JOIN hapi.related_events_descriptions d ON ((aa.activity ->> 'resourceId'::text)::uuid) = d.resource_id
                        LEFT JOIN hapi.related_events_primary_reference_numbers prn ON ((aa.activity ->> 'resourceId'::text)::uuid) = prn.resource_id
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_events
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX related_events_resourceinstanceid
                            ON hapi.related_events USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE MATERIALIZED VIEW hapi.related_monument_records
                        TABLESPACE pg_default
                        AS
                        WITH primary_reference_numbers AS (
                            SELECT DISTINCT 
                                ar.associated_resource,
                                prn.primary_reference_number
                            FROM hapi.associated_resources_mv ar
                            JOIN hapi.monument_and_area_primary_reference_numbers_mv prn 
                            ON ar.associated_resource::uuid = prn.resourceinstanceid
                        )
                        SELECT 
                            ar.resourceinstanceid,
                            prn.primary_reference_number,
                            v.value AS association_type
                        FROM hapi.associated_resources_mv ar
                        JOIN primary_reference_numbers prn 
                            ON ar.associated_resource = prn.associated_resource
                        JOIN "values" v 
                            ON ar.association_type = v.valueid
                        WITH NO DATA;
                    """)
                    cursor.execute("""
                        ALTER TABLE hapi.related_monument_records
                            OWNER TO postgres;
                    """)
                    cursor.execute("""
                        CREATE INDEX related_monument_records_resourceinstanceid
                            ON hapi.related_monument_records USING btree
                            (resourceinstanceid)
                            TABLESPACE pg_default;
                    """)
                    cursor.execute("""
                        CREATE FUNCTION hapi.get_resources(
                            interval_param interval DEFAULT NULL::interval,
                            start_date timestamp with time zone DEFAULT NULL::timestamp with time zone,
                            end_date timestamp with time zone DEFAULT NULL::timestamp with time zone,
                            resource_instance_ids text DEFAULT NULL::text)
                        RETURNS TABLE(
                            resource_instance_id uuid, 
                            resource_type text, 
                            resource_name text, 
                            primary_reference_number numeric, 
                            most_recent_timestamp timestamp with time zone) 
                        LANGUAGE 'plpgsql'
                        COST 100
                        VOLATILE PARALLEL UNSAFE
                        ROWS 100

                        AS $BODY$
                        BEGIN
                            RETURN QUERY
                            SELECT 
                                rv.resourceinstanceid, 
                                rv.resource_type, 
                                rv.resource_name, 
                                rv.primary_reference_number, 
                                rv.most_recent_timestamp
                            FROM hapi.resources_mv rv
                            WHERE 
                                (resource_instance_ids IS NOT NULL AND rv.resourceinstanceid = ANY(string_to_array(resource_instance_ids, ',')::uuid[]))
                                OR (resource_instance_ids IS NULL AND start_date IS NOT NULL AND end_date IS NOT NULL AND rv.most_recent_timestamp BETWEEN start_date AND end_date)
                                OR (resource_instance_ids IS NULL AND start_date IS NULL AND end_date IS NULL AND 
                                    (interval_param IS NOT NULL AND rv.most_recent_timestamp >= NOW() - interval_param 
                                    OR interval_param IS NULL AND rv.most_recent_timestamp >= '0001-01-01'));
                        END;
                        $BODY$;
                    """)
                    cursor.execute("""
                        ALTER FUNCTION hapi.get_resources(interval, timestamp with time zone, timestamp with time zone, text)
                            OWNER TO postgres;
                    """)

            self.stdout.write(self.style.SUCCESS(
                'Standalone H.API database migration applied successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error applying standalone migration: {e}'))

    @staticmethod
    def refresh_materialized_views(cursor, refresh_option, use_tqdm=False):
        # Extract materialized views from this file
        with open(__file__, 'r') as file:
            content = file.read()

        # Regex to find materialized view names
        pattern = re.compile(r'CREATE MATERIALIZED VIEW (\w+\.\w+)')
        views = pattern.findall(content)

        # Refresh each materialized view
        pbar = tqdm(views, disable=not use_tqdm)
        max_len = max([len(view) for view in views])
        for view in pbar:
            if use_tqdm:
                pbar.set_description(view.ljust(max_len))
            start_time = time.time()
            cursor.execute(f'REFRESH MATERIALIZED VIEW {view} {refresh_option};')
            duration = time.time() - start_time
            tqdm.write(f'Refreshed {view} in {duration:.2f} seconds')

    def delete_schema(self, cursor):
        cursor.execute(f"""
            DROP SCHEMA IF EXISTS hapi CASCADE;
        """)
