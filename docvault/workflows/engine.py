"""Workflow engine - stateless service for managing workflow lifecycle."""

import importlib
import logging
from datetime import timedelta

from django.utils import timezone

from workflows.constants import ON_ENTRY, ON_EXIT, UNIT_DAYS, UNIT_HOURS, UNIT_MINUTES, UNIT_WEEKS

logger = logging.getLogger(__name__)


def launch(document, template, user=None):
    """
    Launch a workflow instance for a document.

    Creates a WorkflowInstance at the template's initial state,
    then runs entry actions for that state.
    """
    from workflows.models import WorkflowInstance, WorkflowState

    initial_state = WorkflowState.objects.filter(
        workflow=template, initial=True
    ).first()
    if not initial_state:
        raise ValueError(
            f"Workflow '{template.label}' has no initial state."
        )

    instance = WorkflowInstance.objects.create(
        workflow=template,
        document=document,
        current_state=initial_state,
        context={},
    )

    # Create launch log entry
    from workflows.models import WorkflowInstanceLogEntry

    WorkflowInstanceLogEntry.objects.create(
        instance=instance,
        user=user,
        comment=f"Workflow '{template.label}' launched.",
    )

    _run_state_actions(instance, initial_state, ON_ENTRY)
    return instance


def do_transition(instance, transition, user=None, field_values=None, comment=""):
    """
    Execute a transition on a workflow instance.

    Validates origin state, checks required fields, evaluates condition,
    runs exit actions, moves state, updates context, creates log, runs entry actions.
    """
    from workflows.conditions import evaluate_condition
    from workflows.models import WorkflowInstanceLogEntry

    if instance.current_state_id != transition.origin_state_id:
        raise ValueError(
            f"Instance is in state '{instance.current_state.label}', "
            f"but transition '{transition.label}' requires state "
            f"'{transition.origin_state.label}'."
        )

    if instance.is_complete:
        raise ValueError("Cannot transition a completed workflow instance.")

    # Validate required fields
    field_values = field_values or {}
    for field in transition.fields.filter(required=True):
        if field.name not in field_values or not field_values[field.name]:
            raise ValueError(f"Required field '{field.label}' is missing.")

    # Check condition
    if transition.condition:
        if not evaluate_condition(transition.condition, instance):
            raise ValueError(
                f"Transition condition not met for '{transition.label}'."
            )

    # Run exit actions on current state
    _run_state_actions(instance, instance.current_state, ON_EXIT)

    # Move to destination state
    old_state = instance.current_state
    instance.current_state = transition.destination_state
    instance.state_changed_at = timezone.now()

    # Merge field values into context
    if field_values:
        ctx = instance.context or {}
        ctx.update(field_values)
        instance.context = ctx

    instance.save(update_fields=["current_state", "state_changed_at", "context"])

    # Create log entry
    WorkflowInstanceLogEntry.objects.create(
        instance=instance,
        transition=transition,
        user=user,
        comment=comment,
        transition_field_values=field_values,
    )

    # Run entry actions on new state
    _run_state_actions(instance, transition.destination_state, ON_ENTRY)
    return instance


def get_available_transitions(instance, user=None):
    """
    Get transitions available from the current state.

    Filters by condition evaluation.
    """
    from workflows.conditions import evaluate_condition
    from workflows.models import WorkflowTransition

    if not instance.current_state_id or instance.is_complete:
        return WorkflowTransition.objects.none()

    transitions = WorkflowTransition.objects.filter(
        workflow=instance.workflow,
        origin_state=instance.current_state,
    )

    available = []
    for t in transitions:
        if t.condition:
            try:
                if not evaluate_condition(t.condition, instance):
                    continue
            except Exception:
                logger.exception("Error evaluating condition for transition %s", t.pk)
                continue
        available.append(t.pk)

    return WorkflowTransition.objects.filter(pk__in=available)


def check_escalations():
    """
    Check all active workflow instances for overdue escalations.

    For each instance in a non-final state, check if any escalation
    rules have passed their deadline and auto-transition.
    """
    from workflows.conditions import evaluate_condition
    from workflows.models import WorkflowInstance, WorkflowStateEscalation

    now = timezone.now()
    active_instances = WorkflowInstance.objects.filter(
        current_state__isnull=False,
        current_state__final=False,
    ).select_related("current_state", "workflow")

    escalated_count = 0
    for instance in active_instances:
        escalations = WorkflowStateEscalation.objects.filter(
            state=instance.current_state,
            enabled=True,
        ).order_by("priority")

        for esc in escalations:
            delta = _escalation_timedelta(esc.amount, esc.unit)
            deadline = instance.state_changed_at + delta

            if now < deadline:
                continue

            # Check escalation condition
            if esc.condition:
                try:
                    if not evaluate_condition(esc.condition, instance):
                        continue
                except Exception:
                    logger.exception(
                        "Error evaluating escalation condition for instance %s",
                        instance.pk,
                    )
                    continue

            # Execute the escalation transition
            try:
                do_transition(
                    instance,
                    esc.transition,
                    user=None,
                    comment=esc.comment or f"Auto-escalated after {esc.amount} {esc.unit}.",
                )
                escalated_count += 1
                break  # Only one escalation per instance per check
            except Exception:
                logger.exception(
                    "Failed to escalate instance %s via transition %s",
                    instance.pk,
                    esc.transition_id,
                )

    return escalated_count


def _run_state_actions(instance, state, when):
    """Load and execute actions for a state at the given timing (ON_ENTRY/ON_EXIT)."""
    from workflows.conditions import evaluate_condition
    from workflows.models import WorkflowStateAction

    actions = WorkflowStateAction.objects.filter(
        state=state,
        enabled=True,
        when=when,
    ).order_by("order")

    for action in actions:
        # Check action condition
        if action.condition:
            try:
                if not evaluate_condition(action.condition, instance):
                    continue
            except Exception:
                logger.exception(
                    "Error evaluating action condition for action %s",
                    action.pk,
                )
                continue

        # Load and execute the action backend
        try:
            action_cls = _load_action_class(action.backend_path)
            if action_cls:
                action_instance = action_cls()
                action_instance.execute(instance, action.backend_data)
            else:
                logger.warning(
                    "Could not load action backend: %s", action.backend_path,
                )
        except Exception:
            logger.exception(
                "Error executing action '%s' (backend: %s) for instance %s",
                action.label,
                action.backend_path,
                instance.pk,
            )


def _load_action_class(dotted_path):
    """Load an action class from a dotted Python path."""
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError):
        return None


def _escalation_timedelta(amount, unit):
    """Convert escalation amount + unit into a timedelta."""
    if unit == UNIT_MINUTES:
        return timedelta(minutes=amount)
    elif unit == UNIT_HOURS:
        return timedelta(hours=amount)
    elif unit == UNIT_DAYS:
        return timedelta(days=amount)
    elif unit == UNIT_WEEKS:
        return timedelta(weeks=amount)
    return timedelta(days=amount)
