from __future__ import annotations

from rest_framework import serializers

from .models import Prediction


class PredictionSerializer(serializers.ModelSerializer):
    """Serializer exposing all prediction fields plus convenience helpers."""

    image_url = serializers.SerializerMethodField()
    confidence_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Prediction
        fields = [
            "id",
            "image",
            "image_url",
            "image_hash",
            "predicted_class",
            "confidence_score",
            "confidence_percentage",
            "urgency_level",
            "urgency_color",
            "urgency_icon",
            "immediate_actions",
            "medical_recommendations",
            "lifestyle_recommendations",
            "follow_up",
            "disclaimer",
            "created_at",
            "processing_time_ms",
            "cached_result",
            "true_class",
            "is_corrected",
            "corrected_at",
        ]
        read_only_fields = [
            "id",
            "image_url",
            "image_hash",
            "created_at",
            "processing_time_ms",
            "cached_result",
            "true_class",
            "is_corrected",
            "corrected_at",
        ]

    def get_image_url(self, obj: Prediction) -> str | None:
        request = self.context.get("request")
        if not obj.image:
            return None
        url = obj.image.url
        return request.build_absolute_uri(url) if request is not None else url

    def get_confidence_percentage(self, obj: Prediction) -> float:
        return obj.confidence_percentage


class FeedbackSerializer(serializers.Serializer):
    """Accepts a user correction for a prediction."""

    true_class = serializers.ChoiceField(
        choices=Prediction.DiseaseClass.choices,
        help_text="The correct disease class for this X-ray.",
    )

