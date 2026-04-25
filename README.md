## 🎥 Pitch Video

> **Watch here:** [Pitch Video (Fiveo'clock).mp4](https://drive.google.com/file/d/1Xv03Y41kQsAJ-fbI3TbD3Z37C_oDlt7M/view?usp=sharing)

# AdsGenerator — AI-Powered Advertising Strategy & Content Pipeline

AdsGenerator is an intelligent marketing dashboard that transforms product inventory data into high-performing advertising campaigns. It analyzes inventory risk, gathers real-time market context via web-search enabled AI, and generates tailored ad creative (copy and visuals) using the Ilmu GLM 5.1 ecosystem.

## 🚀 Key Features

- **Inventory Risk Analysis**: Deterministic scoring based on stock levels, expiry dates, and capital exposure.
- **Live Market Context**: Real-time gathering of trending ad formats, platform CPMs, and upcoming events in target regions using **Ilmu GLM 5.1** web-search.
- **AI Strategy Proposer**: Generates diverse, data-driven marketing strategies (product, platform, audience, angle).
- **Creative Generation**: Automated generation of ad headlines, captions, hashtags, and AI-generated visuals via **Z.AI (GLM-Image)**.
- **Smart Rationale**: Provides financial and marketing justification for every generated ad.
- **Persistence**: Full history tracking and campaign management backed by Google Firestore.

## 🧠 AI Pipeline Explained

AdsGenerator uses AI in a staged pipeline so each output builds on the previous step.

### 1) Market Context Collector (Ilmu GLM 5.1 + Web Search)

- **Purpose**: Pull fresh market signals before strategy generation.
- **Inputs**: Region/area, product categories, and campaign intent.
- **What AI does**: Searches for current trends, ad formats, estimated CPM ranges, and upcoming local events.
- **Outputs**: Structured market context that is passed to downstream strategy and copy generation.

### 2) Strategy Generator (Ilmu GLM 5.1 Text)

- **Purpose**: Turn inventory and market context into practical campaign options.
- **Inputs**: Inventory risk analysis, product metadata, and market context.
- **What AI does**: Produces multiple campaign strategies with channel recommendations, audience targets, and messaging angles.
- **Outputs**: Ranked or selectable strategy candidates for creative production.

### 3) Copy Generator (Ilmu GLM 5.1 Text)

- **Purpose**: Create platform-ready ad text.
- **Inputs**: Selected strategy + product information + campaign constraints.
- **What AI does**: Writes headlines, primary captions, hooks, CTA variants, and hashtags aligned to the chosen angle.
- **Outputs**: Reusable ad copy variants for social and paid channels.

### 4) Visual Generator (Z.AI / GLM-Image)

- **Purpose**: Produce ad visuals that match the campaign message.
- **Inputs**: Creative direction from strategy and generated copy cues.
- **What AI does**: Converts prompts into image assets designed for ad use.
- **Outputs**: AI-generated visual creatives paired with text variants.

### 5) Rationale & Decision Support (Ilmu GLM 5.1 Text)

- **Purpose**: Explain _why_ each campaign output is recommended.
- **Inputs**: Strategy, copy, visual intent, and inventory/business context.
- **What AI does**: Generates concise marketing and financial justification (for example, urgency due to stock/expiry risk or expected audience fit).
- **Outputs**: Human-readable rationale to help teams approve and iterate quickly.

### 6) Human-in-the-Loop Review

- **Purpose**: Keep quality and brand consistency high.
- **How it works**: Users review AI outputs, compare options, and finalize the campaign package before launch.
- **Benefit**: AI accelerates ideation and drafting, while humans control final brand and compliance decisions.

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
