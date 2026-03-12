import os
import glob
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.model_selection import train_test_split

# ==============================================================================
# 1. KAGGLE DATASET MERGER
# ==============================================================================
KAGGLE_INPUT_DIR = "/kaggle/input"

NIH_DIR   = f"{KAGGLE_INPUT_DIR}/datasets/organizations/nih-chest-xrays/data"
COVID_DIR = f"{KAGGLE_INPUT_DIR}/datasets/tawsifurrahman/covid19-radiography-database/COVID-19_Radiography_Dataset"
TB_DIR    = f"{KAGGLE_INPUT_DIR}/datasets/tawsifurrahman/tuberculosis-tb-chest-xray-dataset/TB_Chest_Radiography_Database"

DISEASES = [
    "Atelectasis", "Cardiomegaly", "Consolidation", "Edema", "Effusion",
    "Emphysema", "Fibrosis", "Hernia", "Infiltration", "Mass", "Nodule",
    "Pleural_Thickening", "Pneumonia", "Pneumothorax", "COVID-19", "Tuberculosis", "Normal"
]

def load_nih_dataset() -> pd.DataFrame:
    csv_path = os.path.join(NIH_DIR, "Data_Entry_2017.csv")
    if not os.path.exists(csv_path): return pd.DataFrame()

    df = pd.read_csv(csv_path)
    print("Scanning all NIH sub-folders recursively...")
    image_paths = {os.path.basename(p): p for p in glob.glob(f"{NIH_DIR}/**/images/*.png", recursive=True)}
    print(f"Found {len(image_paths)} NIH images on disk.")
    
    df['filepath'] = df['Image Index'].map(image_paths)
    df = df.dropna(subset=['filepath']) 
    
    for disease in DISEASES: df[disease] = 0.0
        
    for index, row in df.iterrows():
        labels = str(row['Finding Labels']).split('|')
        if "No Finding" in labels:
            df.at[index, 'Normal'] = 1.0
        else:
            for label in labels:
                if label in DISEASES:
                    df.at[index, label] = 1.0
                    
    return df[['filepath'] + DISEASES]

def load_covid_dataset() -> pd.DataFrame:
    if not os.path.exists(COVID_DIR): return pd.DataFrame()
    data = []
    mapping = {"COVID": "COVID-19", "Normal": "Normal", "Viral Pneumonia": "Pneumonia", "Lung_Opacity": "Pneumonia"}
    for folder, disease_label in mapping.items():
        folder_path = os.path.join(COVID_DIR, folder, "images")
        if not os.path.exists(folder_path): folder_path = os.path.join(COVID_DIR, folder) 
        images = glob.glob(f"{folder_path}/*.png")
        for img_path in images:
            row = {"filepath": img_path}
            row.update({d: (1.0 if d == disease_label else 0.0) for d in DISEASES})
            data.append(row)
    return pd.DataFrame(data)

def load_tb_dataset() -> pd.DataFrame:
    if not os.path.exists(TB_DIR): return pd.DataFrame()
    data = []
    mapping = {"Tuberculosis": "Tuberculosis", "Normal": "Normal"}
    for folder, disease_label in mapping.items():
        folder_path = os.path.join(TB_DIR, folder) 
        images = glob.glob(f"{folder_path}/*.png")
        for img_path in images:
            row = {"filepath": img_path}
            row.update({d: (1.0 if d == disease_label else 0.0) for d in DISEASES})
            data.append(row)
    return pd.DataFrame(data)

def build_master_dataframe() -> pd.DataFrame:
    print("Merging Datasets...")
    # NOTE: Dropped RSNA dataset to avoid DICOM (.dcm) crashes inside tf.data. 
    # The remaining datasets still provide 130,000+ clean PNG/JPG images.
    master_df = pd.concat([load_nih_dataset(), load_covid_dataset(), load_tb_dataset()], ignore_index=True)
    
    print(f"Final Database Size: {len(master_df)} Images (PNG only).")
    for d in DISEASES:
        print(f"  - {d}: {int(master_df[d].sum())}")

    return master_df

# ==============================================================================
# 2. HIGH-PERFORMANCE TF.DATA PIPELINE
# ==============================================================================
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

