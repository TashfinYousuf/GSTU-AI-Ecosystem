from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID # 🟢 Supabase এর আসল ID Type
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class User(Base):
    __tablename__ = "users" 
    __table_args__ = {'extend_existing': True}

    # 🟢 String এর বদলে UUID দিলাম, যাতে Supabase এর সাথে কনফ্লিক্ট না হয়
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="Student") 
    subscription_tier = Column(String, default="free") 
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")

class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="workspaces")

    # Workspace ক্লাসের ভেতরে যোগ করুন
    messages = relationship("Message", back_populates="workspace", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False) # 'user' অথবা 'ai'
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # রিলেশনশিপ
    workspace = relationship("Workspace", back_populates="messages")

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    workspace = relationship("Workspace")