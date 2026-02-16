from __future__ import annotations

"""Training script for the lung disease detection model.

This script expects datasets downloaded from Kaggle:

- COVID-19 Radiography Database:
  https://www.kaggle.com/tawsifurrahman/covid19-radiography-database
- TB Chest X-ray Database:
  https://www.kaggle.com/tawsifurrahman/tuberculosis-tb-chest-xray-dataset

Place the extracted folders under: ``backend/dataset/``.

The script:
 - Combines datasets into a unified folder structure.
 - Applies data augmentation.
 - Handles class imbalance via class weights.
 - Splits into 70% train, 15% validation, 15% test.
 - Uses MobileNetV2 transfer learning (see model.py).
 - Trains in two phases: head-only then fine-tuning.
 - Saves best model to ``ml_model/saved_models/model.h5``.
"""

import json
import os
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.callbacks import (
    ModelCheckpoint,
    EarlyStopping,
    ReduceLROnPlateau,
)
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from .model import create_model, compile_model, IMAGE_SIZE


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
COMBINED_DIR = DATASET_DIR / "combined"
SAVED_MODELS_DIR = Path(__file__).resolve().parent / "saved_models"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


CLASSES = [
    "COVID-19",
    "Tuberculosis",
    "Bacterial Pneumonia",
    "Viral Pneumonia",
    "Normal",
]


def prepare_combined_dataset() -> None:
    """Prepare a combined dataset directory with class subfolders.

    This function assumes you have manually placed images into subfolders for
    the COVID and TB datasets. To keep this script environment-agnostic, we
    avoid moving files automatically and instead document the expected layout:

    backend/dataset/combined/
        COVID-19/
        Tuberculosis/
        Bacterial Pneumonia/
        Viral Pneumonia/
        Normal/
    """
    COMBINED_DIR.mkdir(parents=True, exist_ok=True)
    for cls in CLASSES:
        (COMBINED_DIR / cls).mkdir(parents=True, exist_ok=True)


def build_generators(
    image_size: Tuple[int, int] = IMAGE_SIZE,
    batch_size: int = 32,
) -> Tuple[tf.keras.preprocessing.image.DirectoryIterator, ...]:
    """Create train, validation, and test generators with augmentation."""
    prepare_combined_dataset()

    # Data augmentation for training
    train_datagen = ImageDataGenerator(
        rescale=1.0 / 255.0,
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        horizontal_flip=True,
        validation_split=0.30,  # 70% train / 30% temp
    )

    # For validation/test (no augmentation, only rescaling)
    test_datagen = ImageDataGenerator(rescale=1.0 / 255.0, validation_split=0.30)

    train_generator = train_datagen.flow_from_directory(
        COMBINED_DIR,
        target_size=image_size,
        batch_size=batch_size,
        class_mode="categorical",
        subset="training",
    )

    temp_generator = test_datagen.flow_from_directory(
        COMBINED_DIR,
        target_size=image_size,
        batch_size=batch_size,
        class_mode="categorical",
        subset="validation",
        shuffle=False,
    )

    # Split temp into validation and test (50/50 => 15% val, 15% test)
    n_temp = temp_generator.samples
    indices = np.arange(n_temp)
    np.random.shuffle(indices)
    split = n_temp // 2
    val_idx, test_idx = indices[:split], indices[split:]

    def _make_subset(gen: tf.keras.preprocessing.image.DirectoryIterator, subset_idx: np.ndarray):
        gen_subset = tf.keras.preprocessing.image.DirectoryIterator(
            directory=gen.directory,
            image_data_generator=gen.image_data_generator,
            target_size=gen.target_size,
            color_mode=gen.color_mode,
            classes=None,  # Do not pass int array, let it scan or pass string list
            class_mode=gen.class_mode,
            batch_size=gen.batch_size,
            shuffle=False,
            subset=None,
        )
        gen_subset.filenames = [gen.filenames[i] for i in subset_idx]
        gen_subset.samples = len(gen_subset.filenames)
        gen_subset.classes = gen.classes[subset_idx]
        gen_subset.class_indices = gen.class_indices
        return gen_subset

    val_generator = _make_subset(temp_generator, val_idx)
    test_generator = _make_subset(temp_generator, test_idx)

    return train_generator, val_generator, test_generator


def compute_class_weights_from_generator(
    generator: tf.keras.preprocessing.image.DirectoryIterator,
) -> Dict[int, float]:
    """Compute class weights to handle imbalance."""
    y = generator.classes
    class_labels = np.unique(y)
    weights = compute_class_weight(class_weight="balanced", classes=class_labels, y=y)
    return {int(cls): float(w) for cls, w in zip(class_labels, weights)}


def main() -> None:
    batch_size = 32
    train_gen, val_gen, test_gen = build_generators(batch_size=batch_size)

    num_classes = len(train_gen.class_indices)
    print(f"Detected classes: {train_gen.class_indices}")

    class_weights = compute_class_weights_from_generator(train_gen)
    # Save class weights for reference at inference time if needed
    with open(SAVED_MODELS_DIR / "class_weights.json", "w", encoding="utf-8") as f:
        json.dump(class_weights, f)

    model = create_model(num_classes=num_classes)
    model = compile_model(model, base_learning_rate=1e-4)

    callbacks = [
        ModelCheckpoint(
            filepath=str(SAVED_MODELS_DIR / "model.h5"),
            monitor="val_accuracy",
            save_best_only=True,
            save_weights_only=False,
            mode="max",
            verbose=1,
        ),
        EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    # Phase 1: train top layers with base frozen
    history1 = model.fit(
        train_gen,
        epochs=15,
        validation_data=val_gen,
        class_weight=class_weights,
        callbacks=callbacks,
    )

    # Phase 2: fine-tune some of the base_model layers
    base_model = model.get_layer("mobilenetv2_1.00_224")
    base_model.trainable = True
    fine_tune_at = len(base_model.layers) // 2
    for layer in base_model.layers[:fine_tune_at]:
        layer.trainable = False

    model = compile_model(model, base_learning_rate=1e-5)

    history2 = model.fit(
        train_gen,
        epochs=30,
        validation_data=val_gen,
        class_weight=class_weights,
        callbacks=callbacks,
    )

    # Evaluate on test set
    print("Evaluating on test set...")
    test_loss, test_acc, test_prec, test_rec = model.evaluate(test_gen)
    print(
        f"Test accuracy: {test_acc * 100:.2f}% | "
        f"Precision: {test_prec:.3f} | Recall: {test_rec:.3f}"
    )


if __name__ == "__main__":
    main()

