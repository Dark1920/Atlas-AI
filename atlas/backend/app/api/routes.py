"""
API Routes for Atlas Risk Scoring System
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import logging

from app.api.dependencies import (
    get_db, get_risk_scorer, get_explainer, get_audit_logger
)
from app.models.schemas import (
    TransactionCreate, Transaction, RiskAssessment, 
    TransactionListItem, TransactionListResponse,
    DashboardStats, RiskLevel, RecommendedAction,
    FullExplanation, AuditLogEntry
)
from app.models.database import (
    TransactionRecord, RiskAssessmentRecord, AuditLogRecord
)
from app.services.risk_scorer import RiskScorer
from app.services.explainer import ExplainabilityEngine
from app.services.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Risk Scoring"])


# ============ Scoring Endpoints ============

@router.post("/score", response_model=RiskAssessment)
async def score_transaction(
    transaction: TransactionCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Score a transaction for fraud risk.
    
    Returns real-time risk assessment with:
    - Risk score (0-100)
    - Risk level classification
    - Top contributing factors with SHAP explanations
    - Recommended action
    """
    # Generate transaction ID
    txn_id = f"txn_{uuid.uuid4().hex[:12]}"
    timestamp = transaction.timestamp or datetime.utcnow()
    
    # Build transaction dict for scoring
    txn_dict = {
        "transaction_id": txn_id,
        "user_id": transaction.user_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "merchant_id": transaction.merchant_id,
        "merchant_category": transaction.merchant_category,
        "timestamp": timestamp,
        "location": transaction.location.model_dump(),
        "device": transaction.device.model_dump(),
    }
    
    # Score transaction
    assessment = risk_scorer.score_transaction(txn_dict)
    
    # Store transaction and assessment in background
    background_tasks.add_task(
        store_transaction_and_assessment,
        db=db,
        transaction=txn_dict,
        assessment=assessment,
        audit_logger=audit_logger,
        ip_address=request.client.host if request.client else None
    )
    
    return assessment


@router.post("/score/batch", response_model=List[RiskAssessment])
async def score_transactions_batch(
    transactions: List[TransactionCreate],
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
):
    """
    Score multiple transactions in batch.
    
    Useful for bulk processing or testing.
    Limited to 100 transactions per request.
    """
    if len(transactions) > 100:
        raise HTTPException(
            status_code=400,
            detail="Batch size limited to 100 transactions"
        )
    
    assessments = []
    for txn in transactions:
        txn_dict = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": txn.user_id,
            "amount": txn.amount,
            "currency": txn.currency,
            "merchant_id": txn.merchant_id,
            "merchant_category": txn.merchant_category,
            "timestamp": txn.timestamp or datetime.utcnow(),
            "location": txn.location.model_dump(),
            "device": txn.device.model_dump(),
        }
        assessment = risk_scorer.score_transaction(txn_dict)
        assessments.append(assessment)
    
    return assessments


# ============ Transaction History Endpoints ============

