import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, Base
from app.core.logger import logger
from app.core.security import hash_password


async def create_tables():
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created successfully")


async def create_initial_user():
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import async_session
    from app.repositories.user_repository import UserRepository

    async with async_session() as session:
        user_repo = UserRepository(session)

        admin = await user_repo.get_by_username("admin")
        if not admin:
            await user_repo.create(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                phone="13800138000",
                badge_number="ADMIN001",
                role="admin",
                department="交通执法总队",
                is_active=True,
                is_new_user=False,
                onboarding_step=5,
                cases_handled=0
            )
            logger.info("Created default admin user: admin/admin123")

        inspector = await user_repo.get_by_username("inspector01")
        if not inspector:
            await user_repo.create(
                username="inspector01",
                password_hash=hash_password("inspector123"),
                real_name="张稽查",
                phone="13800138001",
                badge_number="INS001",
                role="inspector",
                department="第一执法大队",
                is_active=True,
                is_new_user=True,
                onboarding_step=0,
                cases_handled=0
            )
            logger.info("Created default inspector user: inspector01/inspector123")

        reviewer = await user_repo.get_by_username("reviewer01")
        if not reviewer:
            await user_repo.create(
                username="reviewer01",
                password_hash=hash_password("reviewer123"),
                real_name="李复核",
                phone="13800138002",
                badge_number="REV001",
                role="reviewer",
                department="案件复核科",
                is_active=True,
                is_new_user=False,
                onboarding_step=5,
                cases_handled=0
            )
            logger.info("Created default reviewer user: reviewer01/reviewer123")

        await session.commit()


async def init_sample_road_segments():
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import async_session
    from app.models.road_segment import RoadSegment
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point, LineString

    async with async_session() as session:
        result = await session.execute(
            RoadSegment.__table__.select().limit(1)
        )
        if result.scalar_one_or_none():
            logger.info("Road segments already exist, skipping initialization")
            return

        sample_segments = [
            {
                "name": "中关村大街",
                "code": "RD001",
                "road_type": "主干道",
                "direction": "南北",
                "lane_count": 6,
                "speed_limit": 60,
                "length_meters": 2500,
                "start_point": from_shape(Point(116.3150, 39.9850), srid=4326),
                "end_point": from_shape(Point(116.3200, 39.9650), srid=4326),
                "center_point": from_shape(Point(116.3175, 39.9750), srid=4326),
                "geometry": from_shape(LineString([(116.3150, 39.9850), (116.3200, 39.9650)]), srid=4326),
                "district": "海淀区",
                "area": "中关村",
                "is_no_parking": True,
                "is_school_zone": True,
                "is_hospital_zone": False,
                "is_bus_stop": True,
                "is_intersection": True,
                "priority_level": "high",
                "average_congestion_index": 6.5
            },
            {
                "name": "海淀黄庄东街",
                "code": "RD002",
                "road_type": "次干道",
                "direction": "东西",
                "lane_count": 4,
                "speed_limit": 40,
                "length_meters": 800,
                "start_point": from_shape(Point(116.3200, 39.9750), srid=4326),
                "end_point": from_shape(Point(116.3300, 39.9750), srid=4326),
                "center_point": from_shape(Point(116.3250, 39.9750), srid=4326),
                "geometry": from_shape(LineString([(116.3200, 39.9750), (116.3300, 39.9750)]), srid=4326),
                "district": "海淀区",
                "area": "海淀黄庄",
                "is_no_parking": False,
                "is_school_zone": False,
                "is_hospital_zone": True,
                "is_bus_stop": True,
                "is_intersection": True,
                "priority_level": "medium",
                "average_congestion_index": 4.2
            },
            {
                "name": "王府井大街",
                "code": "RD003",
                "road_type": "商业街",
                "direction": "南北",
                "lane_count": 4,
                "speed_limit": 30,
                "length_meters": 1500,
                "start_point": from_shape(Point(116.4100, 39.9200), srid=4326),
                "end_point": from_shape(Point(116.4120, 39.9100), srid=4326),
                "center_point": from_shape(Point(116.4110, 39.9150), srid=4326),
                "geometry": from_shape(LineString([(116.4100, 39.9200), (116.4120, 39.9100)]), srid=4326),
                "district": "东城区",
                "area": "王府井",
                "is_no_parking": True,
                "is_school_zone": False,
                "is_hospital_zone": False,
                "is_bus_stop": True,
                "is_intersection": True,
                "priority_level": "critical",
                "average_congestion_index": 8.0
            }
        ]

        for seg in sample_segments:
            session.add(RoadSegment(**seg))

        await session.commit()
        logger.info(f"Created {len(sample_segments)} sample road segments")


async def main():
    logger.info("Starting database initialization...")

    try:
        await create_tables()
        await create_initial_user()
        await init_sample_road_segments()
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
