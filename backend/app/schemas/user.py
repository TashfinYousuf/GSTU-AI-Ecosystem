from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

# Base properties (সব জায়গায় লাগবে)
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "Student"

# API তে ডেটা রিসিভ করার জন্য (Create/Sync)
class UserCreate(UserBase):
    id: uuid.UUID  # Supabase Auth থেকে পাওয়া আসল ID

# API থেকে ডেটা রিটার্ন করার জন্য (Response)
class UserResponse(UserBase):
    id: uuid.UUID
    subscription_tier: str
    is_active: bool
    created_at: datetime

    # Pydantic V2 তে ORM (SQLAlchemy) ডেটা পড়ার নিয়ম
    class Config:
        from_attributes = True