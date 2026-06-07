"""No-op output handler: leaves the downloaded file in its current location."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shelfmark.core.logger import setup_logger
from shelfmark.download.outputs import StatusCallback, register_output

if TYPE_CHECKING:
    from pathlib import Path
    from threading import Event

    from shelfmark.core.models import DownloadTask

logger = setup_logger(__name__)

NOOP_OUTPUT_MODE = "noop"


def _supports_noop_output(task: DownloadTask) -> bool:
    return True


@register_output(NOOP_OUTPUT_MODE, supports_task=_supports_noop_output, priority=0)
def process_noop_output(
    temp_file: Path,
    task: DownloadTask,
    cancel_flag: Event,
    status_callback: StatusCallback,
    *,
    preserve_source_on_failure: bool = False,
) -> str | None:
    """Leave the downloaded file in place without moving or copying it."""
    del cancel_flag, preserve_source_on_failure

    if not temp_file.exists():
        logger.warning("Task %s: noop output — file not found at %s", task.task_id, temp_file)
        status_callback("error", f"File not found: {temp_file}")
        return None

    logger.info("Task %s: noop output — leaving file at %s", task.task_id, temp_file)
    status_callback("complete", f"File left in place: {temp_file}")
    return str(temp_file)
