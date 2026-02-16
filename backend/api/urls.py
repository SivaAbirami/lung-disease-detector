from __future__ import annotations

from django.urls import path

from .views import (
    PredictView,
    PredictionHistoryView,
    TaskStatusView,
    RecommendationView,
    PredictionFeedbackView,
)


urlpatterns = [
    path("predict/", PredictView.as_view(), name="predict"),
    path("predictions/", PredictionHistoryView.as_view(), name="prediction-history"),
    path("task/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    path(
        "recommendations/<str:disease_name>/",
        RecommendationView.as_view(),
        name="recommendations",
    ),
    path(
        "predictions/<int:prediction_id>/feedback/",
        PredictionFeedbackView.as_view(),
        name="prediction-feedback",
    ),
]
