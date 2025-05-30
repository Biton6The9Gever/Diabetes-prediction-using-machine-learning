# -*- coding: utf-8 -*-
"""TabNet TransferLearning

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/16pVncMv7P3mXPHtUmr-4dxAFceJrwdAQ
"""

!cp /content/drive/MyDrive/diabetes_binary_health_indicators_BRFSS2015.csv.zip /content/  # Load Data


!unzip -o /content/diabetes_binary_health_indicators_BRFSS2015.csv.zip                    # Unzip Data

pip install pandas numpy scikit-learn matplotlib pytorch-tabnet

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from pytorch_tabnet.tab_model import TabNetClassifier


# Load your dataset (replace this path as needed)
df = pd.read_csv("/content/diabetes_binary_health_indicators_BRFSS2015.csv")
df.rename(columns={'Diabetes_binary': 'Output'}, inplace=True)

print(f"Duplicates are {df.duplicated().sum()}")
print("Droping all duplicates")
df.drop_duplicates(inplace = True)
print(f"Duplicates are {df.duplicated().sum()}")

feature_columns = [
    'HighBP', 'HighChol', 'BMI', 'Smoker', 'Stroke',
    'HeartDiseaseorAttack', 'PhysActivity',
    'NoDocbcCost', 'GenHlth',
    'MentHlth', 'PhysHlth', 'DiffWalk', 'Sex', 'Age'
]

scaler = MinMaxScaler()
df[feature_columns] = scaler.fit_transform(df[feature_columns])

X = df[feature_columns].values.astype(np.float32)
y = df["Output"].values.astype(np.int64)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=42)

print("Shapes:", X_train.shape, X_test.shape, y_train.shape, y_test.shape)

# === 1. Pretrain TabNet ===
pretrain_model = TabNetClassifier(
    n_d=8, n_a=8, n_steps=3,
    gamma=1.5, n_independent=2, n_shared=2,
    momentum=0.3, lambda_sparse=1e-3,
    optimizer_fn=torch.optim.Adam,
    optimizer_params=dict(lr=2e-2),
    mask_type='entmax'
)

print("Starting pretraining...")
pretrain_model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    eval_name=['train', 'valid'],
    eval_metric=['accuracy', 'auc'],
    max_epochs=50,
    patience=10,
    batch_size=1024,
    virtual_batch_size=128,
    num_workers=0,
    drop_last=False
)


# === Evaluate Pretrained Model ===
pretrained_preds = pretrain_model.predict(X_test)
pretrained_acc = (pretrained_preds == y_test).mean()
print(f"Pretrained Test Accuracy: {pretrained_acc:.4f}")

# === 2. Fine-tune TabNet starting from pretrained weights ===
finetune_model = TabNetClassifier(
    n_d=8, n_a=8, n_steps=3,
    gamma=1.5, n_independent=2, n_shared=2,
    momentum=0.3, lambda_sparse=1e-3,
    optimizer_fn=torch.optim.Adam,
    optimizer_params=dict(lr=1e-3),
    mask_type='entmax'
)


finetune_model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    eval_name=['train', 'valid'],
    eval_metric=['accuracy', 'auc'],
    max_epochs=50,
    patience=10,
    batch_size=1024,
    virtual_batch_size=128,
    num_workers=0,
    drop_last=False
)


# === Evaluate Fine-tuned Model ===
finetuned_preds = finetune_model.predict(X_test)
finetuned_acc = (finetuned_preds == y_test).mean()
print(f"Fine-tuned Test Accuracy: {finetuned_acc:.4f}")

# === 3. Plot Accuracy & AUC over Epochs ===

def plot_metrics(history, title):
    epochs = range(1, len(history['train_accuracy']) + 1)

    plt.figure(figsize=(12, 5))

    # Accuracy
    plt.subplot(1, 2, 1)
    plt.plot(epochs, history['train_accuracy'], label='Train Accuracy')
    plt.plot(epochs, history['valid_accuracy'], label='Valid Accuracy')
    plt.title(f'{title} - Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True)

    # AUC
    plt.subplot(1, 2, 2)
    plt.plot(epochs, history['train_auc'], label='Train AUC')
    plt.plot(epochs, history['valid_auc'], label='Valid AUC')
    plt.title(f'{title} - AUC')
    plt.xlabel('Epoch')
    plt.ylabel('AUC')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()

plot_metrics(pretrain_model.history, 'Pretraining')
plot_metrics(finetune_model.history, 'Fine-tuning')

# === 4. Plot Confusion Matrices ===

def plot_conf_matrix(y_true, y_pred, title):
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(cmap=plt.cm.Blues)
    plt.title(title)
    plt.grid(False)
    plt.show()

plot_conf_matrix(y_test, pretrained_preds, 'Confusion Matrix - Pretrained Model')
plot_conf_matrix(y_test, finetuned_preds, 'Confusion Matrix - Fine-tuned Model')
try:
  finetune_model.save_model('TabNet_model')
except:
  print("Model Failed to save")

!cp /content/TabNet_model.zip /content/drive/MyDrive

