from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.statistics import OnboardingGuide, OnboardingStep
from app.core.exception_handler import NotFoundException


ONBOARDING_STEPS = [
    {
        "step_id": 1,
        "title": "欢迎使用路面执法系统",
        "description": "本系统将帮助您高效处理巡游车占道停车案件。让我们用5分钟完成新手引导。",
        "icon": "👋",
        "action_hint": "点击'下一步'继续",
        "estimated_time_minutes": 1
    },
    {
        "step_id": 2,
        "title": "认识案件卡片",
        "description": "每个案件卡片包含：车牌号、位置、违章时间、影响程度、证据图片等关键信息。",
        "icon": "📋",
        "action_hint": "查看下方示例卡片，了解各项信息含义",
        "estimated_time_minutes": 1
    },
    {
        "step_id": 3,
        "title": "学习操作手势",
        "description": "👉 左滑：排除案件（非违章或证据不足）\n👉 右滑：立案处理（确认违章）\n👉 长按：补充证据（拍照或上传）",
        "icon": "👆",
        "action_hint": "在模拟卡片上练习操作手势",
        "estimated_time_minutes": 2
    },
    {
        "step_id": 4,
        "title": "了解分级规则",
        "description": "系统根据路段、时段、学校/医院附近等因素自动分级。优先级从高到低：紧急>高>中>普通>低。",
        "icon": "🎯",
        "action_hint": "查看分级规则详情",
        "estimated_time_minutes": 1
    },
    {
        "step_id": 5,
        "title": "开始处理首单",
        "description": "恭喜！您已完成引导。现在开始处理您的第一个案件吧！系统会全程提供提示帮助。",
        "icon": "🚀",
        "action_hint": "点击'开始首单'进入待处理列表",
        "estimated_time_minutes": 0
    }
]

ENCOURAGEMENT_MESSAGES = [
    "太棒了！您已经完成了{progress}%的引导，继续加油！",
    "很好！您正在快速掌握系统操作，还差几步就完成了！",
    "做得好！您的学习进度达到了{progress}%，马上就能独立处理案件了！",
    "恭喜！您已完成新手引导，可以开始处理真实案件了！"
]


class OnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_guide(self, user: User) -> OnboardingGuide:
        current_step = user.onboarding_step or 0
        total_steps = len(ONBOARDING_STEPS)
        progress_percent = round(min(current_step / total_steps * 100, 100), 1)

        steps = []
        for step_config in ONBOARDING_STEPS:
            step_id = step_config["step_id"]
            steps.append(OnboardingStep(
                step_id=step_id,
                title=step_config["title"],
                description=step_config["description"],
                icon=step_config["icon"],
                is_completed=step_id <= current_step,
                is_current=step_id == current_step + 1,
                action_hint=step_config["action_hint"],
                estimated_time_minutes=step_config["estimated_time_minutes"]
            ))

        msg_index = min(int(progress_percent / 30), len(ENCOURAGEMENT_MESSAGES) - 1)
        encouragement = ENCOURAGEMENT_MESSAGES[msg_index].format(progress=progress_percent)

        first_case_available = current_step >= 4

        return OnboardingGuide(
            user_id=user.id,
            is_new_user=user.is_new_user,
            current_step=current_step,
            total_steps=total_steps,
            progress_percent=progress_percent,
            steps=steps,
            first_case_available=first_case_available,
            encouragement_message=encouragement
        )

    async def advance_step(self, user_id: int, to_step: int) -> OnboardingGuide:
        if to_step < 1 or to_step > len(ONBOARDING_STEPS):
            from app.core.exception_handler import BadRequestException
            raise BadRequestException(message=f"步骤必须在1-{len(ONBOARDING_STEPS)}之间")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="用户不存在")

        if to_step > user.onboarding_step + 1:
            from app.core.exception_handler import BadRequestException
            raise BadRequestException(message="不能跳过步骤")

        updated_user = await self.user_repo.update_onboarding_step(user_id, to_step)
        return self.get_guide(updated_user)

    def get_step_hints(self, step_id: int) -> dict:
        hints = {
            1: {
                "tips": [
                    "本系统支持路侧摄像头、车载视频、群众随手拍三种数据源",
                    "案件会自动分析占道影响程度并分级",
                    "您的任务是快速核验并做出处理决策"
                ],
                "faq": [
                    {"q": "需要执法资质吗？", "a": "是的，本系统仅限持证执法人员使用。"},
                    {"q": "处理的案件有效吗？", "a": "所有操作都会留痕，生成的证据包可作为执法依据。"}
                ]
            },
            2: {
                "tips": [
                    "红色卡片表示高优先级，请优先处理",
                    "卡片上的⚠️标志表示影响通行",
                    "🏫表示学校附近，🏥表示医院附近",
                    "数字显示历史违章次数和同点位复犯次数"
                ],
                "card_example": {
                    "plate_number": "京B·12345",
                    "location": "中关村大街与海淀黄庄路口",
                    "violation_time": "2024-01-15 08:30:00",
                    "badges": ["高峰时段", "学校附近", "影响通行"],
                    "stats": {"history": 5, "same_spot": 2}
                }
            },
            3: {
                "tips": [
                    "排除：证据不足、不属于管辖范围、已自行纠正",
                    "立案：确认违章，进入处罚流程",
                    "补证：现场补充拍照录像，完善证据链"
                ],
                "practice": [
                    {"scenario": "车牌模糊无法辨认", "correct": "dismiss"},
                    {"scenario": "禁停标志清晰，车辆占道影响通行", "correct": "file"},
                    {"scenario": "夜间光线不足，需要现场确认", "correct": "supplement"}
                ]
            },
            4: {
                "tips": [
                    "学校/医院周边：权重+30分",
                    "交通高峰期（7-9点，17-19点）：权重+20分",
                    "同点位30天内复犯：每次+3分（最高20分）",
                    "同一车辆历史违章：每次+5分（最高30分）"
                ],
                "priority_table": [
                    {"level": "紧急", "score": "≥120分", "color": "红色", "response": "立即处置"},
                    {"level": "高", "score": "90-119分", "color": "橙色", "response": "30分钟内"},
                    {"level": "中", "score": "50-89分", "color": "黄色", "response": "2小时内"},
                    {"level": "普通", "score": "20-49分", "color": "蓝色", "response": "当日处理"},
                    {"level": "低", "score": "<20分", "color": "绿色", "response": "3日内处理"}
                ]
            },
            5: {
                "tips": [
                    "首单处理过程中随时可以点击'帮助'按钮获取提示",
                    "如果不确定，可以先选择'补证'到现场确认",
                    "处理完成后系统会给出评分和改进建议",
                    "遇到复杂情况可以申请上级复核"
                ],
                "first_case_checklist": [
                    "核对车牌是否正确",
                    "确认位置与违章类型匹配",
                    "查看证据是否充分",
                    "根据影响程度选择处理方式",
                    "填写处理备注（可选）"
                ]
            }
        }

        return hints.get(step_id, {})

    def get_processing_helper(self, case_priority: str, case_severity: str) -> dict:
        priority_guide = {
            "critical": {
                "title": "🚨 紧急案件处理指引",
                "steps": [
                    "1. 立即呼叫现场支援",
                    "2. 联系车主立即驶离",
                    "3. 全程录音录像固定证据",
                    "4. 如拒不配合，依法拖车"
                ],
                "time_limit": "立即处理，最长不超过30分钟"
            },
            "high": {
                "title": "⚠️ 高优先级案件处理指引",
                "steps": [
                    "1. 优先核验证据完整性",
                    "2. 电话通知车主劝离",
                    "3. 如已驶离，发送违法告知",
                    "4. 生成处罚建议"
                ],
                "time_limit": "30分钟内处理完毕"
            },
            "medium": {
                "title": "📋 中优先级案件处理指引",
                "steps": [
                    "1. 核验车牌和位置信息",
                    "2. 确认违章事实",
                    "3. 发送劝离短信或处罚告知",
                    "4. 标记处理完成"
                ],
                "time_limit": "2小时内处理完毕"
            },
            "normal": {
                "title": "✅ 普通案件处理指引",
                "steps": [
                    "1. 快速核验证据",
                    "2. 确认无异议后立案",
                    "3. 系统自动发送告知",
                    "4. 归档处理"
                ],
                "time_limit": "当日处理完毕"
            },
            "low": {
                "title": "📝 低优先级案件处理指引",
                "steps": [
                    "1. 批量核验证据",
                    "2. 系统自动生成处罚建议",
                    "3. 人工复核后发出",
                    "4. 定期跟踪处理结果"
                ],
                "time_limit": "3日内处理完毕"
            }
        }

        helper = priority_guide.get(case_priority, priority_guide["normal"])

        severity_tips = {
            "critical": "注意：该案件严重影响交通，可能需要拖车处理。",
            "major": "注意：该案件影响较严重，建议依法从重处罚。",
            "minor": "提示：该案件有一定影响，按常规流程处理即可。",
            "trivial": "提示：该案件影响轻微，可先劝离教育为主。"
        }

        helper["severity_tip"] = severity_tips.get(case_severity, "")

        return helper
