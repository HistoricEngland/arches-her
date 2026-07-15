import os

AUTOMATIC_RUN_TYPE = "automatic"
MANUAL_RUN_TYPE = "manual"

try:
    import psutil  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised when optional dependency is missing.
    psutil = None

PSUTIL_ERRORS = (psutil.Error,) if psutil is not None else ()


def _iter_parent_processes(process):
    current_process = process

    while current_process is not None:
        try:
            parent = current_process.parent()
        except (AttributeError, OSError, TypeError, ValueError) + PSUTIL_ERRORS:
            return

        if parent is None:
            return

        yield parent
        current_process = parent


def is_windows_task_scheduler_parent(process=None):
    if os.name != "nt":
        return False

    if process is None and psutil is None:
        return False

    try:
        current_process = process or psutil.Process(os.getpid())
        for parent in _iter_parent_processes(current_process):
            parent_name = parent.name().lower()
            cmdline = parent.cmdline() or []
            cmdline_text = " ".join(cmdline).lower()

            if parent_name == "svchost.exe" and "schedule" in cmdline_text:
                return True

        return False
    except (AttributeError, IndexError, OSError, TypeError, ValueError) + PSUTIL_ERRORS:
        return False


def resolve_hapi_cron_run_type(process=None):
    if is_windows_task_scheduler_parent(process=process):
        return AUTOMATIC_RUN_TYPE
    return MANUAL_RUN_TYPE
