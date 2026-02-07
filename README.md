
# 🎯 Atlas AI - Behavioral Risk Intelligence System

## 🚨 The Problem

Trading platforms lose **millions** to:
- Emotional trading (revenge trading after losses)
- Account takeover fraud
- Pattern abuse
- Underage gambling

**Current solutions:** Basic rule-based systems that catch only 30% of risky behavior.

## 💡 Our Solution

**Atlas AI** uses explainable machine learning to detect risky behavior **before** financial damage occurs.

### Key Features
- ⚡ **Real-time Detection** - Analyzes behavior in milliseconds
- 🧠 **Explainable AI** - Clear reasons for every alert (SHAP values)
- 📊 **Risk Scoring** - Precise 0-1 risk score with confidence levels
- 🎯 **Smart Actions** - Recommends cooldowns, limits, or alerts
- 📈 **Adaptive Learning** - Improves with every interaction

## 🛠️ Tech Stack

**Machine Learning:**
- Isolation Forest (anomaly detection)
- XGBoost (risk scoring)
- SHAP (explainability)

**Backend:**
- FastAPI (Python 3.11)
- Pydantic (data validation)

**Frontend:**
- React 18 + Vite
- Chart.js (visualizations)

## 🚀 Quick Start

# Atlas - Explainable AI Fraud Detection System

A production-grade, explainable AI system for real-time financial risk and fraud detection. Atlas analyzes transaction patterns, assigns risk scores with millisecond-level latency, and provides crystal-clear explanations that satisfy both end-users and regulatory auditors.

## Features

- **Real-Time Risk Scoring**: Score transactions in <100ms with 0-100 risk scores
- **SHAP-Based Explainability**: Full transparency into model decisions using SHapley Additive exPlanations
- **Three-Tier Explanations**:
  - **Technical**: SHAP values, feature values for compliance teams
  - **Business**: Analyst-friendly summaries with risk factors
  - **User**: Simple language explanations for cardholders
- **Interactive Dashboard**: Modern Next.js dashboard with real-time updates
- **Audit Trail**: Immutable logging for regulatory compliance
- **30+ Fraud Detection Features**: Comprehensive feature engineering

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **LightGBM** for gradient boosting classification
- **SHAP** for model interpretability
- **PostgreSQL** for data persistence
- **Redis** for caching

### Frontend
- **Next.js 14** with App Router
- **React 18** with TypeScript
- **Tailwind CSS** + custom design system
- **Recharts** for data visualization
- **TanStack Query** for data fetching

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
  

### Installation
```bash
# 1. Clone repository
git clone https://github.com/your-team/atlas-ai.git
cd atlas-ai

# 2. Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Generate synthetic data
python data/synthetic/generate_data.py

# 4. Train models
python models/train.py

# 5. Start API
cd src/api
uvicorn main:app --reload --port 8000

# 6. Start Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Access
- **Frontend Dashboard:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

## 📊 Demo

### Example: Detecting Emotional Trading

**Input:**
```json
{
  "trades_count": 47,
  "loss_streak": 6,
  "session_duration_hours": 8.5,
  "avg_trade_size": 850
}
```

**Output:**
```json
{
  "risk_score": 0.89,
  "risk_level": "HIGH",
  "is_anomaly": true,
  "explanation": {
    "top_factors": [
      {"feature": "loss_streak", "impact": 0.42},
      {"feature": "trades_count", "impact": 0.31},
      {"feature": "session_duration_hours", "impact": 0.16}
    ]
  },
  "recommended_action": "Immediate 30-min cooldown + support outreach"
}
```

## 🎯 Business Impact

- **Reduce emotional trading losses by 60%**
- **Detect fraud 10x faster** than rule-based systems
- **Improve user retention** through protective interventions
- **Regulatory compliance** with explainable decisions

## 🏗️ Architecture
```
User Actions → Feature Extraction → ML Models → Risk Score → Action
                                    ├─ Isolation Forest
                                    ├─ XGBoost Scorer
                                    └─ SHAP Explainer
