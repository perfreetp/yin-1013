import os
import json
import hashlib
import zipfile
import tempfile
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.case import Case
from app.repositories.case_repository import CaseRepository
from app.core.logger import logger
from app.core.exception_handler import BusinessException, NotFoundException


class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.case_repo = CaseRepository(db)

    async def generate_evidence_package(self, case_id: int) -> Dict[str, Any]:
        case = await self.case_repo.get_by_id(case_id, ["evidence", "vehicle", "operations"])
        if not case:
            raise NotFoundException(message="案件不存在")

        storage_dir = os.path.join(settings.STORAGE_PATH, "evidence_packages")
        os.makedirs(storage_dir, exist_ok=True)

        package_filename = f"evidence_{case.case_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        package_path = os.path.join(storage_dir, package_filename)

        manifest_data = {
            "case_number": case.case_number,
            "generated_at": datetime.now().isoformat(),
            "case_info": {
                "source_type": case.source_type,
                "violation_type": case.violation_type,
                "violation_time": case.violation_time.isoformat() if case.violation_time else None,
                "plate_number": case.plate_number,
                "location_text": case.location_text,
                "severity_level": case.severity_level,
                "is_affecting_traffic": case.is_affecting_traffic,
                "traffic_impact_score": case.traffic_impact_score,
            },
            "vehicle_info": {},
            "evidence_list": [],
            "operation_history": [],
            "hash_algorithm": "sha256"
        }

        if case.vehicle:
            manifest_data["vehicle_info"] = {
                "plate_number": case.vehicle.plate_number,
                "vehicle_type": case.vehicle.vehicle_type,
                "owner_name": case.vehicle.owner_name,
                "company_name": case.vehicle.company_name,
                "total_violations": case.vehicle.total_violations,
            }

        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for idx, evidence in enumerate(case.evidence):
                evidence_entry = {
                    "id": evidence.id,
                    "type": evidence.type,
                    "file_name": evidence.file_name or f"evidence_{idx + 1}",
                    "file_type": evidence.file_type,
                    "capture_time": evidence.capture_time.isoformat() if evidence.capture_time else None,
                    "capture_device": evidence.capture_device,
                    "file_hash": None,
                    "archive_path": f"evidence/{evidence.id}_{evidence.file_name or f'evidence_{idx + 1}'}"
                }

                local_file_path = os.path.join(settings.STORAGE_PATH, evidence.file_path.lstrip('/')) if evidence.file_path else None

                if local_file_path and os.path.exists(local_file_path):
                    with open(local_file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    evidence_entry["file_hash"] = file_hash
                    zf.write(local_file_path, evidence_entry["archive_path"])
                elif evidence.file_url:
                    evidence_entry["file_url"] = evidence.file_url
                    evidence_entry["note"] = "文件未在本地存储，仅保留URL引用"

                manifest_data["evidence_list"].append(evidence_entry)

            for op in case.operations:
                manifest_data["operation_history"].append({
                    "operation_type": op.operation_type,
                    "operator_id": op.operator_id,
                    "from_status": op.from_status,
                    "to_status": op.to_status,
                    "remark": op.remark,
                    "created_at": op.created_at.isoformat()
                })

            manifest_json = json.dumps(manifest_data, ensure_ascii=False, indent=2)
            zf.writestr("manifest.json", manifest_json)

            hash_obj = hashlib.sha256()
            hash_obj.update(manifest_json.encode('utf-8'))
            package_hash = hash_obj.hexdigest()

            zf.writestr("hash.txt", f"Package SHA256: {package_hash}\nGenerated: {datetime.now().isoformat()}")

        case.evidence_package_url = f"/storage/evidence_packages/{package_filename}"
        case.evidence_package_hash = package_hash
        await self.db.flush()

        file_size = os.path.getsize(package_path)

        logger.info(f"Evidence package generated for case {case.case_number}: {package_filename}")

        return {
            "package_url": case.evidence_package_url,
            "package_hash": package_hash,
            "file_size": file_size,
            "evidence_count": len(case.evidence),
            "generated_at": datetime.now()
        }

    def get_appeal_review_data(self, case: Case) -> Dict[str, Any]:
        from geoalchemy2.shape import to_shape

        location = None
        if case.location:
            try:
                point = to_shape(case.location)
                location = {"lng": point.x, "lat": point.y}
            except Exception:
                pass

        return {
            "case_number": case.case_number,
            "appeal_status": case.appeal_status,
            "appeal_requested_at": case.appeal_requested_at,
            "appeal_remark": case.appeal_remark,
            "violation_info": {
                "type": case.violation_type,
                "code": case.violation_code,
                "time": case.violation_time.isoformat() if case.violation_time else None,
                "location": location,
                "location_text": case.location_text,
                "duration": case.violation_duration
            },
            "evidence": [
                {
                    "id": e.id,
                    "type": e.type,
                    "url": e.file_url,
                    "thumbnail": e.thumbnail_url,
                    "capture_time": e.capture_time.isoformat() if e.capture_time else None,
                    "is_verified": e.is_verified
                }
                for e in case.evidence
            ],
            "analysis_result": {
                "is_affecting_traffic": case.is_affecting_traffic,
                "traffic_impact_score": case.traffic_impact_score,
                "severity_level": case.severity_level,
                "near_school": case.near_school,
                "near_hospital": case.near_hospital,
                "in_peak_hour": case.in_peak_hour,
                "congestion_index": case.congestion_index
            },
            "penalty_suggestion": case.penalty_suggestion,
            "timeline": self._build_timeline(case)
        }

    def _build_timeline(self, case: Case) -> list:
        timeline = []

        if case.created_at:
            timeline.append({
                "time": case.created_at.isoformat(),
                "event": "案件创建",
                "type": "create"
            })

        if case.reviewed_at:
            timeline.append({
                "time": case.reviewed_at.isoformat(),
                "event": f"案件审核: {case.review_result}",
                "type": "review"
            })

        if case.handled_at:
            timeline.append({
                "time": case.handled_at.isoformat(),
                "event": f"案件处理: {case.handling_result}",
                "type": "handle"
            })

        if case.appeal_requested_at:
            timeline.append({
                "time": case.appeal_requested_at.isoformat(),
                "event": "提起申诉",
                "type": "appeal"
            })

        if case.appeal_reviewed_at:
            timeline.append({
                "time": case.appeal_reviewed_at.isoformat(),
                "event": f"申诉审核: {case.appeal_result}",
                "type": "appeal_review"
            })

        if case.closed_at:
            timeline.append({
                "time": case.closed_at.isoformat(),
                "event": "案件结案",
                "type": "close"
            })

        return sorted(timeline, key=lambda x: x["time"])

    async def request_appeal(self, case_id: int, appeal_remark: str) -> Case:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise NotFoundException(message="案件不存在")

        if case.appeal_status != "none":
            raise BusinessException(message="该案件已有申诉记录")

        case.appeal_status = "pending"
        case.appeal_requested_at = datetime.utcnow()
        case.appeal_remark = appeal_remark

        await self.db.flush()
        await self.db.refresh(case)

        logger.info(f"Appeal requested for case {case.case_number}")
        return case

    async def review_appeal(self, case_id: int, approved: bool, review_remark: str) -> Case:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise NotFoundException(message="案件不存在")

        if case.appeal_status != "pending":
            raise BusinessException(message="该案件没有待审核的申诉")

        case.appeal_status = "approved" if approved else "rejected"
        case.appeal_reviewed_at = datetime.utcnow()
        case.appeal_result = "申诉通过" if approved else "申诉驳回"
        case.appeal_remark = f"{case.appeal_remark or ''} | 审核意见: {review_remark}"

        if approved:
            case.status = "appeal_sustained"
        else:
            case.status = "appeal_rejected"

        case.closed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(case)

        logger.info(f"Appeal reviewed for case {case.case_number}: {case.appeal_status}")
        return case
