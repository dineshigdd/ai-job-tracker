import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine, Base
from sqlalchemy import text
from app import models  # noqa: F401  — registers every table on Base.metadata
from app.routers import jobs, users , auth , resumes , dashboard , match_score


# Lifespan event handler for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("🟢 SUCCESS: FastAPI backend successfully connected to PostgreSQL database!")
        # Managed Postgres (Render) starts empty and this project has no migration
        # tool, so create any missing tables here. Existing tables are left alone.
        Base.metadata.create_all(bind=engine)
        print("🟢 SUCCESS: Database schema is up to date.")
    except Exception as e:
        print(f"❌ ERROR: Could not connect to database on startup: {e}")
        traceback.print_exc()

    yield
    
    # --- Shutdown logic (if any) ---
    print("🔴 Shutting down backend application...")

# Initialize FastAPI app with the lifespan handler
app = FastAPI(
    title="AI-Powered Job Application Tracker API",
    version="1.0.0",
    lifespan=lifespan
)

# --- CORS MIDDLEWARE CONFIGURATION ---
# An Origin is scheme + host + port only — never a path, so no "/api" suffix here.
origins = [
    "https://ai-job-tracker-eosin.vercel.app",
    "http://localhost:3000",   # React dev server
    "http://localhost:5173",   # Vite dev server
    "http://127.0.0.1:8000",  # Alternative local address
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Regex allows any preview deployment under your Vercel project domain
    allow_origin_regex=r"https://ai-job-tracker-.*\.vercel\.app", 
    allow_credentials=True,
    allow_methods=["*"],   # Essential for OPTIONS, POST, PUT, DELETE, etc.
    allow_headers=["*"],   # Essential for Content-Type, Authorization, etc.
)


# Starlette's built-in 500 handler sits OUTSIDE CORSMiddleware, so an unhandled
# exception returns a bare "Internal Server Error" with no Access-Control-Allow-Origin
# header — which the browser reports as a CORS failure, hiding the real crash.
# Registering a handler routes 500s back through the middleware stack so the
# response carries CORS headers and the frontend sees the actual status.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled error on {request.method} {request.url.path}: {exc!r}")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def read_root():
    return {"message": "Welcome to the AI-Powered Job Application Tracker API!"}


@app.get("/api/health/db", tags=["Health"])
def health_db():
    """Diagnostic endpoint to verify database connectivity."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503, 
            content={"status": "unhealthy", "database": "disconnected"}
        )

app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
# app.include_router(match_score.router, prefix="/api/jobs", tags=["Match Score"])


# app.include_router(jobs.router)
# app.include_router(users.router)
# app.include_router(auth.router)
# app.include_router(resumes.router)
# app.include_router(dashboard.router)
# # Shares the /jobs prefix with jobs.router. No conflict: a path parameter never spans a
# # "/", so /jobs/{job_id} cannot swallow /jobs/{job_id}/match-score.
# app.include_router(match_score.router)