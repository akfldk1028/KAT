from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, security, agents, secret

# Create DB tables (Optional for security-only backend, but keeping for now)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kanana DualGuard POC",
    description="양방향 보안 Agent API - 안심 전송 + 안심 가드",
    version="1.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(security.router, prefix="/api/security", tags=["security"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(secret.router, prefix="/api/secret", tags=["secret"])

@app.get("/")
def read_root():
    return {
        "message": "Kanana DualGuard Backend is running",
        "version": "1.0.0",
        "endpoints": {
            "analyze_outgoing": "/api/agents/analyze/outgoing",
            "analyze_incoming": "/api/agents/analyze/incoming",
            "secret_create": "/api/secret/create",
            "secret_view": "/api/secret/view/{secret_id}",
            "health": "/api/agents/health",
            "docs": "/docs"
        }
    }
