from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(20), unique=True, index=True, nullable=False)
    plate_color = Column(String(10))
    vehicle_type = Column(String(50))
    vehicle_brand = Column(String(50))
    vehicle_model = Column(String(50))
    vehicle_color = Column(String(20))
    owner_name = Column(String(100))
    owner_phone = Column(String(20))
    company_id = Column(Integer, ForeignKey("companies.id"))
    company_name = Column(String(200))
    is_operational = Column(Boolean, default=True)
    operational_status = Column(String(20))
    registration_date = Column(DateTime)
    inspection_expiry = Column(DateTime)
    insurance_expiry = Column(DateTime)
    total_violations = Column(Integer, default=0)
    total_penalties = Column(Integer, default=0)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="vehicles")
    cases = relationship("Case", back_populates="vehicle")
    alerts = relationship("Alert", back_populates="vehicle")