@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: Optional[RiskLevel] = None,
    user_id: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List scored transactions with filtering and pagination.
    """
    # Build query
    query = select(TransactionRecord, RiskAssessmentRecord).join(
        RiskAssessmentRecord,
        TransactionRecord.id == RiskAssessmentRecord.transaction_id
    )
    
    # Apply filters
    if risk_level:
        query = query.where(RiskAssessmentRecord.risk_level == risk_level.value)
    if user_id:
        query = query.where(TransactionRecord.user_id == user_id)
    if min_score is not None:
        query = query.where(RiskAssessmentRecord.risk_score >= min_score)
    if max_score is not None:
        query = query.where(RiskAssessmentRecord.risk_score <= max_score)
    if start_date:
        query = query.where(TransactionRecord.timestamp >= start_date)
    if end_date:
        query = query.where(TransactionRecord.timestamp <= end_date)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(desc(TransactionRecord.timestamp))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Transform to response
    transactions = []
    for txn, assessment in rows:
        transactions.append(TransactionListItem(
            transaction_id=txn.id,
            user_id=txn.user_id,
            amount=txn.amount,
            currency=txn.currency,
            merchant_id=txn.merchant_id,
            merchant_category=txn.merchant_category or "",
            location_country=txn.location_country or "",
            timestamp=txn.timestamp,
            risk_score=assessment.risk_score,
            risk_level=RiskLevel(assessment.risk_level),
            recommended_action=RecommendedAction(assessment.recommended_action),
        ))
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
        has_more=total > page * page_size
    )


@router.get("/transactions/{transaction_id}", response_model=RiskAssessment)
async def get_transaction_detail(
    transaction_id: str,
    include_explanation: bool = True,
    db: AsyncSession = Depends(get_db),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
):
    """
    Get detailed risk assessment for a specific transaction.
    
    Includes full three-tier explanation if requested.
    """
    # Get transaction and assessment
    result = await db.execute(
        select(TransactionRecord, RiskAssessmentRecord)
        .join(RiskAssessmentRecord, TransactionRecord.id == RiskAssessmentRecord.transaction_id)
        .where(TransactionRecord.id == transaction_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    txn, assessment_record = row
    
    # Reconstruct transaction dict
    txn_dict = {
        "transaction_id": txn.id,
        "user_id": txn.user_id,
        "amount": txn.amount,
        "currency": txn.currency,
        "merchant_id": txn.merchant_id,
        "merchant_category": txn.merchant_category,
        "timestamp": txn.timestamp,
        "location": {
            "country": txn.location_country,
            "city": txn.location_city,
            "latitude": txn.location_lat,
            "longitude": txn.location_lon,
        },
        "device": {
            "fingerprint": txn.device_fingerprint,
            "type": txn.device_type,
        }
    }
    
    # Build response from stored data
    from app.models.schemas import FeatureContribution
    
    top_factors = []
    if assessment_record.top_factors:
        for f in assessment_record.top_factors:
            top_factors.append(FeatureContribution(**f))
    
    assessment = RiskAssessment(
        transaction_id=transaction_id,
        risk_score=assessment_record.risk_score,
        risk_level=RiskLevel(assessment_record.risk_level),
        confidence=assessment_record.confidence,
        recommended_action=RecommendedAction(assessment_record.recommended_action),
        processing_time_ms=assessment_record.processing_time_ms or 0,
        top_factors=top_factors,
    )
    
    # Add full explanation if requested
    if include_explanation:
        if assessment_record.explanation_technical:
            # Use stored explanation
            from app.models.schemas import (
                TechnicalExplanation, BusinessExplanation, 
                UserExplanation, RiskFactor
            )
            
            assessment.explanation = FullExplanation(
                technical=TechnicalExplanation(**assessment_record.explanation_technical),
                business=BusinessExplanation(
                    **{**assessment_record.explanation_business,
                       "top_factors": [RiskFactor(**f) for f in assessment_record.explanation_business.get("top_factors", [])]}
                ),
                user=UserExplanation(**assessment_record.explanation_user),
            )
        else:
            # Generate explanation on the fly
            assessment.explanation = risk_scorer.get_detailed_explanation(
                txn_dict, assessment
            )
    
    return assessment


# ============ Explanation Endpoints ============

@router.get("/explain/{transaction_id}", response_model=FullExplanation)
async def get_transaction_explanation(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
):
    """
    Get full three-tier explanation for a transaction.
    
    Returns:
    - Technical: SHAP values, feature values, model version
    - Business: Summary, top factors, comparison to baseline
    - User: Simple language explanation for cardholders
    """
    # Get transaction and assessment
    result = await db.execute(
        select(TransactionRecord, RiskAssessmentRecord)
        .join(RiskAssessmentRecord, TransactionRecord.id == RiskAssessmentRecord.transaction_id)
        .where(TransactionRecord.id == transaction_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    txn, assessment_record = row
    
    # Reconstruct for explanation generation
    txn_dict = {
        "transaction_id": txn.id,
        "user_id": txn.user_id,
        "amount": txn.amount,
        "currency": txn.currency,
        "merchant_id": txn.merchant_id,
        "merchant_category": txn.merchant_category,
        "timestamp": txn.timestamp,
        "location": {
            "country": txn.location_country,
            "city": txn.location_city,
            "latitude": txn.location_lat,
            "longitude": txn.location_lon,
        },
        "device": {
            "fingerprint": txn.device_fingerprint,
            "type": txn.device_type,
        }
    }
    
    assessment = RiskAssessment(
        transaction_id=transaction_id,
        risk_score=assessment_record.risk_score,
        risk_level=RiskLevel(assessment_record.risk_level),
        confidence=assessment_record.confidence,
        recommended_action=RecommendedAction(assessment_record.recommended_action),
        processing_time_ms=0,
        top_factors=[],
    )
    
    return risk_scorer.get_detailed_explanation(txn_dict, assessment)


# ============ Dashboard Endpoints ============

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard summary statistics.
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total transactions today
    txn_count_result = await db.execute(
        select(func.count(TransactionRecord.id))
        .where(TransactionRecord.timestamp >= today)
    )
    total_transactions = txn_count_result.scalar() or 0
    
    # Total amount today
    amount_result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .where(TransactionRecord.timestamp >= today)
    )
    total_amount = amount_result.scalar() or 0
    
    # Fraud detected (high/critical risk)
    fraud_result = await db.execute(
        select(func.count(RiskAssessmentRecord.id))
        .join(TransactionRecord, RiskAssessmentRecord.transaction_id == TransactionRecord.id)
        .where(TransactionRecord.timestamp >= today)
        .where(RiskAssessmentRecord.risk_level.in_(["high", "critical"]))
    )
    fraud_detected = fraud_result.scalar() or 0
    
    # Amount blocked
    blocked_result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .join(RiskAssessmentRecord, TransactionRecord.id == RiskAssessmentRecord.transaction_id)
        .where(TransactionRecord.timestamp >= today)
        .where(RiskAssessmentRecord.recommended_action == "block")
    )
    blocked_amount = blocked_result.scalar() or 0
    
    # Average risk score
    avg_score_result = await db.execute(
        select(func.avg(RiskAssessmentRecord.risk_score))
        .join(TransactionRecord, RiskAssessmentRecord.transaction_id == TransactionRecord.id)
        .where(TransactionRecord.timestamp >= today)
    )
    avg_score = avg_score_result.scalar() or 0
    
    # Distribution by risk level
    level_result = await db.execute(
        select(
            RiskAssessmentRecord.risk_level,
            func.count(RiskAssessmentRecord.id)
        )
        .join(TransactionRecord, RiskAssessmentRecord.transaction_id == TransactionRecord.id)
        .where(TransactionRecord.timestamp >= today)
        .group_by(RiskAssessmentRecord.risk_level)
    )
    
    by_risk_level = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for level, count in level_result:
        by_risk_level[level] = count
    
    # False positive rate (simplified - would need actual labels)
    false_positive_rate = 0.02  # Placeholder
    
    return DashboardStats(
        total_transactions_today=total_transactions,
        total_amount_today=total_amount,
        fraud_detected_today=fraud_detected,
        fraud_amount_blocked=blocked_amount,
        average_risk_score=round(avg_score, 1),
        false_positive_rate=false_positive_rate,
        transactions_by_risk_level=by_risk_level
    )


# ============ Audit Endpoints ============

@router.get("/audit/{transaction_id}", response_model=List[AuditLogEntry])
async def get_audit_trail(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete audit trail for a transaction.
    """
    result = await db.execute(
        select(AuditLogRecord)
        .where(AuditLogRecord.transaction_id == transaction_id)
        .order_by(AuditLogRecord.timestamp)
    )
    
    records = result.scalars().all()
    
    return [
        AuditLogEntry(
            id=r.id,
            transaction_id=r.transaction_id,
            timestamp=r.timestamp,
            action=r.action,
            risk_score=r.risk_score,
            model_version=r.model_version or "",
            operator_id=r.actor_id,
            notes=r.reason,
        )
        for r in records
    ]


