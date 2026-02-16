from __future__ import annotations

from typing import Tuple

import tensorflow as tf
from tensorflow.keras import layers, models, optimizers


IMAGE_SIZE: Tuple[int, int] = (224, 224)


def get_data_augmentation() -> tf.keras.Sequential:
    """Return a data augmentation pipeline."""
    return tf.keras.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.1),
            layers.RandomZoom(0.1),
            layers.RandomContrast(0.1),
        ],
        name="data_augmentation",
    )


def create_model(num_classes: int) -> tf.keras.Model:
    """Create a MobileNetV2-based transfer learning model."""
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(*IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    inputs = layers.Input(shape=(*IMAGE_SIZE, 3))
    x = get_data_augmentation()(inputs)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = models.Model(inputs, outputs, name="lung_disease_mobilenetv2")
    return model


def compile_model(model: tf.keras.Model, base_learning_rate: float = 1e-4) -> tf.keras.Model:
    """Compile the model with Adam optimizer and appropriate metrics."""
    optimizer = optimizers.Adam(learning_rate=base_learning_rate)
    model.compile(
        optimizer=optimizer,
        loss="categorical_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
    return model

