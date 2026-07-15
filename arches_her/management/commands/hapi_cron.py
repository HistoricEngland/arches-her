import json
import subprocess
import sys
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from arches_her.management.commands.utils.hapi_run_type import resolve_hapi_cron_run_type
from arches_her.hapi.seed_runtime import run_cron_daemon, send_cron_runtime_command


class Command(BaseCommand):
    help = "Run and manage the HAPI /batch/submit/cron workflow from the command line."

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            nargs="?",
            default="run",
            help="One of: run, status, terminate, shutdown",
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
            help="Whether to refresh accessioned/materialized HAPI data before upload (default: true).",
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

        # Internal options used when spawning detached process.
        parser.add_argument("--daemon", action="store_true",
                            help="Internal use only.")
        parser.add_argument("--task-id", default=None,
                            help="Internal use only.")
        parser.add_argument(
            "--run-type", choices=["automatic", "manual"], default=None, help="Internal use only.")

    def handle(self, *args, **options):
        action = str(options["action"]).strip().lower()

        if action not in ("run", "status", "terminate", "shutdown"):
            raise CommandError(
                "Action must be one of: run, status, terminate, shutdown")

        clean_monument_sources = options["clean_monument_sources"].lower(
        ) == "true"
        refresh_data = options["refresh_data"].lower() == "true"
        shutdown_on_complete = options["shutdown_on_complete"].lower(
        ) == "true"
        clear_data_on_complete = options["clear_data_on_complete"].lower(
        ) == "true"

        if options.get("daemon"):
            task_id = options.get("task_id") or str(uuid.uuid4())
            run_type = options.get("run_type") or "manual"
            run_cron_daemon(
                task_id=task_id,
                clean_monument_sources=clean_monument_sources,
                refresh_data=refresh_data,
                clear_data_on_complete=clear_data_on_complete,
                shutdown_on_complete=shutdown_on_complete,
                run_type=run_type,
            )
            return

        if action == "run":
            self._start_upload(
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
            self._terminate_upload()
            return

        if action == "shutdown":
            self._shutdown_upload()
            return

    def _start_upload(self, clean_monument_sources, refresh_data, clear_data_on_complete, shutdown_on_complete):
        status = send_cron_runtime_command("STATUS")
        if status and status.get("status") in ("pending", "progress"):
            self.stdout.write(
                self.style.WARNING(
                    f"A batch upload operation is already running (task_id={status.get('task_id', 'unknown')}).")
            )
            self.stdout.write(json.dumps(status, indent=2, default=str))
            return

        if status:
            send_cron_runtime_command("SHUTDOWN")

        task_id = str(uuid.uuid4())
        run_type = resolve_hapi_cron_run_type()
        manage_py = Path(__file__).resolve().parents[3] / "manage.py"

        cmd = [
            sys.executable,
            str(manage_py),
            "hapi_cron",
            "run",
            "--daemon",
            "--task-id",
            task_id,
            "--run-type",
            run_type,
            "--clean-monument-sources",
            "true" if clean_monument_sources else "false",
            "--refresh-data",
            "true" if refresh_data else "false",
            "--shutdown-on-complete",
            "true" if shutdown_on_complete else "false",
            "--clear-data-on-complete",
            "true" if clear_data_on_complete else "false",
        ]

        subprocess.Popen(
            cmd,
            cwd=str(manage_py.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "HAPI cron submission started asynchronously. Use `python manage.py hapi_cron status` to monitor progress.")
        )
        self.stdout.write(
            json.dumps(
                {
                    "status": "pending",
                    "message": "Batch upload started. Please check status.",
                    "task_id": task_id,
                    "run_type": run_type,
                    "refresh_data": refresh_data,
                    "clear_data_on_complete": clear_data_on_complete,
                    "shutdown_on_complete": shutdown_on_complete,
                },
                indent=2,
            )
        )

    def _show_status(self):
        status = send_cron_runtime_command("STATUS")
        if not status:
            payload = {
                "status": "not_running",
                "message": "No in-memory HAPI cron runtime is currently available.",
            }
            self.stdout.write(json.dumps(payload, indent=2))
            return

        self.stdout.write(json.dumps(status, indent=2, default=str))

    def _terminate_upload(self):
        response = send_cron_runtime_command("TERMINATE")
        if not response:
            payload = {
                "status": "not_running",
                "message": "No in-memory HAPI cron runtime is currently running.",
            }
            self.stdout.write(json.dumps(payload, indent=2))
            return

        self.stdout.write(json.dumps(response, indent=2, default=str))

    def _shutdown_upload(self):
        response = send_cron_runtime_command("SHUTDOWN")
        if not response:
            payload = {
                "status": "not_running",
                "message": "No in-memory HAPI cron runtime is currently running.",
            }
            self.stdout.write(json.dumps(payload, indent=2))
            return

        self.stdout.write(json.dumps(response, indent=2, default=str))