# ============ Demo Data Endpoint ============

@router.post("/demo/generate")
async def generate_demo_data(
    count: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
):
    """
    Generate demo transactions for testing.
    """
    import random
    
    generated = []
    
    for i in range(count):
        is_fraud = random.random() < 0.05  # 5% fraud rate
        
        if is_fraud:
            amount = random.uniform(500, 5000)
            country = random.choice(["NG", "RU", "CN"])
            hour = random.choice([2, 3, 4, 23])
            category = random.choice(["electronics", "jewelry", "cryptocurrency"])
        else:
            amount = random.gauss(80, 40)
            amount = max(5, min(300, amount))
            country = random.choice(["US", "CA", "GB", "DE"])
            hour = random.randint(9, 20)
            category = random.choice(["grocery", "restaurant", "retail"])
        
        timestamp = datetime.utcnow() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        txn = TransactionCreate(
            user_id=f"user_{random.randint(1, 100):03d}",
            amount=round(amount, 2),
            currency="USD",
            merchant_id=f"merch_{random.randint(1, 500)}",
            merchant_category=category,
            location={
                "country": country,
                "city": "City",
                "latitude": random.uniform(25, 55),
                "longitude": random.uniform(-120, 40),
            },
            device={
                "fingerprint": f"fp_{random.randint(1, 1000)}",
                "type": random.choice(["desktop", "mobile"]),
            },
            timestamp=timestamp
        )
        
        txn_dict = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            **txn.model_dump()
        }
        txn_dict["location"] = txn.location.model_dump()
        txn_dict["device"] = txn.device.model_dump()
        
        assessment = risk_scorer.score_transaction(txn_dict)
        
        # Store in database
        await store_transaction_and_assessment(
            db=db,
            transaction=txn_dict,
            assessment=assessment,
            audit_logger=AuditLogger(),
            ip_address="127.0.0.1"
        )
        
        generated.append({
            "transaction_id": txn_dict["transaction_id"],
            "risk_score": assessment.risk_score,
            "is_fraud": is_fraud
        })
    
    return {
        "generated": count,
        "samples": generated[:10]
    }


