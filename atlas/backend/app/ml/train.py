"""
ML Model Training Script
Trains LightGBM model with SHAP explainer for fraud detection
"""
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import joblib
from pathlib import Path
import logging

from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, classification_report,
    confusion_matrix, average_precision_score
)
import shap

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.feature_engine import FeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_synthetic_data(n_samples: int = 10000, fraud_rate: float = 0.02) -> pd.DataFrame:
    """
    Generate synthetic transaction data for training.
    
    Args:
        n_samples: Number of transactions to generate
        fraud_rate: Percentage of fraudulent transactions
    
    Returns:
        DataFrame with features and labels
    """
    logger.info(f"Generating {n_samples} synthetic transactions...")
    
    feature_engineer = FeatureEngineer()
    data = []
    
    # Countries and their probabilities
    countries = ["US", "CA", "GB", "DE", "FR", "NG", "RU", "CN", "BR", "IN"]
    country_probs_normal = [0.4, 0.1, 0.1, 0.1, 0.1, 0.02, 0.02, 0.06, 0.05, 0.05]
    country_probs_fraud = [0.1, 0.05, 0.05, 0.05, 0.05, 0.2, 0.2, 0.1, 0.1, 0.1]
    
    merchant_categories = ["grocery", "restaurant", "retail", "electronics", 
                          "jewelry", "cryptocurrency", "gambling", "travel"]
    
    # Simulate users
    user_ids = [f"user_{i}" for i in range(n_samples // 10)]
    
    for i in range(n_samples):
        is_fraud = random.random() < fraud_rate
        user_id = random.choice(user_ids)
        
        # Generate transaction based on fraud status
        if is_fraud:
            # Fraudulent patterns
            amount = random.choice([
                random.uniform(500, 5000),  # High amount
                random.randint(1, 10) * 100,  # Round numbers
                random.uniform(50, 200),  # Small test transaction
            ])
            country = np.random.choice(countries, p=country_probs_fraud)
            hour = random.choice([random.randint(0, 5), random.randint(22, 23)])  # Night
            merchant = random.choice(["electronics", "jewelry", "cryptocurrency", "gambling"])
            is_new_device = random.random() < 0.7
        else:
            # Normal patterns
            amount = random.gauss(80, 40)
            amount = max(5, min(500, amount))
            country = np.random.choice(countries, p=country_probs_normal)
            hour = random.randint(8, 21)
            merchant = random.choice(["grocery", "restaurant", "retail", "travel"])
            is_new_device = random.random() < 0.1
        
        # Build transaction
        timestamp = datetime.utcnow() - timedelta(days=random.randint(0, 90))
        timestamp = timestamp.replace(hour=hour, minute=random.randint(0, 59))
        
        transaction = {
            "transaction_id": f"txn_{i}",
            "user_id": user_id,
            "amount": amount,
            "currency": "USD",
            "merchant_id": f"merch_{random.randint(1, 1000)}",
            "merchant_category": merchant,
            "timestamp": timestamp,
            "location": {
                "country": country,
                "city": "City",
                "latitude": random.uniform(-60, 70),
                "longitude": random.uniform(-180, 180),
            },
            "device": {
                "fingerprint": f"fp_{random.randint(1, 100) if not is_new_device else random.randint(10000, 99999)}",
                "type": random.choice(["desktop", "mobile"]),
            }
        }
        
        # Extract features
        features = feature_engineer.extract_features(transaction)
        features["is_fraud"] = 1 if is_fraud else 0
        features["transaction_id"] = transaction["transaction_id"]
        
        # Update user profile for next iteration
        feature_engineer.update_user_profile(user_id, transaction)
        
        data.append(features)
    
    df = pd.DataFrame(data)
    
    # Log class distribution
    fraud_count = df["is_fraud"].sum()
    logger.info(f"Generated {fraud_count} fraudulent transactions ({fraud_count/n_samples*100:.2f}%)")
    
    return df


def train_model(df: pd.DataFrame, save_path: str = "models"):
    """
    Train LightGBM model and SHAP explainer.
    
    Args:
        df: Training data with features and is_fraud label
        save_path: Directory to save model artifacts
    """
    logger.info("Starting model training...")
    
    # Prepare features
    feature_cols = FeatureEngineer.FEATURE_NAMES
    X = df[feature_cols].fillna(0)
    y = df["is_fraud"]
    
    # Train/test split (time-aware would be better in production)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"Training set: {len(X_train)} samples")
    logger.info(f"Test set: {len(X_test)} samples")
    
    # Calculate class weight for imbalanced data
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1
    
    logger.info(f"Class weight: {scale_pos_weight:.2f}")
    
    # Train LightGBM
    lgbm = LGBMClassifier(
        objective="binary",
        num_leaves=31,
        learning_rate=0.05,
        n_estimators=200,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbose=-1,
    )
    
    logger.info("Training LightGBM classifier...")
    lgbm.fit(X_train, y_train)
    
    # Calibrate probabilities
    logger.info("Calibrating probabilities...")
    calibrated = CalibratedClassifierCV(lgbm, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train)
    
    # Evaluate
    y_pred_proba = calibrated.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    avg_precision = average_precision_score(y_test, y_pred_proba)
    
    logger.info(f"\n=== Model Evaluation ===")
    logger.info(f"ROC-AUC: {roc_auc:.4f}")
    logger.info(f"Average Precision: {avg_precision:.4f}")
    logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
    logger.info(f"\nConfusion Matrix:\n{confusion_matrix(y_test, y_pred)}")
    
    # Feature importance
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": lgbm.feature_importances_
    }).sort_values("importance", ascending=False)
    
    logger.info(f"\nTop 10 Feature Importances:\n{importance.head(10)}")
    
    # Create SHAP explainer
    logger.info("Creating SHAP explainer...")
    explainer = shap.TreeExplainer(lgbm)
    
    # Test SHAP values
    shap_values = explainer.shap_values(X_test.iloc[:100])
    logger.info(f"SHAP values shape: {np.array(shap_values).shape}")
    
    # Save artifacts
    os.makedirs(save_path, exist_ok=True)
    
    model_path = os.path.join(save_path, "risk_model.joblib")
    explainer_path = os.path.join(save_path, "shap_explainer.joblib")
    metadata_path = os.path.join(save_path, "model_metadata.json")
    
    # Save model
    joblib.dump({
        "model": calibrated,
        "base_model": lgbm,
        "feature_names": feature_cols,
    }, model_path)
    logger.info(f"Model saved to {model_path}")
    
    # Save explainer
    joblib.dump(explainer, explainer_path)
    logger.info(f"Explainer saved to {explainer_path}")
    
    # Save metadata
    metadata = {
        "version": "1.0.0",
        "created_at": datetime.utcnow().isoformat(),
        "feature_names": feature_cols,
        "metrics": {
            "roc_auc": float(roc_auc),
            "average_precision": float(avg_precision),
        },
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_importance": importance.to_dict("records"),
    }
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to {metadata_path}")
    
    return calibrated, explainer, metadata


def main():
    """Main training pipeline."""
    logger.info("=== Atlas Model Training Pipeline ===")
    
    # Generate or load data
    data_path = "data/training_data.csv"
    
    if os.path.exists(data_path):
        logger.info(f"Loading existing data from {data_path}")
        df = pd.read_csv(data_path)
    else:
        logger.info("Generating synthetic training data...")
        df = generate_synthetic_data(n_samples=20000, fraud_rate=0.03)
        
        os.makedirs("data", exist_ok=True)
        df.to_csv(data_path, index=False)
        logger.info(f"Training data saved to {data_path}")
    
    # Train model
    model, explainer, metadata = train_model(df)
    
    logger.info("\n=== Training Complete ===")
    logger.info(f"Model ROC-AUC: {metadata['metrics']['roc_auc']:.4f}")
    
    return model, explainer


if __name__ == "__main__":
    main()
