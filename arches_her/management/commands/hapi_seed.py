import json
import subprocess
import sys
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from arches_her.hapi.seed_runtime import run_dry_run_daemon, run_seed_daemon, run_validate_daemon, send_runtime_command


class Command(BaseCommand):
    help = "Run and manage the HAPI initial seed operation from the command line."

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            nargs="?",
            default="seed",
            help="One of: seed, validate, dry-run, status, terminate, shutdown, report",
        )
        parser.add_argument(
            "--seed-limit-count",
            type=int,
            default=0,
            help="Optional limit for number of resources to seed. 0 means all resources.",
        )
        parser.add_argument(
            "--clean-monument-sources",
            choices=["true", "false"],
            default="true",
            help="Whether to clean monument source validation errors (default: true).",
        )
        parser.add_argument(
            "--refresh-data",
            choices=["true", "false"],
            default="true",
            help="Whether to refresh materialized HAPI data before processing (default: true).",
        )
        parser.add_argument(
            "--confirm",
            choices=["yes", "no"],
            default="no",
            help="Confirm that you want to start the operation (required for seed, validate, dry-run). Pass 'yes' to proceed.",
        )
        parser.add_argument(
            "--shutdown-on-complete",
            choices=["true", "false"],
            default="false",
            help="Whether the detached daemon should exit automatically when the operation completes (default: false).",
        )
        parser.add_argument(
            "--clear-data-on-complete",
            choices=["true", "false"],
            default="true",
            help="Whether materialized views should be cleared with WITH NO DATA when the operation completes (default: true).",
        )
        parser.add_argument(
            "--batch-id",
            type=int,
            default=None,
            help="Batch ID for report action. Negative values are used for validation-only/dry-run operations.",
        )
        parser.add_argument(
            "--format",
            choices=["json", "text", "csv"],
            default="json",
            help="Output format for report (default: json).",
        )
        parser.add_argument(
            "--full-report",
            choices=["true", "false"],
            default="false",
            help="Generate full report with all errors (default: false).",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=500,
            help="Batch size for streaming database rows during report generation (default: 500).",
        )

        # Internal options used when spawning detached process.
        parser.add_argument("--daemon", action="store_true",
                            help="Internal use only.")
        parser.add_argument("--task-id", default=None,
                            help="Internal use only.")
        parser.add_argument(
            "--operation", choices=["seed", "validate", "dry-run"], default="seed", help="Internal use only.")

    def handle(self, *args, **options):
        action = str(options["action"]).strip().lower()

        if action not in ("seed", "validate", "dry-run", "status", "terminate", "shutdown", "report"):
            raise CommandError(
                "Action must be one of: seed, validate, dry-run, status, terminate, shutdown, report")

        clean_monument_sources = options["clean_monument_sources"].lower(
        ) == "true"
        refresh_data = options["refresh_data"].lower() == "true"
        seed_limit_count = int(options["seed_limit_count"])
        confirm = options.get("confirm", "no").lower()
        shutdown_on_complete = options["shutdown_on_complete"].lower(
        ) == "true"
        clear_data_on_complete = options["clear_data_on_complete"].lower(
        ) == "true"

        if seed_limit_count < 0:
            raise CommandError(
                "--seed-limit-count must be 0 or a positive integer")

        if options.get("daemon"):
            task_id = options.get("task_id") or str(uuid.uuid4())
            operation = options.get("operation", "seed")
            if operation == "validate":
                run_validate_daemon(
                    task_id=task_id,
                    seed_limit_count=seed_limit_count,
                    clean_monument_sources=clean_monument_sources,
                    refresh_data=refresh_data,
                    clear_data_on_complete=clear_data_on_complete,
                    shutdown_on_complete=shutdown_on_complete,
                )
            elif operation == "dry-run":
                run_dry_run_daemon(
                    task_id=task_id,
                    seed_limit_count=seed_limit_count,
                    clean_monument_sources=clean_monument_sources,
                    refresh_data=refresh_data,
                    clear_data_on_complete=clear_data_on_complete,
                    shutdown_on_complete=shutdown_on_complete,
                )
            else:
                run_seed_daemon(
                    task_id=task_id,
                    seed_limit_count=seed_limit_count,
                    clean_monument_sources=clean_monument_sources,
                    refresh_data=refresh_data,
                    clear_data_on_complete=clear_data_on_complete,
                    shutdown_on_complete=shutdown_on_complete,
                )
            return

        if action == "seed":
            if confirm != "yes":
                self.stdout.write(
                    self.style.ERROR(
                        "ERROR: Seed operation requires explicit confirmation.\n"
                        "Use: python manage.py hapi_seed seed --confirm yes [--seed-limit-count N] [--clean-monument-sources true|false]"
                    )
                )
                return
            self._start_seed(
                seed_limit_count=seed_limit_count,
                clean_monument_sources=clean_monument_sources,
                refresh_data=refresh_data,
                clear_data_on_complete=clear_data_on_complete,
                shutdown_on_complete=shutdown_on_complete,
            )
            return

        if action == "validate":
            if confirm != "yes":
                self.stdout.write(
                    self.style.ERROR(
                        "ERROR: Validation operation requires explicit confirmation.\n"
                        "Use: python manage.py hapi_seed validate --confirm yes [--seed-limit-count N] [--clean-monument-sources true|false]"
                    )
                )
                return
            self._start_validate(
                seed_limit_count=seed_limit_count,
                clean_monument_sources=clean_monument_sources,
                refresh_data=refresh_data,
                clear_data_on_complete=clear_data_on_complete,
                shutdown_on_complete=shutdown_on_complete,
            )
            return

        if action == "dry-run":
            if confirm != "yes":
                self.stdout.write(
                    self.style.ERROR(
                        "ERROR: Dry-run operation requires explicit confirmation.\n"
                        "Use: python manage.py hapi_seed dry-run --confirm yes [--seed-limit-count N] [--clean-monument-sources true|false]"
                    )
                )
                return
            self._start_dry_run(
                seed_limit_count=seed_limit_count,
                clean_monument_sources=clean_monument_sources,
                refresh_data=refresh_data,
                clear_data_on_complete=clear_data_on_complete,
                shutdown_on_complete=shutdown_on_complete,
            )
            return

        if action == "status":
            self._show_status()
            return

        if action == "terminate":
            self._terminate_seed()
            return

        if action == "shutdown":
            self._shutdown_seed()
            return

        if action == "report":
            batch_id = options.get("batch_id")
            if batch_id is None:
                self.stdout.write(
                    self.style.ERROR(
                        "ERROR: Report action requires --batch-id parameter.\n"
                        "Use: python manage.py hapi_seed report --batch-id -1 [--format json|text|csv]"
                    )
                )
                return
            format_type = options.get("format", "json")
            full_report = options.get("full_report", "false").lower() == "true"
            chunk_size = int(options.get("chunk_size", 500))
            if chunk_size <= 0:
                raise CommandError("--chunk-size must be a positive integer")
            self._generate_report(
                batch_id=batch_id,
                format_type=format_type,
                full_report=full_report,
                chunk_size=chunk_size,
            )
            return

    def _start_seed(self, seed_limit_count, clean_monument_sources, refresh_data, clear_data_on_complete, shutdown_on_complete):
        status = send_runtime_command("STATUS")
        if status and status.get("status") in ("pending", "progress"):
            self.stdout.write(self.style.WARNING(
                f"A seed operation is already running (task_id={status.get('task_id', 'unknown')})."))
            self.stdout.write(json.dumps(status, indent=2, default=str))
            return

        if status:
            send_runtime_command("SHUTDOWN")

        task_id = str(uuid.uuid4())
        manage_py = Path(__file__).resolve().parents[3] / "manage.py"

        cmd = [
            sys.executable,
            str(manage_py),
            "hapi_seed",
            "seed",
            "--daemon",
            "--task-id", task_id,
            "--seed-limit-count", str(seed_limit_count),
            "--clean-monument-sources", "true" if clean_monument_sources else "false",
            "--refresh-data", "true" if refresh_data else "false",
            "--shutdown-on-complete", "true" if shutdown_on_complete else "false",
            "--clear-data-on-complete", "true" if clear_data_on_complete else "false",
        ]

        subprocess.Popen(cmd, cwd=str(manage_py.parent), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)

        self.stdout.write(self.style.SUCCESS(
            "HAPI seed started asynchronously. Use `python manage.py hapi_seed status` to monitor progress."))
        self.stdout.write(json.dumps({"status": "pending", "task_id": task_id, "refresh_data": refresh_data,
                          "clear_data_on_complete": clear_data_on_complete, "shutdown_on_complete": shutdown_on_complete}, indent=2))

    def _start_validate(self, seed_limit_count, clean_monument_sources, refresh_data, clear_data_on_complete, shutdown_on_complete):
        status = send_runtime_command("STATUS")
        if status and status.get("status") in ("pending", "progress"):
            self.stdout.write(self.style.WARNING(
                f"A validation operation is already running (task_id={status.get('task_id', 'unknown')})."))
            self.stdout.write(json.dumps(status, indent=2, default=str))
            return

        if status:
            send_runtime_command("SHUTDOWN")

        task_id = str(uuid.uuid4())
        manage_py = Path(__file__).resolve().parents[3] / "manage.py"

        cmd = [
            sys.executable,
            str(manage_py),
            "hapi_seed",
            "validate",
            "--daemon",
            "--task-id", task_id,
            "--seed-limit-count", str(seed_limit_count),
            "--clean-monument-sources", "true" if clean_monument_sources else "false",
            "--refresh-data", "true" if refresh_data else "false",
            "--shutdown-on-complete", "true" if shutdown_on_complete else "false",
            "--clear-data-on-complete", "true" if clear_data_on_complete else "false",
            "--operation", "validate",
        ]

        subprocess.Popen(cmd, cwd=str(manage_py.parent), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)

        self.stdout.write(self.style.SUCCESS(
            "HAPI validation started asynchronously. Use `python manage.py hapi_seed status` to monitor progress."))
        self.stdout.write(json.dumps({"status": "pending", "task_id": task_id, "validation_only": True, "refresh_data": refresh_data,
                          "clear_data_on_complete": clear_data_on_complete, "shutdown_on_complete": shutdown_on_complete}, indent=2))

    def _start_dry_run(self, seed_limit_count, clean_monument_sources, refresh_data, clear_data_on_complete, shutdown_on_complete):
        status = send_runtime_command("STATUS")
        if status and status.get("status") in ("pending", "progress"):
            self.stdout.write(self.style.WARNING(
                f"A dry-run operation is already running (task_id={status.get('task_id', 'unknown')})."))
            self.stdout.write(json.dumps(status, indent=2, default=str))
            return

        if status:
            send_runtime_command("SHUTDOWN")

        task_id = str(uuid.uuid4())
        manage_py = Path(__file__).resolve().parents[3] / "manage.py"

        cmd = [
            sys.executable,
            str(manage_py),
            "hapi_seed",
            "dry-run",
            "--daemon",
            "--task-id", task_id,
            "--seed-limit-count", str(seed_limit_count),
            "--clean-monument-sources", "true" if clean_monument_sources else "false",
            "--refresh-data", "true" if refresh_data else "false",
            "--shutdown-on-complete", "true" if shutdown_on_complete else "false",
            "--clear-data-on-complete", "true" if clear_data_on_complete else "false",
            "--operation", "dry-run",
        ]

        subprocess.Popen(cmd, cwd=str(manage_py.parent), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)

        self.stdout.write(self.style.SUCCESS(
            "HAPI dry-run started asynchronously. Use `python manage.py hapi_seed status` to monitor progress."))
        self.stdout.write(json.dumps({"status": "pending", "task_id": task_id, "dry_run": True, "validation_only": True, "refresh_data": refresh_data,
                          "clear_data_on_complete": clear_data_on_complete, "shutdown_on_complete": shutdown_on_complete}, indent=2))

    def _show_status(self):
        status = send_runtime_command("STATUS")
        if not status:
            self.stdout.write(json.dumps(
                {"status": "not_running", "message": "No in-memory HAPI seed runtime is currently available."}, indent=2))
            return
        self.stdout.write(json.dumps(status, indent=2, default=str))

    def _terminate_seed(self):
        response = send_runtime_command("TERMINATE")
        if not response:
            self.stdout.write(json.dumps(
                {"status": "not_running", "message": "No in-memory HAPI seed runtime is currently running."}, indent=2))
            return
        self.stdout.write(json.dumps(response, indent=2, default=str))

    def _shutdown_seed(self):
        response = send_runtime_command("SHUTDOWN")
        if not response:
            self.stdout.write(json.dumps(
                {"status": "not_running", "message": "No in-memory HAPI seed runtime is currently running."}, indent=2))
            return
        self.stdout.write(json.dumps(response, indent=2, default=str))

    def _generate_report(self, batch_id, format_type="json", full_report=False, chunk_size=500):
        """Generate a validation error report from hapi_data rows matching the batch_id."""
        from arches_her.models import models
        from arches_her.hapi.validation_error_analyzer import ValidationErrorAnalyzer
        import csv
        import io

        try:
            base_queryset = models.HeritageApiData.objects.filter(
                batch_id=batch_id).order_by("part")

            if not base_queryset.exists():
                self.stdout.write(self.style.ERROR(
                    f"No data found for batch_id={batch_id}"))
                return

            total_records = 0
            total_invalid_records = 0
            rows_iter = base_queryset.values_list(
                "validation", "data").iterator(chunk_size=chunk_size)

            analyzer = ValidationErrorAnalyzer() if format_type in ("json", "text") else None

            csv_buffer = None
            csv_writer = None
            if format_type == "csv":
                csv_buffer = io.StringIO()
                csv_writer = csv.writer(csv_buffer, lineterminator="\n")
                csv_writer.writerow(
                    ["Resource_ID", "Field_Name", "Validation_Error"])
                self.stdout.write(csv_buffer.getvalue(), ending="")
                csv_buffer.seek(0)
                csv_buffer.truncate(0)

            for validation_response, row_data in rows_iter:
                if row_data and isinstance(row_data, dict):
                    records = row_data.get("records", [])
                    total_records += len(records) if records else 0

                if not validation_response or not isinstance(validation_response, dict):
                    continue

                errors = validation_response.get("errors", [])

                if isinstance(errors, dict):
                    total_invalid_records += len(errors.keys())

                    if analyzer is not None:
                        analyzer.process_error_entry(errors)

                    if csv_writer is not None:
                        for record_id, field_errors in errors.items():
                            if isinstance(field_errors, dict):
                                for field_name, error_messages in field_errors.items():
                                    if isinstance(error_messages, list):
                                        for message in error_messages:
                                            csv_writer.writerow(
                                                [record_id, field_name, str(message)])
                                    else:
                                        csv_writer.writerow(
                                            [record_id, field_name, str(error_messages)])

                elif isinstance(errors, list):
                    for error_entry in errors:
                        if not error_entry or not isinstance(error_entry, dict):
                            continue
                        total_invalid_records += len(error_entry.keys())

                        if analyzer is not None:
                            analyzer.process_error_entry(error_entry)

                        if csv_writer is not None:
                            for record_id, field_errors in error_entry.items():
                                if isinstance(field_errors, dict):
                                    for field_name, error_messages in field_errors.items():
                                        if isinstance(error_messages, list):
                                            for message in error_messages:
                                                csv_writer.writerow(
                                                    [record_id, field_name, str(message)])
                                        else:
                                            csv_writer.writerow(
                                                [record_id, field_name, str(error_messages)])

                if csv_buffer is not None and csv_buffer.tell() > 65536:
                    self.stdout.write(csv_buffer.getvalue(), ending="")
                    csv_buffer.seek(0)
                    csv_buffer.truncate(0)

            if full_report:
                field_limit = message_limit = combo_limit = 0
            else:
                field_limit, message_limit, combo_limit = 20, 20, 15

            if format_type == "text":
                analyzer.total_records_processed = total_records
                analyzer.total_invalid_records = total_invalid_records
                self.stdout.write(analyzer.generate_report(
                    field_limit=field_limit, message_limit=message_limit, combo_limit=combo_limit))

            elif format_type == "csv":
                if csv_buffer is not None:
                    remaining = csv_buffer.getvalue()
                    if remaining:
                        self.stdout.write(remaining, ending="")
                    csv_buffer.close()

            else:  # json (default)
                analyzer.total_records_processed = total_records
                analyzer.total_invalid_records = total_invalid_records

                top_fields = sorted(
                    analyzer.field_errors.items(), key=lambda x: x[1], reverse=True)
                if field_limit > 0:
                    top_fields = top_fields[:field_limit]

                top_messages = sorted(
                    analyzer.error_messages.items(), key=lambda x: x[1], reverse=True)
                if message_limit > 0:
                    top_messages = top_messages[:message_limit]

                report_data = {
                    "status": "success",
                    "batch_id": batch_id,
                    "summary_statistics": {
                        "total_records_processed": analyzer.total_records_processed,
                        "total_unique_failed_resources": len(analyzer.unique_failed_resources),
                        "resources_with_monument_sources_only_errors": len(analyzer.monument_sources_only_resources),
                        "resources_that_will_not_appear_in_hg": len(analyzer.unique_failed_resources) - len(analyzer.monument_sources_only_resources),
                        "resources_that_will_appear_in_hg": analyzer.total_records_processed - (len(analyzer.unique_failed_resources) - len(analyzer.monument_sources_only_resources)),
                        "total_invalid_records": analyzer.total_invalid_records,
                        "total_validation_errors": analyzer.total_errors,
                        "unique_error_messages": len(analyzer.error_messages),
                        "unique_fields_with_errors": len(analyzer.field_errors),
                        "avg_errors_per_invalid_record": analyzer.total_errors / max(1, analyzer.total_invalid_records),
                    },
                    "field_errors": [
                        {"field": field, "count": count, "percentage": round(
                            (count / analyzer.total_errors) * 100, 2)}
                        for field, count in top_fields
                    ],
                    "error_messages": [
                        {"message": message, "count": count, "percentage": round(
                            (count / analyzer.total_errors) * 100, 2)}
                        for message, count in top_messages
                    ],
                }
                self.stdout.write(json.dumps(report_data, indent=2))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Error generating report: {str(e)}"))
            import traceback
            traceback.print_exc()