def parse_image(filepath, label):
    # Read the file
    img = tf.io.read_file(filepath)
    # Decode PNG/JPEG
    img = tf.image.decode_image(img, channels=3, expand_animations=False)
    # Resize
    img = tf.image.resize(img, IMAGE_SIZE)
    # DenseNet121 native preprocessing (moved OUTSIDE the model)
    # DenseNet expects inputs scaled according to its specific ImageNet distribution computation
    img = tf.keras.applications.densenet.preprocess_input(img)
    return img, label

def augment_image(img, label):
    img = tf.image.random_flip_left_right(img)
    # We avoid Brightness/Contrast/Zoom/Rotation here to keeping density gradients intact and inference wildly fast
    return img, label

def create_tf_dataset(df: pd.DataFrame, is_training: bool = True):
    filepaths = df['filepath'].values
    labels = df[DISEASES].values.astype('float32') # MUST be float32 for Focal Loss
    
    dataset = tf.data.Dataset.from_tensor_slices((filepaths, labels))
    dataset = dataset.map(parse_image, num_parallel_calls=tf.data.AUTOTUNE)
    if is_training:
        dataset = dataset.shuffle(buffer_size=2000)
        dataset = dataset.map(augment_image, num_parallel_calls=tf.data.AUTOTUNE)
    
    dataset = dataset.batch(BATCH_SIZE)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset

# ==============================================================================
# 3. MODEL DEFINITION
# ==============================================================================
def create_model(num_classes: int) -> tf.keras.Model:
    base_model = tf.keras.applications.DenseNet121(input_shape=(*IMAGE_SIZE, 3), include_top=False, weights="imagenet")
    base_model.trainable = False
    
    inputs = layers.Input(shape=(*IMAGE_SIZE, 3))
    # NO preprocessing Lambda layers inside the model! 
    # All scaling is done in `tf.data` map functions to ensure perfect serialization.
    
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dense(512, activation="relu")(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(num_classes, activation="sigmoid")(x)
    
    return models.Model(inputs, outputs, name="densenet121_medical")

def compile_model(model: tf.keras.Model, base_learning_rate: float = 1e-4) -> tf.keras.Model:
    # We rely purely on Focal Loss. No class_weights in model.fit()!
    # Gamma=2.0 sharply focuses on hard examples. Alpha=0.25 balances positive/negative imbalance natively.
    loss = tf.keras.losses.BinaryFocalCrossentropy(gamma=2.0, alpha=0.25)
    model.compile(
        optimizer=optimizers.Adam(learning_rate=base_learning_rate),
        loss=loss, 
        metrics=[
            tf.keras.metrics.AUC(multi_label=True, name="auc"),
            tf.keras.metrics.Recall(name="recall"),
            tf.keras.metrics.Precision(name="precision")
        ]
    )
    return model

# ==============================================================================
# 4. TRAINING PIPELINE
# ==============================================================================
if __name__ == "__main__":
    # Ensure TF uses mixed precision if hardware supports it (Major speed boost on T4s)
    tf.keras.mixed_precision.set_global_policy('mixed_float16')
    
    df = build_master_dataframe()
    train_df, val_df = train_test_split(df, test_size=0.15, random_state=42)

    # High performance dataset generation
    train_ds = create_tf_dataset(train_df, is_training=True)
    val_ds = create_tf_dataset(val_df, is_training=False)

    model = create_model(len(DISEASES))
    model = compile_model(model, base_learning_rate=1e-3)
    
    os.makedirs("/kaggle/working/saved_models", exist_ok=True)
    callbacks = [
        ModelCheckpoint("/kaggle/working/saved_models/model.keras", monitor="val_auc", save_best_only=True, mode="max", verbose=1),
        EarlyStopping(monitor="val_auc", patience=5, restore_best_weights=True, mode="max"),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-6, verbose=1)
    ]

    print("\n--- Phase 1: Training Head (Base Model Frozen) ---")
    model.fit(train_ds, epochs=10, validation_data=val_ds, callbacks=callbacks)

    print("\n--- Phase 2: Fine-Tuning Backbone ---")
    for layer in model.get_layer("densenet121").layers[-60:]:
        if not isinstance(layer, layers.BatchNormalization):
            layer.trainable = True
            
    model = compile_model(model, base_learning_rate=1e-5) 
    model.fit(train_ds, epochs=25, validation_data=val_ds, callbacks=callbacks)