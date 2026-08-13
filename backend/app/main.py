from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine
from sqlalchemy import text
from app.routers import jobs, users , auth , resumes , dashboard


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

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI-Powered Job Application Tracker API!"}

app.include_router(jobs.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(dashboard.router)