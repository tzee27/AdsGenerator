# AdsGenerator — AI-Powered Advertising Strategy & Content Pipeline

AdsGenerator is an intelligent marketing dashboard that transforms product inventory data into high-performing advertising campaigns. It analyzes inventory risk, gathers real-time market context via web-search enabled AI, and generates tailored ad creative (copy and visuals) using the Ilmu GLM 5.1 ecosystem.

## 🚀 Key Features

- **Inventory Risk Analysis**: Deterministic scoring based on stock levels, expiry dates, and capital exposure.
- **Live Market Context**: Real-time gathering of trending ad formats, platform CPMs, and upcoming events in target regions using **Ilmu GLM 5.1** web-search.
- **AI Strategy Proposer**: Generates diverse, data-driven marketing strategies (product, platform, audience, angle).
- **Creative Generation**: Automated generation of ad headlines, captions, hashtags, and AI-generated visuals via **Z.AI (GLM-Image)**.
- **Smart Rationale**: Provides financial and marketing justification for every generated ad.
- **Persistence**: Full history tracking and campaign management backed by Google Firestore.

## 🛠️ Tech Stack

- **Frontend**: React, Vite, CSS (Vanilla), Firebase Auth & Firestore.
- **Backend**: FastAPI, Pydantic, httpx.
- **AI Integration**: Ilmu GLM 5.1 (Text & Web Search), Z.AI (Image Generation).

## 📂 Project Structure

```text
AdsGenerator/
├── backend/            # FastAPI Backend
│   ├── app/            # Core logic, services, and API routes
│   ├── tests/          # Comprehensive unit & integration tests
│   └── .env            # Backend configuration (AI keys, Area)
└── frontend/           # React Frontend
    ├── src/            # Components, pages, and logic
    ├── public/         # Static assets
    └── .env            # Frontend configuration (API URL, Firebase)
```

## 🚥 Getting Started

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
# Create .env based on .env.example with your ILMU_API_KEY and ZAI_API_KEY
uvicorn app.main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
# Create .env based on .env.example with your VITE_FIREBASE_* keys
npm run dev
```

## 🔒 Security
- Ensure `.env` and `firebase-credentials.json` are **never** committed to version control (already configured in `.gitignore`).
- Use the provided `.env.example` files as templates for local configuration.
