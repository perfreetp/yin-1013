from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.case import Case
from app.core.logger import logger


class ViolationAnalysisEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_traffic_impact(
        self,
        location_lng: float,
        location_lat: float,
        violation_time: datetime,
        road_segment=None,
        violation_duration: int = 0
    ) -> Tuple[bool, float, Dict[str, Any]]:
        impact_score = 0.0
        factors = {}

        near_school = False
        near_hospital = False
        near_bus_stop = False
        in_peak_hour = False

        if road_segment:
            near_school = road_segment.is_school_zone
            near_hospital = road_segment.is_hospital_zone
            near_bus_stop = road_segment.is_bus_stop
            impact_score += road_segment.average_congestion_index * 10

        in_peak_hour = self._is_peak_hour(violation_time)

        if near_school:
            impact_score += 30
            factors["school_zone"] = True
        if near_hospital:
            impact_score += 25
            factors["hospital_zone"] = True
        if near_bus_stop:
            impact_score += 15
            factors["bus_stop"] = True
        if in_peak_hour:
            impact_score += 20
            factors["peak_hour"] = True

        if violation_duration > 300:
            impact_score += min(violation_duration / 60, 20)
            factors["long_duration"] = True

        impact_score = min(impact_score, 100)
        is_affecting = impact_score >= 30

        logger.info(
            f"Traffic impact analysis: score={impact_score:.1f}, "
            f"affecting={is_affecting}, factors={factors}"
        )

        return is_affecting, impact_score, {
            "near_school": near_school,
            "near_hospital": near_hospital,
            "near_bus_stop": near_bus_stop,
            "in_peak_hour": in_peak_hour,
            **factors
        }

    def _is_peak_hour(self, time: datetime) -> bool:
        hour = time.hour
        minute = time.minute
        current_time = f"{hour:02d}:{minute:02d}"

        morning_start = settings.PEAK_HOUR_MORNING_START
        morning_end = settings.PEAK_HOUR_MORNING_END
        evening_start = settings.PEAK_HOUR_EVENING_START
        evening_end = settings.PEAK_HOUR_EVENING_END

        is_morning_peak = morning_start <= current_time <= morning_end
        is_evening_peak = evening_start <= current_time <= evening_end

        return is_morning_peak or is_evening_peak

    def determine_severity_level(self, impact_score: float, is_affecting: bool) -> str:
        if impact_score >= 70:
            return "critical"
        elif impact_score >= 50:
            return "major"
        elif impact_score >= 30 or is_affecting:
            return "minor"
        else:
            return "trivial"

    def determine_priority(
        self,
        severity_level: str,
        near_school: bool,
        near_hospital: bool,
        in_peak_hour: bool,
        repeat_count: int,
        same_location_count: int
    ) -> str:
        priority_score = 0

        severity_weights = {
            "critical": 100,
            "major": 70,
            "minor": 40,
            "trivial": 10
        }
        priority_score += severity_weights.get(severity_level, 0)

        if near_school:
            priority_score += 30
        if near_hospital:
            priority_score += 25
        if in_peak_hour:
            priority_score += 20

        priority_score += min(repeat_count * 5, 30)
        priority_score += min(same_location_count * 3, 20)

        if priority_score >= 120:
            return "critical"
        elif priority_score >= 90:
            return "high"
        elif priority_score >= 50:
            return "medium"
        elif priority_score >= 20:
            return "normal"
        else:
            return "low"

    def determine_violation_type(self, is_no_parking: bool, is_affecting: bool, lane_count: int) -> Tuple[str, str]:
        if is_no_parking:
            if is_affecting:
                return "violation_code_001", "在禁停路段占道停车，影响通行"
            else:
                return "violation_code_001", "在禁停路段临时停车"
        elif lane_count <= 2 and is_affecting:
            return "violation_code_002", "在窄路占道停车，严重影响通行"
        else:
            return "violation_code_003", "占道停车影响通行"

    def generate_penalty_suggestion(
        self,
        violation_code: str,
        severity_level: str,
        is_affecting: bool,
        repeat_count: int
    ) -> Dict[str, Any]:
        base_fine_map = {
            "violation_code_001": {"fine": 200, "points": 3},
            "violation_code_002": {"fine": 200, "points": 3},
            "violation_code_003": {"fine": 100, "points": 0},
        }

        base = base_fine_map.get(violation_code, {"fine": 100, "points": 0})

        multiplier = 1.0
        if severity_level == "critical":
            multiplier = 2.0
        elif severity_level == "major":
            multiplier = 1.5
        elif is_affecting:
            multiplier = 1.2

        if repeat_count >= 3:
            multiplier *= 1.5

        fine_amount = int(base["fine"] * multiplier)
        points = base["points"]

        return {
            "violation_code": violation_code,
            "violation_name": "机动车违反规定停放、临时停车",
            "penalty_type": "both" if points > 0 else "fine",
            "fine_amount": fine_amount,
            "points": points,
            "description": self._generate_description(
                violation_code, severity_level, is_affecting, repeat_count
            ),
            "legal_basis": "《中华人民共和国道路交通安全法》第五十六条、第九十三条",
            "is_repeat_offense": repeat_count >= 3
        }

    def _generate_description(
        self,
        violation_code: str,
        severity_level: str,
        is_affecting: bool,
        repeat_count: int
    ) -> str:
        parts = []

        type_map = {
            "violation_code_001": "在设有禁停标志、标线的路段停车",
            "violation_code_002": "在宽度不足4米的窄路停车",
            "violation_code_003": "在道路上临时停车妨碍其他车辆",
        }

        parts.append(type_map.get(violation_code, "占道停车"))

        if is_affecting:
            parts.append("，影响其他车辆和行人通行")

        if severity_level == "critical":
            parts.append("，情节严重")

        if repeat_count >= 3:
            parts.append(f"，系{repeat_count}次重复违章")

        return "".join(parts)

    def generate_dissuasion_template(
        self,
        severity_level: str,
        near_school: bool,
        near_hospital: bool,
        in_peak_hour: bool,
        plate_number: str,
        location_text: str
    ) -> str:
        templates = {
            "trivial": (
                f"您好，这里是交通执法人员。您的车辆{plate_number}在{location_text}"
                f"临时停车，请尽快驶离，感谢配合！"
            ),
            "minor": (
                f"您好，这里是交通执法人员。您的车辆{plate_number}在{location_text}"
                f"停车已影响通行，请立即驶离，否则将依法处罚！"
            ),
            "major": (
                f"您好，这里是交通执法人员。您的车辆{plate_number}"
                f"在{location_text}"
                f"违章停车已严重影响交通秩序，请立即驶离！"
            ),
            "critical": (
                f"警告！您的车辆{plate_number}在{location_text}"
                f"严重违章停车，已造成交通拥堵，请立即驶离！"
            ),
        }

        template = templates.get(severity_level, templates["minor"])

        extra = []
        if near_school:
            extra.append("此处为学校区域")
        if near_hospital:
            extra.append("此处为医院区域")
        if in_peak_hour:
            extra.append("当前为交通高峰期")

        if extra:
            template += "（" + "、".join(extra) + "），请特别注意！"

        return template

    async def enrich_case_data(self, case: Case, road_segment=None) -> Case:
        if not case.location:
            return case

        from geoalchemy2.shape import to_shape
        point = to_shape(case.location)

        is_affecting, impact_score, factors = await self.analyze_traffic_impact(
            location_lng=point.x,
            location_lat=point.y,
            violation_time=case.violation_time,
            road_segment=road_segment,
            violation_duration=case.violation_duration or 0
        )

        case.is_affecting_traffic = is_affecting
        case.traffic_impact_score = impact_score
        case.near_school = factors["near_school"]
        case.near_hospital = factors["near_hospital"]
        case.near_bus_stop = factors["near_bus_stop"]
        case.in_peak_hour = factors["in_peak_hour"]

        severity = self.determine_severity_level(impact_score, is_affecting)
        case.severity_level = severity

        return case
