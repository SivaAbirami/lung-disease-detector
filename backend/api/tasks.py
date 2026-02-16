from __future__ import annotations

import logging
from datetime import timedelta
from time import perf_counter

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from .models import Prediction
from .serializers import PredictionSerializer
from .validators import validate_xray_image
from .utils.hash_utils import generate_image_hash
from ml_model.predict import predict_image
from ml_model.recommendations import get_disease_recommendations


logger = logging.getLogger(__name__)
task_logger = get_task_logger(__name__)


# IMPORTANT: This order MUST match the alphabetical directory order used by
# ImageDataGenerator.flow_from_directory() during training on Kaggle.
CLASS_NAMES = [
    "Bacterial Pneumonia",
    "COVID-19",
    "Normal",
    "Tuberculosis",
    "Viral Pneumonia",
]


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def predict_image_task(self, prediction_id: int) -> int:
    """Celery task to run ML prediction on a stored image.

    Returns the ID of the updated Prediction instance.
    """
    try:
        prediction = Prediction.objects.get(id=prediction_id)
    except Prediction.DoesNotExist as exc:  # pragma: no cover - defensive
        task_logger.error("Prediction object not found: %s", exc)
        raise

    image_path = prediction.image.path
    start = perf_counter()

    try:
        # Validate again at worker side as a defense-in-depth measure
        with open(image_path, "rb") as f:
            validate_xray_image(f, prediction.image.name)

        predicted_class, confidence, model_time_ms = predict_image(
            image_path=image_path,
            class_names=CLASS_NAMES,
        )
        recs = get_disease_recommendations(predicted_class)

        total_time_ms = (perf_counter() - start) * 1000.0

        prediction.predicted_class = predicted_class
        prediction.confidence_score = confidence
        prediction.urgency_level = recs["urgency_level"]
        prediction.urgency_color = recs["urgency_color"]
        prediction.urgency_icon = recs["urgency_icon"]
        prediction.immediate_actions = recs["immediate_actions"]
        prediction.medical_recommendations = recs["medical_recommendations"]
        prediction.lifestyle_recommendations = recs["lifestyle_recommendations"]
        prediction.follow_up = recs["follow_up"]
        prediction.disclaimer = recs["disclaimer"]
        prediction.processing_time_ms = total_time_ms
        prediction.cached_result = False
        prediction.save(update_fields=[
            "predicted_class",
            "confidence_score",
            "urgency_level",
            "urgency_color",
            "urgency_icon",
            "immediate_actions",
            "medical_recommendations",
            "lifestyle_recommendations",
            "follow_up",
            "disclaimer",
            "processing_time_ms",
            "cached_result",
        ])

        task_logger.info(
            "Prediction %s completed: %s (%.2f%%) in %.2f ms",
            prediction.id,
            prediction.predicted_class,
            prediction.confidence_percentage,
            total_time_ms,
        )
        return prediction.id
    except Exception as exc:  # pragma: no cover - Celery handles retries
        try:
            countdown = 2 ** self.request.retries
        except Exception:
            countdown = 10
        task_logger.error("Error during prediction task: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task
def cleanup_old_predictions(days: int = 30) -> int:
    """Periodic task to delete predictions older than a given number of days.

    Returns the count of deleted records.
    """
    threshold = timezone.now() - timedelta(days=days)
    qs = Prediction.objects.filter(created_at__lt=threshold)
    count = qs.count()
    qs.delete()
    logger.info("Deleted %s old predictions (older than %s days)", count, days)
    return count

