from __future__ import annotations

import logging

from celery.result import AsyncResult
from django.db.models import Q
from django.http import Http404
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Prediction
from .serializers import PredictionSerializer
from .tasks import predict_image_task
from .utils.hash_utils import generate_image_hash
from .validators import validate_xray_image
from ml_model.recommendations import get_disease_recommendations


logger = logging.getLogger(__name__)


class PredictView(APIView):
    """Handle image upload and dispatch async prediction task."""

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("image")
        if not file_obj:
            return Response(
                {"detail": "No image file provided under 'image' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run validations
        try:
            validate_xray_image(file_obj, file_obj.name)
        except Exception as exc:
            logger.warning("Image validation failed: %s", exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Hash-based caching
        image_hash = generate_image_hash(file_obj)
        cached = Prediction.objects.filter(image_hash=image_hash).first()
        if cached:
            serializer = PredictionSerializer(cached, context={"request": request})
            return Response(
                {
                    "status": "completed",
                    "cached": True,
                    "prediction": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        # No cache hit: create prediction stub and enqueue async task
        prediction = Prediction.objects.create(
            image=file_obj,
            image_hash=image_hash,
            predicted_class=Prediction.DiseaseClass.UNKNOWN,
            confidence_score=0.0,
            urgency_level="MEDIUM",
            urgency_color="yellow",
            urgency_icon="🟡",
            immediate_actions=[],
            medical_recommendations=[],
            lifestyle_recommendations=[],
            follow_up="Pending model evaluation.",
            disclaimer=(
                "This is an AI-assisted screening tool. Not a medical diagnosis. "
                "Consult a healthcare provider."
            ),
            processing_time_ms=0.0,
            cached_result=False,
        )

        task = predict_image_task.delay(prediction.id)
        logger.info("Enqueued prediction task %s for prediction %s", task.id, prediction.id)

        return Response(
            {
                "task_id": task.id,
                "status": "processing",
                "cached": False,
                "prediction_id": prediction.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PredictionHistoryView(generics.ListAPIView):
    """Paginated history of predictions with basic filtering and search."""

    serializer_class = PredictionSerializer
    queryset = Prediction.objects.all()
    filterset_fields = ["predicted_class"]
    search_fields = ["id", "predicted_class", "image_hash"]
    ordering_fields = ["created_at", "confidence_score"]
    ordering = ["-created_at"]


class TaskStatusView(APIView):
    """Poll the status of an async prediction task."""

    def get(self, request, task_id: str, *args, **kwargs):
        from django.conf import settings

        # In eager mode, AsyncResult doesn't store results, so check the DB
        is_eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)

        if not is_eager:
            result = AsyncResult(task_id)
            state = result.state

            if state in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
                return Response({"status": "processing"}, status=status.HTTP_200_OK)

            if state == "FAILURE":
                return Response(
                    {"status": "failed", "error": str(result.info)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # SUCCESS: result should be prediction_id
            try:
                prediction_id = int(result.result)
                prediction = Prediction.objects.get(id=prediction_id)
            except Exception:
                raise Http404("Prediction not found for completed task.")

            serializer = PredictionSerializer(prediction, context={"request": request})
            return Response(
                {"status": "completed", "prediction": serializer.data},
                status=status.HTTP_200_OK,
            )

        # Eager mode: look up prediction by task_id from the POST response
        # The frontend passes prediction_id as a query param
        prediction_id = request.query_params.get("prediction_id")
        if prediction_id:
            try:
                prediction = Prediction.objects.get(id=int(prediction_id))
            except Prediction.DoesNotExist:
                return Response({"status": "processing"}, status=status.HTTP_200_OK)

            # Check if prediction has been filled in (not "Unknown" anymore)
            if prediction.predicted_class != Prediction.DiseaseClass.UNKNOWN:
                serializer = PredictionSerializer(prediction, context={"request": request})
                return Response(
                    {"status": "completed", "prediction": serializer.data},
                    status=status.HTTP_200_OK,
                )

        # Fallback: try to find the most recent completed prediction
        return Response({"status": "processing"}, status=status.HTTP_200_OK)


class RecommendationView(APIView):
    """Return recommendations for a specific disease name."""

    def get(self, request, disease_name: str, *args, **kwargs):
        recs = get_disease_recommendations(disease_name)
        return Response(recs, status=status.HTTP_200_OK)

