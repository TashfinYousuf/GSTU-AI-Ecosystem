from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, workspaces, chat, knowledge, documents, admin, mentor, payment, powerups
from app.api import academic

# Initialize FastAPI App
app = FastAPI(
    title="GSTU AI Ecosystem API", 
    version="2.0",
    description="The Headless Engine powering GSTU AI Web and Mobile Platforms."
)

# CORS Middleware (Allows Next.js and Flutter to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Next.js এর পোর্ট অ্যালাউ করা হলো
    # allow_origins=["*"], # প্রোডাকশনে এখানে Next.js এর ডোমেইন দেব
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"]) 
app.include_router(academic.router, prefix="/api/v1/academic", tags=["Academic Tools"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["Workspaces"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["AI Engine"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents & RAG"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin & Analytics"])
app.include_router(mentor.router, prefix="/api/v1/mentor", tags=["Agentic Mentor"])
app.include_router(payment.router, prefix="/api/v1/billing", tags=["Enterprise Billing"])
app.include_router(powerups.router, prefix="/api/v1/powerups", tags=["Power-Ups & Gen-Z Tools"])

@app.get("/")
async def root():
    return {
        "message": "GSTU AI Core Engine is Online! 🚀", 
        "status": "Healthy",
        "architecture": "FastAPI + SQLAlchemy"
    }