```



## Team Roles

- **MADIEGA S AIDA JUSTINE ** – ML Engineer  
  Responsible for deployment, testing, and bug fixing to ensure Atlas AI runs reliably in production.

- **DEMILADE AYEKU ** – Full Stack Developer  
  Developed the backend and frontend of Atlas AI, handling APIs, database models, and user interface integration.


## 📄 License

MIT License - Built for Deriv AI Talent Sprint 2025

---

**Made with ❤️ for safer trading platforms**
=======
- Docker & Docker Compose (optional)

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access the app
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

1. **Start Infrastructure**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

2. **Backend Setup**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```

3. **Generate Demo Data**
```bash
cd backend
python scripts/generate_demo_data.py
```

4. **Frontend Setup**
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

5. **Access the App**
- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Project Structure

```
atlas/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── ml/            # ML model training and inference
│   │   ├── models/        # Pydantic schemas & DB models
│   │   └── services/      # Business logic services
│   ├── scripts/           # Utility scripts
│   ├── models/            # Saved ML models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   └── lib/           # Utilities & API client
│   └── package.json
├── docker-compose.yml     # Production setup
└── docker-compose.dev.yml # Development setup
```

## API Endpoints

### Risk Scoring
- `POST /api/v1/score` - Score a single transaction
- `POST /api/v1/score/batch` - Score multiple transactions

### Transactions
- `GET /api/v1/transactions` - List scored transactions
- `GET /api/v1/transactions/{id}` - Get transaction detail

### Explanations
- `GET /api/v1/explain/{id}` - Get full explanation for a transaction

### Dashboard
- `GET /api/v1/dashboard/stats` - Get dashboard statistics

### Demo
- `POST /api/v1/demo/generate` - Generate demo transactions

## Feature Engineering

Atlas extracts 30 features from each transaction:

| Category | Features |
|----------|----------|
| Monetary | amount, amount_zscore, is_round_amount |
| Temporal | hour, day_of_week, is_weekend, is_night |
| Velocity | txn_count_1h, txn_count_24h, velocity_score |
| Location | country_risk, distance_from_last, is_new_country |
| Device | is_new_device, device_age_days |
| Merchant | merchant_category_risk, is_high_risk_merchant |
| Behavior | amount_vs_avg_ratio, behavior_anomaly_score |

## Model Training

Train a new model with your data:

```bash
cd backend
python -m app.ml.train
```

This will:
1. Generate synthetic training data (or use your own)
2. Train a LightGBM classifier with class balancing
3. Calibrate probabilities
4. Create SHAP explainer
5. Save model artifacts to `models/`

## Configuration

### Environment Variables

**Backend (`backend/.env`)**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/atlas
REDIS_URL=redis://localhost:6379/0
DEBUG=false
```

**Frontend (`frontend/.env.local`)**
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Design System

The UI uses a dark theme with semantic risk colors:

```css
/* Risk Levels */
--risk-critical: #DC2626  /* 80-100 */
--risk-high: #F59E0B      /* 60-79 */
--risk-medium: #FCD34D    /* 40-59 */
--risk-low: #10B981       /* 0-39 */

/* Theme */
--background: #0A0E27
--surface: #141B3D
```

## Hackathon Simplifications

This MVP version excludes enterprise features:
- ❌ Kafka event streaming (using REST API)
- ❌ Neo4j graph database (skipping fraud ring detection)
- ❌ Kubernetes/Helm (using Docker Compose)
- ❌ Feature store (inline feature engineering)
- ❌ Triton Inference Server (direct Python inference)

## Authors

- **MADIEGA S AIDA JUSTINE** - Lead Developer
- **DEMILADE AYEKU** - Collaborator

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- SHAP library for model interpretability
- LightGBM for efficient gradient boosting
- Kaggle Credit Card Fraud Detection dataset for inspiration

