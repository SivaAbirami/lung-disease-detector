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
    """Create a DenseNet121-based transfer learning model for multi-label classification."""
    base_model = tf.keras.applications.DenseNet121(
        input_shape=(*IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    inputs = layers.Input(shape=(*IMAGE_SIZE, 3))
    x = get_data_augmentation()(inputs)
    # DenseNet expects inputs scaled from 0-1, or preprocess_input. 
    # Your ImageDataGenerator usually does rescale=1./255. 
    # If the generator rescales, we don't necessarily need preprocess_input, but it's safer.
    x = tf.keras.applications.densenet.preprocess_input(x * 255.0) # TF applications often want 0-255 inputs before preprocessing
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(512, activation="relu")(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    # MULTI-LABEL CHANGE: Output uses sigmoid
    outputs = layers.Dense(num_classes, activation="sigmoid")(x)

    model = models.Model(inputs, outputs, name="lung_disease_densenet121")
    return model


def compile_model(model: tf.keras.Model, base_learning_rate: float = 1e-4) -> tf.keras.Model:
    """Compile the model with Adam optimizer and multi-label metrics."""
    optimizer = optimizers.Adam(learning_rate=base_learning_rate)
    
    # MULTI-LABEL CHANGE: Loss uses binary_crossentropy
    model.compile(
        optimizer=optimizer,
        loss="binary_crossentropy", 
        metrics=[
            "accuracy",
            tf.keras.metrics.AUC(multi_label=True, name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
    return model

