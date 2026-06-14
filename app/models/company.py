from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.session import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), unique=True, index=True, nullable=False)
    unified_social_credit = Column(String(50), unique=True, index=True)
    legal_person = Column(String(50))
    legal_person_phone = Column(String(20))
    contact_person = Column(String(50))
    contact_phone = Column(String(20))
    address = Column(String(500))
    business_scope = Column(String(500))
    license_number = Column(String(100))
    license_expiry = Column(DateTime)
    total_vehicles = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)
    rating = Column(String(10))
    is_active = Column(Boolean, default=True)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vehicles = relationship("Vehicle", back_populates="company")
