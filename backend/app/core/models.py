import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base # database.py থেকে Base ইমপোর্ট করা হয়েছে

class User(Base):
    __tablename__ = "users"

    # Supabase Auth এর UUID টাই এখানে প্রাইমারি কি হিসেবে বসবে
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship: একজন ইউজারের অনেকগুলো ওয়ার্কস্পেস থাকতে পারে
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False) # e.g., "IR", "Personal", "Projects"
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship: একটি ওয়ার্কস্পেস নির্দিষ্ট একজন ইউজারের আন্ডারে থাকবে
    owner = relationship("User", back_populates="workspaces")