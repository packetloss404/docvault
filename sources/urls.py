"""URL configuration for the sources module."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"sources", views.SourceViewSet, basename="source")
router.register(r"mail-accounts", views.MailAccountViewSet, basename="mail-account")

# Nested mail rule views
mail_rule_list = views.MailRuleViewSet.as_view({
    "get": "list",
    "post": "create",
})
mail_rule_detail = views.MailRuleViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path(
        "mail-accounts/<int:account_pk>/rules/",
        mail_rule_list,
        name="mail-rule-list",
    ),
    path(
        "mail-accounts/<int:account_pk>/rules/<int:pk>/",
        mail_rule_detail,
        name="mail-rule-detail",
    ),
    *router.urls,
]
