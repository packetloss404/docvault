"""Views for the workflows module."""

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document
from security.permissions import IsAdminOrReadOnly

from . import engine
from .actions import BUILTIN_ACTIONS
from .models import (
    WorkflowAction,
    WorkflowInstance,
    WorkflowInstanceLogEntry,
    WorkflowRule,
    WorkflowState,
    WorkflowStateAction,
    WorkflowStateEscalation,
    WorkflowTemplate,
    WorkflowTransition,
    WorkflowTransitionField,
    WorkflowTrigger,
)
from .serializers import (
    TransitionExecuteSerializer,
    WorkflowActionSerializer,
    WorkflowInstanceLogEntrySerializer,
    WorkflowInstanceSerializer,
    WorkflowRuleSerializer,
    WorkflowStateActionSerializer,
    WorkflowStateEscalationSerializer,
    WorkflowStateSerializer,
    WorkflowTemplateSerializer,
    WorkflowTransitionFieldSerializer,
    WorkflowTransitionSerializer,
    WorkflowTriggerSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------

class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for workflow templates."""

    queryset = WorkflowTemplate.objects.all()
    serializer_class = WorkflowTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["label", "internal_name"]
    ordering_fields = ["label", "created_at"]
    ordering = ["label"]


class WorkflowStateViewSet(viewsets.ModelViewSet):
    """CRUD for states within a workflow template."""

    serializer_class = WorkflowStateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowState.objects.filter(
            workflow_id=self.kwargs["template_pk"]
        )

    def perform_create(self, serializer):
        serializer.save(workflow_id=self.kwargs["template_pk"])


class WorkflowTransitionViewSet(viewsets.ModelViewSet):
    """CRUD for transitions within a workflow template."""

    serializer_class = WorkflowTransitionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowTransition.objects.filter(
            workflow_id=self.kwargs["template_pk"]
        ).select_related("origin_state", "destination_state")

    def perform_create(self, serializer):
        serializer.save(workflow_id=self.kwargs["template_pk"])


class WorkflowTransitionFieldViewSet(viewsets.ModelViewSet):
    """CRUD for fields on a transition."""

    serializer_class = WorkflowTransitionFieldSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowTransitionField.objects.filter(
            transition_id=self.kwargs["transition_pk"],
            transition__workflow_id=self.kwargs["template_pk"],
        )

    def perform_create(self, serializer):
        serializer.save(transition_id=self.kwargs["transition_pk"])


class WorkflowStateActionViewSet(viewsets.ModelViewSet):
    """CRUD for actions on a state."""

    serializer_class = WorkflowStateActionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowStateAction.objects.filter(
            state_id=self.kwargs["state_pk"],
            state__workflow_id=self.kwargs["template_pk"],
        )

    def perform_create(self, serializer):
        serializer.save(state_id=self.kwargs["state_pk"])


class WorkflowStateEscalationViewSet(viewsets.ModelViewSet):
    """CRUD for escalation rules on a state."""

    serializer_class = WorkflowStateEscalationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowStateEscalation.objects.filter(
            state_id=self.kwargs["state_pk"],
            state__workflow_id=self.kwargs["template_pk"],
        )

    def perform_create(self, serializer):
        serializer.save(state_id=self.kwargs["state_pk"])


# ---------------------------------------------------------------------------
# Document workflow operations
# ---------------------------------------------------------------------------

class DocumentWorkflowViewSet(viewsets.ViewSet):
    """Operations on workflow instances attached to a document."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_document(self, document_pk):
        return Document.objects.get(pk=document_pk)

    def list(self, request, document_pk=None):
        """List all workflow instances for a document."""
        instances = WorkflowInstance.objects.filter(
            document_id=document_pk,
        ).select_related("workflow", "current_state")
        serializer = WorkflowInstanceSerializer(instances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def launch(self, request, document_pk=None):
        """Launch a workflow for a document."""
        template_id = request.data.get("workflow_template_id")
        if not template_id:
            return Response(
                {"error": "workflow_template_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document = self._get_document(document_pk)
            template = WorkflowTemplate.objects.get(pk=template_id)
        except (Document.DoesNotExist, WorkflowTemplate.DoesNotExist) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            instance = engine.launch(document, template, user=request.user)
        except (ValueError, Exception) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            WorkflowInstanceSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"(?P<instance_pk>[0-9]+)/transitions/(?P<transition_pk>[0-9]+)/execute",
    )
    def execute_transition(self, request, document_pk=None,
                           instance_pk=None, transition_pk=None):
        """Execute a transition on a workflow instance."""
        try:
            instance = WorkflowInstance.objects.get(
                pk=instance_pk, document_id=document_pk,
            )
            transition = WorkflowTransition.objects.get(
                pk=transition_pk, workflow=instance.workflow,
            )
        except (WorkflowInstance.DoesNotExist, WorkflowTransition.DoesNotExist) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TransitionExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            instance = engine.do_transition(
                instance,
                transition,
                user=request.user,
                field_values=serializer.validated_data.get("field_values", {}),
                comment=serializer.validated_data.get("comment", ""),
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(WorkflowInstanceSerializer(instance).data)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"(?P<instance_pk>[0-9]+)/log",
    )
    def log(self, request, document_pk=None, instance_pk=None):
        """Get the audit log for a workflow instance."""
        entries = WorkflowInstanceLogEntry.objects.filter(
            instance_id=instance_pk,
            instance__document_id=document_pk,
        ).select_related("transition", "user")
        serializer = WorkflowInstanceLogEntrySerializer(entries, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"(?P<instance_pk>[0-9]+)/available-transitions",
    )
    def available_transitions(self, request, document_pk=None, instance_pk=None):
        """Get available transitions for a workflow instance."""
        try:
            instance = WorkflowInstance.objects.get(
                pk=instance_pk, document_id=document_pk,
            )
        except WorkflowInstance.DoesNotExist:
            return Response(
                {"error": "Workflow instance not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        transitions = engine.get_available_transitions(instance, request.user)
        serializer = WorkflowTransitionSerializer(transitions, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Trigger-Action Rules
# ---------------------------------------------------------------------------

class WorkflowRuleViewSet(viewsets.ModelViewSet):
    """CRUD for workflow rules."""

    queryset = WorkflowRule.objects.all()
    serializer_class = WorkflowRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["name"]
    ordering_fields = ["name", "order", "created_at"]
    ordering = ["order", "name"]


class WorkflowRuleTriggerViewSet(viewsets.ModelViewSet):
    """CRUD for triggers within a workflow rule."""

    serializer_class = WorkflowTriggerSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowTrigger.objects.filter(
            rules=self.kwargs["rule_pk"],
        )

    def perform_create(self, serializer):
        trigger = serializer.save()
        rule = WorkflowRule.objects.get(pk=self.kwargs["rule_pk"])
        rule.triggers.add(trigger)


class WorkflowRuleActionViewSet(viewsets.ModelViewSet):
    """CRUD for actions within a workflow rule."""

    serializer_class = WorkflowActionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WorkflowAction.objects.filter(
            rules=self.kwargs["rule_pk"],
        )

    def perform_create(self, serializer):
        action = serializer.save()
        rule = WorkflowRule.objects.get(pk=self.kwargs["rule_pk"])
        rule.actions.add(action)


class ActionBackendListView(APIView):
    """List available action backends."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        backends = [
            {"backend_path": path, **info}
            for path, info in BUILTIN_ACTIONS.items()
        ]
        return Response(backends)
