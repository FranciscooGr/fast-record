# 🚀 FastRecord

FastRecord is a modern, full-stack financial tracking system designed for frictionless expense and income management. It allows users to register their financial movements seamlessly through a **WhatsApp Bot** and visualizes their financial health via a robust **React-based PWA Dashboard**.

The project is built on a highly optimized architecture featuring a hybrid NLP model (**Go fast with Regex, fallback to Groq LLMs**) and a resilient async **FastAPI** + **PostgreSQL** backend.

---

## 🏗 System Architecture

The application is strictly divided into two distinct domains:

### 1. Backend (`/backend`)
A high-performance Python ASYNC backend built with:
- **Framework**: FastAPI (async/await, dependency injection, high concurrency).
- **Database**: PostgreSQL with SQLAlchemy V2 (async) and Alembic for declarative database migrations.
- **NLP Engine**: Hybrid strategy using Regex deterministic paths + Groq API for advanced natural language understanding. (Fallback ready for Gemini).
- **Authentication**: JWT-based authentication for the dashboard.
- **Testing**: Comprehensive Pytest suite covering webhook handlers, LLM endpoints, and API contracts.

### 2. Frontend (`/frontend`)
A progressive, mobile-first Web App (PWA) built with:
- **Framework**: React 19 with Vite.
- **Styling**: Tailwind CSS for responsive, accessible, and fast UI design.
- **Data Visualization**: Recharts for dynamic visual representations of finances (Income vs. Expenses).
- **Icons**: Lucide React.
- **Architecture**: Clear separation of API services, DTO types, and Dashboard UI components.

---

## ✨ Key Features

- **WhatsApp Webhook Integration**: Complete webhook management to receive, process, and acknowledge WhatsApp messages directly into the financial ledger.
- **Smart NLP Parsing**: 
  - *Fast Path*: Identifies deterministic messages (e.g., "+5000 sueldo") using optimized regex roots.
  - *Slow Path*: Uses Groq LLM to intelligently categorize ambiguous or conversational spending (e.g., "Me compré un café en el centro por 2000").
- **Dynamic Balance Calculation**: Ensuring strict data consistency, the "Balance" is never stored as a stagnant column. It is dynamically aggregated via SQL using the ledger of movements.
- **Responsive PWA Dashboard**: A fluid, modern dashboard delivering:
  - Real-time balance calculations.
  - Dynamic filtering by Day, Month, or Year.
  - Category-based breakdowns with Recharts.
  - Secure "Reset Account" mechanisms.

---

## ⚙️ Getting Started

### Prerequisites

- Node.js (v18+)
- Python (3.11+)
- PostgreSQL (Listening on port 5432)

### ▶️ Setting up the Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Environment Variables:
   Create a `.env` file (referencing `.env.example`) and fill in the database credentials, JWT secrets, and the **Groq API Key**.
5. Run Database Migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the API Server:
   ```bash
   fastapi run app/main.py --port 8000
   # or with uvicorn: uvicorn app.main:app --reload --port 8000
   ```
   *The Swagger UI will be available at [http://localhost:8000/docs](http://localhost:8000/docs)*

### ▶️ Setting up the Frontend

1. Navigate to the frontend window:
   ```bash
   cd frontend
   ```
2. Install NodeJS dependencies:
   ```bash
   npm install
   ```
3. Start the Vite Dev Server:
   ```bash
   npm run dev
   ```
   *The application will boot up at [http://localhost:5173](http://localhost:5173)*

---

## 🧪 Testing

The backend is built with Test-Driven Development (TDD) best practices.

To run the backend test suite:
```bash
cd backend
pytest -v
```

---

## 🤝 Rules of Engagement (Contribution Guidelines)

- **Domain Isolation**: Backend and Frontend components must never mix. Backend strictly handles data and API specs. Frontend handles solely presentation, visualization, and API consumption based on JSON DTO contracts.
- **Balance Calculation Rule**: *Nunca persistir una columna o tabla de saldo*. Balances must ALWAYS be queried and aggregated dynamically via raw logic.
- **Mobile First**: All frontend design must prioritize mobile viewing, later scaling to desktop.

---

**FastRecord** — Eliminating the friction of daily budget tracking.
