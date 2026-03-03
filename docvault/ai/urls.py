"""URL configuration for the AI module."""

from django.urls import path

from . import views

urlpatterns = [
    # Search
    path("ai/search/semantic/", views.SemanticSearchView.as_view(), name="ai-semantic-search"),
    path("ai/search/hybrid/", views.HybridSearchView.as_view(), name="ai-hybrid-search"),
    path("ai/similar/<int:pk>/", views.SimilarDocumentsAIView.as_view(), name="ai-similar"),
    # Chat
    path("ai/documents/<int:pk>/chat/", views.DocumentChatView.as_view(), name="ai-document-chat"),
    path("ai/chat/", views.GlobalChatView.as_view(), name="ai-global-chat"),
    # Features
    path("ai/documents/<int:pk>/summarize/", views.SummarizeView.as_view(), name="ai-summarize"),
    path("ai/documents/<int:pk>/entities/", views.EntityExtractView.as_view(), name="ai-entities"),
    path(
        "ai/documents/<int:pk>/suggest-title/",
        views.SmartTitleView.as_view(),
        name="ai-suggest-title",
    ),
    # Admin
    path("ai/config/", views.AIConfigView.as_view(), name="ai-config"),
    path("ai/status/", views.AIStatusView.as_view(), name="ai-status"),
    path("ai/rebuild-index/", views.RebuildVectorIndexView.as_view(), name="ai-rebuild-index"),
]
