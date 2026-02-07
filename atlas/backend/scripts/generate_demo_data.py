#!/usr/bin/env python3
"""
Demo Data Generation Script
Generates synthetic transaction data for Atlas demo
"""
import os
import sys
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.database import Base, TransactionRecord, RiskAssessmentRecord, AuditLogRecord, UserProfile
from app.services.risk_scorer import RiskScorer
from app.services.audit_logger import AuditLogger
import uuid


# Configuration
from app.config import settings
DATABASE_URL = settings.database_url
NUM_TRANSACTIONS = 200
FRAUD_RATE = 0.05


async def main():
    print("=" * 50)
    print("Atlas Demo Data Generator")
    print("=" * 50)
    
    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created")
    
    # Create session
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Initialize services
    risk_scorer = RiskScorer()
    audit_logger = AuditLogger()
    
    # Countries and their probabilities
    countries_normal = ["US", "CA", "GB", "DE", "FR", "AU", "JP"]
    countries_fraud = ["NG", "RU", "CN", "BR"]
    
    merchant_categories = ["grocery", "restaurant", "retail", "electronics", 
                          "jewelry", "travel", "entertainment", "utilities"]
    
    # Generate user IDs
    user_ids = [f"user_{i:03d}" for i in range(50)]
    
    print(f"\nGenerating {NUM_TRANSACTIONS} transactions...")
    
    transactions_created = 0
    fraud_count = 0
    
    async with async_session() as session:
        for i in range(NUM_TRANSACTIONS):
            is_fraud = random.random() < FRAUD_RATE
            user_id = random.choice(user_ids)
            
            if is_fraud:
                fraud_count += 1
                # Fraudulent patterns
                amount = random.choice([
                    random.uniform(500, 5000),
                    random.randint(1, 10) * 100,
                    random.uniform(50, 200),
                ])
                country = random.choice(countries_fraud)
                hour = random.choice([0, 1, 2, 3, 4, 22, 23])
                category = random.choice(["electronics", "jewelry", "cryptocurrency"])
                is_new_device = random.random() < 0.8
            else:
                # Normal patterns
                amount = max(5, random.gauss(100, 50))
                country = random.choice(countries_normal)
                hour = random.randint(8, 21)
                category = random.choice(merchant_categories[:6])
                is_new_device = random.random() < 0.1
            
            # Generate timestamp (last 7 days)
            timestamp = datetime.now() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            timestamp = timestamp.replace(hour=hour)
            
            # Build transaction
            txn_id = f"txn_{uuid.uuid4().hex[:12]}"
            
            transaction = {
                "transaction_id": txn_id,
                "user_id": user_id,
                "amount": round(amount, 2),
                "currency": "USD",
                "merchant_id": f"merch_{random.randint(1, 500)}",
                "merchant_category": category,
                "timestamp": timestamp,
                "location": {
                    "country": country,
                    "city": f"City_{random.randint(1, 100)}",
                    "latitude": random.uniform(25, 55),
                    "longitude": random.uniform(-120, 40),
                },
                "device": {
                    "fingerprint": f"fp_{random.randint(10000, 99999) if is_new_device else random.randint(1, 100)}",
                    "type": random.choice(["desktop", "mobile"]),
                }
            }
            
            # Score transaction (async method)
            assessment = await risk_scorer.score_transaction(transaction)
            
            # Store in database
            location = transaction["location"]
            device = transaction["device"]
            
            txn_record = TransactionRecord(
                id=txn_id,
                user_id=transaction["user_id"],
                amount=transaction["amount"],
                currency=transaction["currency"],
                merchant_id=transaction["merchant_id"],
                merchant_category=transaction["merchant_category"],
                location_country=location["country"],
                location_city=location["city"],
                location_lat=location["latitude"],
                location_lon=location["longitude"],
                device_fingerprint=device["fingerprint"],
                device_type=device["type"],
                timestamp=timestamp,
            )
            session.add(txn_record)
            
            assessment_record = RiskAssessmentRecord(
                id=f"assess_{uuid.uuid4().hex[:12]}",
                transaction_id=txn_id,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level.value,
                confidence=assessment.confidence,
                recommended_action=assessment.recommended_action.value,
                model_version="1.0.0",
                processing_time_ms=assessment.processing_time_ms,
                top_factors=[f.model_dump() for f in assessment.top_factors] if assessment.top_factors else [],
            )
            session.add(assessment_record)
            
            # Create audit log
            audit_record = audit_logger.create_decision_log(
                transaction_id=txn_id,
                risk_assessment=assessment,
                action="score",
                ip_address="127.0.0.1"
            )
            session.add(audit_record)
            
            transactions_created += 1
            
            if (i + 1) % 50 == 0:
                await session.commit()
                print(f"  Progress: {i + 1}/{NUM_TRANSACTIONS}")
        
        # Final commit
        await session.commit()
    
    print(f"\n✓ Created {transactions_created} transactions")
    print(f"  - Normal: {transactions_created - fraud_count}")
    print(f"  - Fraudulent patterns: {fraud_count} ({fraud_count/transactions_created*100:.1f}%)")
    
    # Print risk distribution
    async with async_session() as session:
        from sqlalchemy import select, func
        
        result = await session.execute(
            select(
                RiskAssessmentRecord.risk_level,
                func.count(RiskAssessmentRecord.id)
            ).group_by(RiskAssessmentRecord.risk_level)
        )
        
        print("\nRisk Distribution:")
        for level, count in result:
            print(f"  - {level}: {count}")
    
    print("\n" + "=" * 50)
    print("Demo data generation complete!")
    print("Start the API server and frontend to view the dashboard")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
