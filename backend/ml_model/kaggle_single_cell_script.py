import os
import glob
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.model_selection import GroupShuffleSplit

# ==============================================================================
# 1. DATASET LOADING
# ==============================================================================
KAGGLE_INPUT_DIR = "/kaggle/input"

NIH_DIR   = f"{KAGGLE_INPUT_DIR}/datasets/nih-chest-xrays/data"
COVID_DIR = f"{KAGGLE_INPUT_DIR}/datasets/tawsifurrahman/covid19-radiography-database/COVID-19_Radiography_Dataset"
RSNA_DIR  = f"{KAGGLE_INPUT_DIR}/competitions/rsna-pneumonia-detection-challenge"
TB_DIR    = f"{KAGGLE_INPUT_DIR}/datasets/tawsifurrahman/tuberculosis-tb-chest-xray-dataset/TB_Chest_Radiography_Database"

DISEASES = [
    "Atelectasis", "Cardiomegaly", "Consolidation", "Edema", "Effusion",
    "Emphysema", "Fibrosis", "Hernia", "Infiltration", "Mass", "Nodule",
    "Pleural_Thickening", "Pneumonia", "Pneumothorax", "COVID-19", "Tuberculosis", "Normal"
]

def load_nih_dataset() -> pd.DataFrame:
    csv_path = os.path.join(NIH_DIR, "Data_Entry_2017.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    print("Scanning NIH images...")
    image_paths = {
        os.path.basename(p): p
        for p in glob.glob(f"{NIH_DIR}/**/images/*.png", recursive=True)
    }
    print(f"Found {len(image_paths)} NIH images.")
    df['filepath'] = df['Image Index'].map(image_paths)
    df = df.dropna(subset=['filepath'])
    df['patient_id'] = "nih_" + df['Patient ID'].astype(str)
    for d in DISEASES:
        df[d] = 0
    for idx, row in df.iterrows():
        labels = str(row['Finding Labels']).split('|')
        if "No Finding" in labels:
            df.at[idx, 'Normal'] = 1
        else:
            for label in labels:
                if label in DISEASES:
                    df.at[idx, label] = 1
    return df[['filepath', 'patient_id'] + DISEASES]

def load_covid_dataset() -> pd.DataFrame:
    if not os.path.exists(COVID_DIR):
        return pd.DataFrame()
    data = []
    mapping = {
        "COVID": "COVID-19",
        "Normal": "Normal",
        "Viral Pneumonia": "Pneumonia",
        "Lung_Opacity": "Pneumonia"
    }
    for folder, disease_label in mapping.items():
        folder_path = os.path.join(COVID_DIR, folder, "images")
        if not os.path.exists(folder_path):
            folder_path = os.path.join(COVID_DIR, folder)
        for img_path in glob.glob(f"{folder_path}/*.png"):
            row = {"filepath": img_path, "patient_id": f"covid_{os.path.basename(img_path)}"}
            row.update({d: (1 if d == disease_label else 0) for d in DISEASES})
            data.append(row)
    return pd.DataFrame(data)

def load_tb_dataset() -> pd.DataFrame:
    if not os.path.exists(TB_DIR):
        return pd.DataFrame()
    data = []
    for folder, disease_label in {"Tuberculosis": "Tuberculosis", "Normal": "Normal"}.items():
        folder_path = os.path.join(TB_DIR, folder)
        for img_path in glob.glob(f"{folder_path}/*.png"):
            row = {"filepath": img_path, "patient_id": f"tb_{os.path.basename(img_path)}"}
            row.update({d: (1 if d == disease_label else 0) for d in DISEASES})
            data.append(row)
    return pd.DataFrame(data)

def load_rsna_dataset() -> pd.DataFrame:
    csv_path = os.path.join(RSNA_DIR, "stage_2_train_labels.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    df = df.drop_duplicates(subset=['patientId'])
    df['filepath'] = df['patientId'].apply(
        lambda x: os.path.join(RSNA_DIR, "stage_2_train_images", f"{x}.dcm")
    )
    df['patient_id'] = "rsna_" + df['patientId'].astype(str)
    for d in DISEASES:
        df[d] = 0
    df['Pneumonia'] = df['Target']
    df['Normal'] = (df['Target'] == 0).astype(int)
    return df[['filepath', 'patient_id'] + DISEASES]

def build_master_dataframe() -> pd.DataFrame:
    print("Merging datasets...")
    master_df = pd.concat(
        [load_nih_dataset(), load_covid_dataset(), load_rsna_dataset(), load_tb_dataset()],
        ignore_index=True
    )
    print(f"Total images: {len(master_df)}")
    for d in DISEASES:
        print(f"  {d}: {int(master_df[d].sum())}")

    # Downsample Normal-only to 50% (not 80% — too aggressive shifts decision boundary)
    normal_only = (
        (master_df['Normal'] == 1) &
        (master_df[DISEASES].drop(columns=['Normal']).sum(axis=1) == 0)
    )
    drop_idx = np.random.choice(
        master_df[normal_only].index,
        size=int(normal_only.sum() * 0.5),
        replace=False
    )
    master_df = master_df.drop(drop_idx).reset_index(drop=True)
    print(f"After Normal downsampling: {len(master_df)} images.")
    return master_df

# ==============================================================================
# 2. PATIENT-LEVEL SPLIT
# ==============================================================================
def patient_level_split(df, val_size=0.10, test_size=0.10, random_state=42):
    """
    Split by patient ID so no patient appears in more than one split.
    Prevents the model from memorizing patient anatomy and cheating on val/test.
    """
    ids = df['patient_id'].values

    gss = GroupShuffleSplit(1, test_size=test_size, random_state=random_state)
    train_val_idx, test_idx = next(gss.split(df, groups=ids))
    train_val_df = df.iloc[train_val_idx].reset_index(drop=True)
    test_df      = df.iloc[test_idx].reset_index(drop=True)

    val_frac = val_size / (1 - test_size)
    gss2 = GroupShuffleSplit(1, test_size=val_frac, random_state=random_state)
    train_idx, val_idx = next(gss2.split(train_val_df, groups=train_val_df['patient_id'].values))
    train_df = train_val_df.iloc[train_idx].reset_index(drop=True)
    val_df   = train_val_df.iloc[val_idx].reset_index(drop=True)

    # Verify no leakage
    assert not set(train_df.patient_id) & set(val_df.patient_id), "Train/val patient leak!"
    assert not set(train_df.patient_id) & set(test_df.patient_id), "Train/test patient leak!"

    print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")
    return train_df, val_df, test_df

# ==============================================================================
# 3. MODEL
# ==============================================================================
IMAGE_SIZE = (224, 224)

def create_model(num_classes: int) -> tf.keras.Model:
    base_model = tf.keras.applications.DenseNet121(
        input_shape=(*IMAGE_SIZE, 3), include_top=False, weights="imagenet"
    )
    base_model.trainable = False

    inputs = layers.Input(shape=(*IMAGE_SIZE, 3))

    # FIX: augmentation layers need training=True flag so they are
    # disabled at inference time — otherwise every prediction is randomly
    # flipped/rotated giving different results on the same image.
    x = layers.RandomFlip("horizontal")(inputs, training=True)
    x = layers.RandomRotation(0.08)(x, training=True)
    # No RandomContrast — destroys density gradients that distinguish
    # Edema / Consolidation / Fibrosis from each other.

    # FIX: generator outputs [0,1], preprocess_input expects [0,255]
    x = layers.Lambda(lambda t: t * 255.0)(x)
    x = layers.Lambda(lambda t: tf.keras.applications.densenet.preprocess_input(t))(x)

    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(512, activation="relu")(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="sigmoid")(x)

    return models.Model(inputs, outputs, name="lung_disease_densenet121")

def compile_model(model: tf.keras.Model, lr: float = 1e-4) -> tf.keras.Model:
    # Focal Loss handles class imbalance — do NOT also pass class_weight to fit()
    model.compile(
        optimizer=optimizers.Adam(learning_rate=lr),
        loss=tf.keras.losses.BinaryFocalCrossentropy(gamma=2.0, alpha=0.25),
        metrics=[
            "accuracy",
            tf.keras.metrics.AUC(multi_label=True, name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ]
    )
    return model

# ==============================================================================
# 4. TRAINING
# ==============================================================================
if __name__ == "__main__":
    df = build_master_dataframe()
    train_df, val_df, test_df = patient_level_split(df)

    # No augmentation in generator — it lives inside the model only
    datagen = ImageDataGenerator(rescale=1.0 / 255.0)
    train_gen = datagen.flow_from_dataframe(
        train_df, x_col="filepath", y_col=DISEASES,
        target_size=IMAGE_SIZE, batch_size=32, class_mode="raw", shuffle=True
    )
    val_gen = datagen.flow_from_dataframe(
        val_df, x_col="filepath", y_col=DISEASES,
        target_size=IMAGE_SIZE, batch_size=32, class_mode="raw", shuffle=False
    )
    test_gen = datagen.flow_from_dataframe(
        test_df, x_col="filepath", y_col=DISEASES,
        target_size=IMAGE_SIZE, batch_size=32, class_mode="raw", shuffle=False
    )

    model = compile_model(create_model(len(DISEASES)))
    os.makedirs("/kaggle/working/saved_models", exist_ok=True)

    # FIX: both callbacks monitor val_auc so they agree on "best"
    callbacks = [
        ModelCheckpoint(
            "/kaggle/working/saved_models/model.keras",
            monitor="val_auc", save_best_only=True, mode="max", verbose=1
        ),
        EarlyStopping(
            monitor="val_auc", patience=5,
            restore_best_weights=True, mode="max"
        ),
        ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6, verbose=1
        ),
    ]

    print("\n--- Phase 1: Training Head (backbone frozen) ---")
    model.fit(train_gen, epochs=15, validation_data=val_gen, callbacks=callbacks)

    print("\n--- Phase 2: Fine-tuning top half of DenseNet ---")
    base_model = model.get_layer("densenet121")
    base_model.trainable = True
    # FIX: freeze bottom half — unfreezing all layers risks catastrophic
    # forgetting of ImageNet features at this learning rate
    for layer in base_model.layers[:len(base_model.layers) // 2]:
        layer.trainable = False

    model = compile_model(model, lr=1e-5)
    model.fit(train_gen, epochs=25, validation_data=val_gen, callbacks=callbacks)

    print("\n--- Final Evaluation on held-out Test Set ---")
    results = model.evaluate(test_gen)
    print(dict(zip(model.metrics_names, results)))

    # Per-class AUC to see exactly which diseases are still confused
    from sklearn.metrics import roc_auc_score
    preds = model.predict(test_gen, verbose=1)
    true  = test_df[DISEASES].values
    print("\nPer-class AUC:")
    for i, d in enumerate(DISEASES):
        pos = np.sum(true[:, i])
        if pos == 0:
            print(f"  {d:<22}: no positive samples")
            continue
        auc = roc_auc_score(true[:, i], preds[:, i])
        flag = " ⚠️" if auc < 0.75 else ""
        print(f"  {d:<22}: {auc:.4f}{flag}")