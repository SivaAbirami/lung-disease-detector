from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from time import perf_counter
from typing import Tuple

import numpy as np
import tensorflow as tf
from PIL import Image

from .model import IMAGE_SIZE, create_model, compile_model


logger = logging.getLogger(__name__)

_model: tf.keras.Model | None = None
_model_lock = threading.Lock()

NUM_CLASSES = 5  # COVID-19, Tuberculosis, Bacterial Pneumonia, Viral Pneumonia, Normal


def _load_model() -> tf.keras.Model:
    """Load the trained model from disk.

    Rebuilds the model architecture from code and loads weights from the
    converted .weights.h5 file (created by apply_weights.py).
    """
    global _model
    # Use the converted weights file (clean Keras 3 format)
    default_path = str(
        Path(__file__).resolve().parent / "saved_models" / "converted_model.weights.h5"
    )
    model_path = os.getenv("MODEL_PATH", default_path)
    logger.info("Loading ML model from %s", model_path)
    start = perf_counter()

    # Rebuild architecture from code (identical to training)
    _model = create_model(num_classes=NUM_CLASSES)
    _model = compile_model(_model)

    # Load weights from the clean converted file
    _model.load_weights(model_path)

    elapsed = (perf_counter() - start) * 1000
    logger.info("Model loaded in %.2f ms", elapsed)
    return _model


def get_model() -> tf.keras.Model:
    """Return the global model instance, loading it once with double-checked locking."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _load_model()
    assert _model is not None
    return _model


def preprocess_image(image_path: str) -> np.ndarray:
    """Load and preprocess an image file for prediction.

    The model graph already includes mobilenet_v2.preprocess_input() which maps
    [0, 255] -> [-1, 1], so we must NOT rescale here.
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize(IMAGE_SIZE, Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32)  # keep [0, 255] range
    arr = np.expand_dims(arr, axis=0)
    return arr


def predict_image(image_path: str, class_names: list[str]) -> Tuple[str, float, float]:
    """Run inference on an image and return (predicted_class, confidence, time_ms)."""
    model = get_model()
    inputs = preprocess_image(image_path)

    start = perf_counter()
    preds = model.predict(inputs, verbose=0)  # type: ignore[no-untyped-call]
    elapsed_ms = (perf_counter() - start) * 1000.0

    probs = preds[0]
    idx = int(np.argmax(probs))
    confidence = float(probs[idx])
    predicted_class = class_names[idx] if idx < len(class_names) else "Unknown"

    logger.info(
        "Prediction: %s (%.2f%%) in %.2f ms",
        predicted_class,
        confidence * 100.0,
        elapsed_ms,
    )
    return predicted_class, confidence, elapsed_ms

