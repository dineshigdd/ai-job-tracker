from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from sqlalchemy import text
from app.routers import jobs, users , auth , resumes , dashboard , match_score


# Lifespan event handler for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("🟢 SUCCESS: FastAPI backend successfully connected to PostgreSQL database!")
    except Exception as e:
        print(f"❌ ERROR: Could not connect to database on startup: {e}")
    
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
origins = [
    "http://localhost:3000",   # React dev server
    "http://127.0.0.1:8000",  # Alternative local address
    # Add your production domain here when deploying (e.g., "https://myapp.com")
]

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI-Powered Job Application Tracker API!"}

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