# T1T2.ai — Your AI Examiner for IELTS Writing Tasks

T1T2.ai (formerly BandBoost) is an advanced, AI-powered platform designed to provide instant, highly accurate band scores and detailed, professional feedback for IELTS Writing Task 1 and Task 2. 

Powered by **Gemini 2.0 Flash** and **Gemini 3.0 Flash Preview**, T1T2.ai parses essays and charts (multimodal) to simulate an official IELTS examiner, providing scores strictly adhering to the official IELTS rubrics: Task Achievement/Response, Coherence & Cohesion, Lexical Resource, and Grammatical Range & Accuracy.

---

## Features

- **Multimodal Task 1 Evaluation**: Upload pie charts, bar graphs, process diagrams, or maps. The AI "sees" the image and evaluates your description just like a real examiner.
- **Strict Task 2 Grading**: Accurate band score approximation with 0.5 increment precision.
- **Detailed Feedback Pipeline**: Actionable feedback generated for each of the 4 IELTS criteria, alongside top 4 improvements.
- **Premium Dark UI**: Distraction-free, responsive, and beautiful Next.js frontend.
- **PDF Export**: Generate professional evaluation reports instantly.
- **History & Quotas**: Built-in daily rate limiting and persistent history of evaluations.

---

## Tech Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Authentication**: Supabase JWT Auth

### Backend
- **Framework**: Django 5 / Django REST Framework
- **Database**: PostgreSQL (via Supabase / Local Docker)
- **Message Broker / Cache**: Redis
- **Task Queue**: Celery (Background evaluations)
- **AI Integration**: Google Gemini API (`gemini-2.0-flash` and `gemini-3-flash-preview`)
- **PDF Generation**: xhtml2pdf

---

## Prerequisites

- Node.js 18+
- Python 3.10+
- Docker & Docker Compose (for PostgreSQL and Redis)
- Supabase Project (for Authentication)
- Google Gemini API Key

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/gajula21/ielts-task-1-evaluator.git
cd ielts-task-1-evaluator
```

### 2. Infrastructure (Database & Redis)
Start the local PostgreSQL and Redis containers using Docker Compose:
```bash
docker-compose up -d
```

### 3. Backend Setup
Navigate to the `backend` directory, set up your virtual environment, and install dependencies:
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory:
```env
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://bandboost_user:bandboost_password@localhost:5432/bandboost_db
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEYS=your-gemini-key-1,your-gemini-key-2
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Run migrations and start the Django server:
```bash
python manage.py migrate
python manage.py runserver
```

Start the Celery worker (in a new terminal, with venv activated):
```bash
# On Windows (requires --pool=solo):
celery -A myproject worker --loglevel=info --pool=solo

# On Linux/macOS:
celery -A myproject worker --loglevel=info
```

### 4. Frontend Setup
Navigate to the `frontend` directory and install dependencies:
```bash
cd ../frontend
npm install
```

Create a `.env.local` file in the `frontend` directory:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_SUPABASE_URL=https://your-supabase-url.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

Start the Next.js development server:
```bash
npm run dev
```

Visit `http://localhost:3000` to start using T1T2.ai.

---

## Production Deployment

This application is designed to be fully containerized. 
1. Use `backend/Dockerfile` to build the Django/Celery image.
2. Deploy the Next.js frontend to Vercel or a standard Node environment.
3. Ensure you provide a managed PostgreSQL database and Redis instance (e.g., DigitalOcean, AWS ElastiCache).
4. Set `DEBUG=False` in production and configure your `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.

---

## License

MIT License. See `LICENSE` for details.
