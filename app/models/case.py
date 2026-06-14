from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.db.session import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    source_type = Column(String(30), nullable=False)
    source_id = Column(String(100))

    status = Column(String(30), default="pending_review", nullable=False)
    priority = Column(String(20), default="normal")
    severity_level = Column(String(20), default="minor")

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    plate_number = Column(String(20), index=True)
    plate_confidence = Column(Float)

    location = Column(Geometry(geometry_type='POINT', srid=4326))
    location_text = Column(String(500))
    road_segment_id = Column(Integer, ForeignKey("road_segments.id"))
    road_name = Column(String(200))
    district = Column(String(100))
    area = Column(String(100))

    violation_type = Column(String(100))
    violation_code = Column(String(50))
    violation_time = Column(DateTime, nullable=False)
    violation_duration = Column(Integer)

    is_affecting_traffic = Column(Boolean)
    traffic_impact_score = Column(Float, default=0)
    congestion_index = Column(Float, default=0)
    near_school = Column(Boolean, default=False)
    near_hospital = Column(Boolean, default=False)
    near_bus_stop = Column(Boolean, default=False)
    in_peak_hour = Column(Boolean, default=False)

    repeat_offense_count = Column(Integer, default=0)
    same_location_count = Column(Integer, default=0)

    penalty_suggestion = Column(JSON)
    dissuasion_template = Column(String(500))

    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    handled_by = Column(Integer, ForeignKey("users.id"))

    assigned_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    handled_at = Column(DateTime)
    closed_at = Column(DateTime)

    review_result = Column(String(30))
    review_remark = Column(Text)
    handling_result = Column(String(30))
    handling_remark = Column(Text)

    appeal_status = Column(String(20), default="none")
    appeal_requested_at = Column(DateTime)
    appeal_reviewed_at = Column(DateTime)
    appeal_result = Column(String(30))
    appeal_remark = Column(Text)

    evidence_package_url = Column(String(500))
    evidence_package_hash = Column(String(100))

    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vehicle = relationship("Vehicle", back_populates="cases")
    road_segment = relationship("RoadSegment", back_populates="cases")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_cases")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_cases")
    handler = relationship("User", foreign_keys=[handled_by], back_populates="handled_cases")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    operations = relationship("CaseOperation", back_populates="case", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="case")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    type = Column(String(30), nullable=False)
    file_type = Column(String(50))
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_url = Column(String(500))
    file_size = Column(Integer)
    file_hash = Column(String(100))
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Integer)
    thumbnail_url = Column(String(500))
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    capture_time = Column(DateTime)
    capture_device = Column(String(100))
    uploader_id = Column(Integer)
    ocr_result = Column(JSON)
    analysis_result = Column(JSON)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    verified_by = Column(Integer)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="evidence")
    camera = relationship("Camera", back_populates="evidence")


class CaseOperation(Base):
    __tablename__ = "case_operations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation_type = Column(String(50), nullable=False)
    from_status = Column(String(30))
    to_status = Column(String(30))
    remark = Column(Text)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="operations")
    operator = relationship("User", back_populates="operations")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)
    alert_level = Column(String(20), default="normal")
    case_id = Column(Integer, ForeignKey("cases.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    plate_number = Column(String(20), index=True)
    location = Column(Geometry(geometry_type='POINT', srid=4326))
    location_text = Column(String(500))
    alert_time = Column(DateTime, nullable=False)
    description = Column(Text)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    is_handled = Column(Boolean, default=False)
    handled_at = Column(DateTime)
    handled_by = Column(Integer)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="alerts")
    vehicle = relationship("Vehicle", back_populates="alerts")