# ============ Helper Functions ============

async def store_transaction_and_assessment(
    db: AsyncSession,
    transaction: dict,
    assessment: RiskAssessment,
    audit_logger: AuditLogger,
    ip_address: Optional[str] = None
):
    """Store transaction and assessment in database."""
    try:
        # Create transaction record
        location = transaction.get("location", {})
        device = transaction.get("device", {})
        
        txn_record = TransactionRecord(
            id=transaction["transaction_id"],
            user_id=transaction["user_id"],
            amount=transaction["amount"],
            currency=transaction.get("currency", "USD"),
            merchant_id=transaction["merchant_id"],
            merchant_category=transaction.get("merchant_category"),
            location_country=location.get("country"),
            location_city=location.get("city"),
            location_lat=location.get("latitude"),
            location_lon=location.get("longitude"),
            device_fingerprint=device.get("fingerprint"),
            device_type=device.get("type"),
            timestamp=transaction.get("timestamp", datetime.utcnow()),
        )
        
        db.add(txn_record)
        
        # Create assessment record
        assessment_record = RiskAssessmentRecord(
            id=f"assess_{uuid.uuid4().hex[:12]}",
            transaction_id=transaction["transaction_id"],
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level.value,
            confidence=assessment.confidence,
            recommended_action=assessment.recommended_action.value,
            model_version="1.0.0",
            processing_time_ms=assessment.processing_time_ms,
            top_factors=[f.model_dump() for f in assessment.top_factors] if assessment.top_factors else [],
        )
        
        db.add(assessment_record)
        
        # Create audit log
        audit_record = audit_logger.create_decision_log(
            transaction_id=transaction["transaction_id"],
            risk_assessment=assessment,
            action="score",
            ip_address=ip_address
        )
        
        db.add(audit_record)
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error storing transaction: {e}")
        await db.rollback()
        raise
