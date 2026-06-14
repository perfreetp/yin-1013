from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), index=True)
    phone = Column(String(20), unique=True, index=True)
    badge_number = Column(String(50), unique=True, index=True)
    role = Column(String(20), default="inspector", nullable=False)
    department = Column(String(100))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)
    is_new_user = Column(Boolean, default=True, nullable=False)
    onboarding_step = Column(Integer, default=0)
    cases_handled = Column(Integer, default=0)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_cases = relationship("Case", foreign_keys="Case.created_by", back_populates="creator")
    assigned_cases = relationship("Case", foreign_keys="Case.assigned_to", back_populates="assignee")
    handled_cases = relationship("Case", foreign_keys="Case.handled_by", back_populates="handler")
    operations = relationship("CaseOperation", back_populates="operator")
