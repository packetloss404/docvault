"""URL configuration for the workflows module."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    r"workflow-templates",
    views.WorkflowTemplateViewSet,
    basename="workflow-template",
)

# Nested state views
state_list = views.WorkflowStateViewSet.as_view({
    "get": "list",
    "post": "create",
})
state_detail = views.WorkflowStateViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

# Nested transition views
transition_list = views.WorkflowTransitionViewSet.as_view({
    "get": "list",
    "post": "create",
})
transition_detail = views.WorkflowTransitionViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

# Nested transition field views
field_list = views.WorkflowTransitionFieldViewSet.as_view({
    "get": "list",
    "post": "create",
})
field_detail = views.WorkflowTransitionFieldViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

# Nested state action views
action_list = views.WorkflowStateActionViewSet.as_view({
    "get": "list",
    "post": "create",
})
action_detail = views.WorkflowStateActionViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

# Nested state escalation views
escalation_list = views.WorkflowStateEscalationViewSet.as_view({
    "get": "list",
    "post": "create",
})
escalation_detail = views.WorkflowStateEscalationViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

# Document workflow views
doc_workflow_list = views.DocumentWorkflowViewSet.as_view({
    "get": "list",
})
doc_workflow_launch = views.DocumentWorkflowViewSet.as_view({
    "post": "launch",
})
doc_workflow_execute = views.DocumentWorkflowViewSet.as_view({
    "post": "execute_transition",
})
doc_workflow_log = views.DocumentWorkflowViewSet.as_view({
    "get": "log",
})
doc_workflow_available = views.DocumentWorkflowViewSet.as_view({
    "get": "available_transitions",
})

urlpatterns = [
    # Template states
    path(
        "workflow-templates/<int:template_pk>/states/",
        state_list,
        name="workflow-state-list",
    ),
    path(
        "workflow-templates/<int:template_pk>/states/<int:pk>/",
        state_detail,
        name="workflow-state-detail",
    ),
    # Template transitions
    path(
        "workflow-templates/<int:template_pk>/transitions/",
        transition_list,
        name="workflow-transition-list",
    ),
    path(
        "workflow-templates/<int:template_pk>/transitions/<int:pk>/",
        transition_detail,
        name="workflow-transition-detail",
    ),
    # Transition fields
    path(
        "workflow-templates/<int:template_pk>/transitions/<int:transition_pk>/fields/",
        field_list,
        name="workflow-transition-field-list",
    ),
    path(
        "workflow-templates/<int:template_pk>/transitions/<int:transition_pk>/fields/<int:pk>/",
        field_detail,
        name="workflow-transition-field-detail",
    ),
    # State actions
    path(
        "workflow-templates/<int:template_pk>/states/<int:state_pk>/actions/",
        action_list,
        name="workflow-state-action-list",
    ),
    path(
        "workflow-templates/<int:template_pk>/states/<int:state_pk>/actions/<int:pk>/",
        action_detail,
        name="workflow-state-action-detail",
    ),
    # State escalations
    path(
        "workflow-templates/<int:template_pk>/states/<int:state_pk>/escalations/",
        escalation_list,
        name="workflow-state-escalation-list",
    ),
    path(
        "workflow-templates/<int:template_pk>/states/<int:state_pk>/escalations/<int:pk>/",
        escalation_detail,
        name="workflow-state-escalation-detail",
    ),
    # Document workflows
    path(
        "documents/<int:document_pk>/workflows/",
        doc_workflow_list,
        name="document-workflow-list",
    ),
    path(
        "documents/<int:document_pk>/workflows/launch/",
        doc_workflow_launch,
        name="document-workflow-launch",
    ),
    path(
        "documents/<int:document_pk>/workflows/<int:instance_pk>/transitions/<int:transition_pk>/execute/",
        doc_workflow_execute,
        name="document-workflow-execute-transition",
    ),
    path(
        "documents/<int:document_pk>/workflows/<int:instance_pk>/log/",
        doc_workflow_log,
        name="document-workflow-log",
    ),
    path(
        "documents/<int:document_pk>/workflows/<int:instance_pk>/available-transitions/",
        doc_workflow_available,
        name="document-workflow-available-transitions",
    ),
    # Action backends
    path(
        "workflow-action-backends/",
        views.ActionBackendListView.as_view(),
        name="workflow-action-backends",
    ),
    # Router URLs last
    *router.urls,
]
