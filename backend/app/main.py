import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

from app.api import academic, account, admin, auth, billing, chat, department, documents, faculty, knowledge, logger, mentor, payment, powerups, scholar, study, tools, workspaces
# 🔴 1. Import SlowAPI for Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 🔴 2. Initialize Limiter (Tracks by User IP)
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI App
app = FastAPI(
    title="GSTU AI Ecosystem API", 
    version="2.0",
    description="The Headless Engine powering GSTU AI Web and Mobile Platforms."
)

# 🗜️ Compress all JSON payloads larger than 500 bytes (Reduces bandwidth by 70%)
app.add_middleware(GZipMiddleware, minimum_size=500)

# 🔴 3. Add Exception Handler for Rate Limits
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 🔴 Tell FastAPI to serve the "uploads" directory publicly
os.makedirs("uploads/avatars", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS Middleware (Allows Next.js and Flutter to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.1.2:3000", "https://gstu-ai-backend.vercel.app"], # Main domain অ্যালাউ করা হলো
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 🔴 FIX 2: Custom OPTIONS By-Pass Guard
# যদি অন্য কোনো সিস্টেম OPTIONS রিকোয়েস্ট আটকে দেয়, এই মিডলওয়্যার সেটা বাইপাস করে দেবে
@app.middleware("http")
async def options_bypass_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=200) # ডাইরেক্ট 200 OK দিয়ে ব্রাউজারকে শান্ত করবে
    return await call_next(request)

# 🔴 Production Health Check for Render / Railway
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "GSTU AI Backend Engine",
        "environment": os.getenv("RENDER_SERVICE_ID", "local_development")
    }


app.include_router(academic.router, prefix="/api/v1/academic", tags=["Academic Tools"])

app.include_router(account.router, prefix="/api/v1/account", tags=["Account"])

app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin & Analytics"])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

app.include_router(billing.router, prefix="/api/v1/billing", tags=["Enterprise Billing"])

app.include_router(chat.router, prefix="/api/v1/chat", tags=["AI Engine"])

app.include_router(department.router, prefix="/api/v1/department", tags=["Department Hub"])

app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents & RAG"])

app.include_router(faculty.router, prefix="/api/v1/faculty", tags=["Faculty Node"])

app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])

app.include_router(logger.router, prefix="/api/v1/logger", tags=["Study Logger"])

app.include_router(mentor.router, prefix="/api/v1/mentor", tags=["Agentic Mentor"])

app.include_router(payment.router, prefix="/api/v1/payment", tags=["Enterprise Payment"])

app.include_router(powerups.router, prefix="/api/v1/powerups", tags=["Power-Ups & Gen-Z Tools"])

app.include_router(scholar.router, prefix="/api/v1/scholar", tags=["Scholar Hub"])

app.include_router(study.router, prefix="/api/v1/study", tags=["Interactive Study Hub"])

app.include_router(tools.router, prefix="/api/v1/tools", tags=["Gen-Z Tools & Vision"])

app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["Workspaces"])

@app.get("/")
async def root():
    return {
        "message": "GSTU AI Core Engine is Online! 🚀", 
        "status": "Healthy",
        "architecture": "FastAPI + SQLAlchemy"
    }