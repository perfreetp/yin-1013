from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.db.session import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), index=True, nullable=False)
    code = Column(String(50), unique=True, index=True)
    road_type = Column(String(50))
    direction = Column(String(20))
    lane_count = Column(Integer)
    speed_limit = Column(Integer)
    length_meters = Column(Float)
    start_point = Column(Geometry(geometry_type='POINT', srid=4326))
    end_point = Column(Geometry(geometry_type='POINT', srid=4326))
    center_point = Column(Geometry(geometry_type='POINT', srid=4326))
    geometry = Column(Geometry(geometry_type='LINESTRING', srid=4326))
    district = Column(String(100))
    area = Column(String(100))
    is_no_parking = Column(Boolean, default=False)
    is_school_zone = Column(Boolean, default=False)
    is_hospital_zone = Column(Boolean, default=False)
    is_bus_stop = Column(Boolean, default=False)
    is_intersection = Column(Boolean, default=False)
    peak_hour_config = Column(JSON)
    congestion_level = Column(String(20))
    average_congestion_index = Column(Float, default=0)
    total_violations = Column(Integer, default=0)
    hot_spot_score = Column(Float, default=0)
    priority_level = Column(String(20), default="normal")
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cases = relationship("Case", back_populates="road_segment")
    cameras = relationship("Camera", back_populates="road_segment")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200))
    type = Column(String(50))
    manufacturer = Column(String(100))
    model = Column(String(100))
    location = Column(Geometry(geometry_type='POINT', srid=4326))
    address = Column(String(500))
    road_segment_id = Column(Integer, ForeignKey("road_segments.id"))
    direction = Column(String(20))
    coverage_radius = Column(Float, default=50)
    is_active = Column(Boolean, default=True)
    rtsp_url = Column(String(500))
    snapshot_url = Column(String(500))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    road_segment = relationship("RoadSegment", back_populates="cameras")
    evidence = relationship("Evidence", back_populates="camera")
