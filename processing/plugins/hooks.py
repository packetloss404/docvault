"""Pre/post-consume hook plugins - execute user-supplied scripts."""

import logging
import os
import subprocess

from django.conf import settings

from processing.context import PluginResult, ProcessingContext

from .base import ProcessingPlugin

logger = logging.getLogger(__name__)


class PreConsumeHookPlugin(ProcessingPlugin):
    """Execute a user-supplied script before document processing."""

    name = "PreConsumeHook"
    order = 40

    def can_run(self, context: ProcessingContext) -> bool:
        script = getattr(settings, "PRE_CONSUME_SCRIPT", "")
        return bool(script)

    def process(self, context: ProcessingContext) -> PluginResult:
        script = settings.PRE_CONSUME_SCRIPT
        timeout = getattr(settings, "CONSUME_SCRIPT_TIMEOUT", 30)
        return _run_hook(script, context, timeout, "pre-consume")


class PostConsumeHookPlugin(ProcessingPlugin):
    """Execute a user-supplied script after all document processing."""

    name = "PostConsumeHook"
    order = 140

    def can_run(self, context: ProcessingContext) -> bool:
        script = getattr(settings, "POST_CONSUME_SCRIPT", "")
        return bool(script)

    def process(self, context: ProcessingContext) -> PluginResult:
        script = settings.POST_CONSUME_SCRIPT
        timeout = getattr(settings, "CONSUME_SCRIPT_TIMEOUT", 30)
        return _run_hook(script, context, timeout, "post-consume")


def _run_hook(
    script: str,
    context: ProcessingContext,
    timeout: int,
    hook_name: str,
) -> PluginResult:
    """Run a hook script with document information as environment variables."""
    env = os.environ.copy()
    env.update({
        "DOCUMENT_SOURCE_PATH": str(context.source_path or ""),
        "DOCUMENT_ORIGINAL_FILENAME": context.original_filename,
        "DOCUMENT_MIME_TYPE": context.mime_type,
        "DOCUMENT_TITLE": context.title,
        "DOCUMENT_CONTENT": context.content[:10000],
        "DOCUMENT_LANGUAGE": context.language,
        "DOCUMENT_CHECKSUM": context.checksum,
        "DOCUMENT_ID": str(context.document_id or ""),
        "DOCUMENT_TASK_ID": str(context.task_id or ""),
    })

    try:
        result = subprocess.run(
            script,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            shell=True,
        )
        if result.returncode != 0:
            logger.warning(
                "%s hook script failed (exit code %d): %s",
                hook_name, result.returncode, result.stderr[:500],
            )
            return PluginResult(
                success=True,
                message=f"{hook_name} hook failed (exit {result.returncode})",
            )
        logger.info("%s hook script completed successfully", hook_name)
        return PluginResult(success=True, message=f"{hook_name} hook completed")
    except subprocess.TimeoutExpired:
        logger.warning("%s hook script timed out after %ds", hook_name, timeout)
        return PluginResult(
            success=True,
            message=f"{hook_name} hook timed out after {timeout}s",
        )
    except FileNotFoundError:
        logger.warning("%s hook script not found: %s", hook_name, script)
        return PluginResult(
            success=True,
            message=f"{hook_name} hook script not found",
        )
    except Exception as e:
        logger.warning("%s hook script error: %s", hook_name, e)
        return PluginResult(success=True, message=f"{hook_name} hook error: {e}")
