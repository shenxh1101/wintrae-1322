import uuid
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from .models import (
    ExamPaper,
    ExamResult,
    StudentAnswer,
    PracticeSession,
    WrongQuestion,
    QuestionType,
    ReviewInfo,
    Difficulty,
)
from .question_bank import QuestionBank
from .exam_builder import AdaptiveBuilder, AdaptiveRationale
from .grader import Grader
from .session import SessionManager
from .analytics import Analytics, KnowledgePointStats


BATCH_STATUS_GENERATED = "generated"
BATCH_STATUS_DISTRIBUTED = "distributed"
BATCH_STATUS_IMPORTING = "importing"
BATCH_STATUS_GRADED = "graded"
BATCH_STATUS_NEEDS_REVIEW = "needs_review"
BATCH_STATUS_REPORTED = "reported"
BATCH_STATUS_ARCHIVED = "archived"

BATCH_STATUS_FLOW = (
    BATCH_STATUS_GENERATED,
    BATCH_STATUS_DISTRIBUTED,
    BATCH_STATUS_IMPORTING,
    BATCH_STATUS_GRADED,
    BATCH_STATUS_NEEDS_REVIEW,
    BATCH_STATUS_REPORTED,
    BATCH_STATUS_ARCHIVED,
)

BATCH_STATUS_LABEL = {
    BATCH_STATUS_GENERATED: "已生成",
    BATCH_STATUS_DISTRIBUTED: "已发放",
    BATCH_STATUS_IMPORTING: "答案导入中",
    BATCH_STATUS_GRADED: "已批改",
    BATCH_STATUS_NEEDS_REVIEW: "待复核",
    BATCH_STATUS_REPORTED: "已出报告",
    BATCH_STATUS_ARCHIVED: "已归档",
}


@dataclass
class StudentProfile:
    student_id: str
    student_name: str = ""
    grade: Optional[str] = None
    class_id: Optional[str] = None
    wrong_book: Dict[str, WrongQuestion] = field(default_factory=dict)
    weak_knowledge_points: List[KnowledgePointStats] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchMeta:
    batch_id: str
    class_id: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    title_template: str = ""
    total_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    creator_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "class_id": self.class_id,
            "subject": self.subject,
            "grade": self.grade,
            "title_template": self.title_template,
            "total_count": self.total_count,
            "created_at": self.created_at.isoformat(),
            "creator_id": self.creator_id,
            "metadata": self.metadata,
        }


@dataclass
class BatchExamItem:
    student_id: str
    exam_paper: ExamPaper
    rationale: Optional[AdaptiveRationale] = None
    session_id: Optional[str] = None
    source_type: str = "adaptive"
    question_count: int = 0
    estimated_minutes: int = 0
    weak_basis: List[str] = field(default_factory=list)
    status: str = "generated"
    import_status: str = "pending"
    import_errors: List[str] = field(default_factory=list)
    import_notes: str = ""
    regenerated_from: Optional[str] = None
    regenerated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "session_id": self.session_id,
            "exam_id": self.exam_paper.id if self.exam_paper else None,
            "exam_title": self.exam_paper.title if self.exam_paper else "",
            "source_type": self.source_type,
            "question_count": self.question_count,
            "estimated_minutes": self.estimated_minutes,
            "weak_basis": self.weak_basis,
            "status": self.status,
            "import_status": self.import_status,
            "import_errors": self.import_errors,
            "import_notes": self.import_notes,
            "regenerated_from": self.regenerated_from,
            "regenerated_at": self.regenerated_at.isoformat() if self.regenerated_at else None,
            "overall_mastery": self.rationale.overall_mastery if self.rationale else None,
        }


@dataclass
class SkippedStudent:
    student_id: str
    reason: str
    student_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "reason": self.reason,
        }


@dataclass
class StudentImportResult:
    student_id: str
    status: str
    imported_count: int = 0
    total_count: int = 0
    errors: List[str] = field(default_factory=list)
    was_processed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "status": self.status,
            "imported_count": self.imported_count,
            "total_count": self.total_count,
            "errors": self.errors,
            "was_processed": self.was_processed,
        }


@dataclass
class BatchImportResult:
    batch_id: str
    per_student: List[StudentImportResult] = field(default_factory=list)
    success_count: int = 0
    partial_count: int = 0
    skipped_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "per_student": [r.to_dict() for r in self.per_student],
            "success_count": self.success_count,
            "partial_count": self.partial_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
        }


@dataclass
class ImportReceipt:
    batch_id: str
    processed_at: datetime = field(default_factory=datetime.now)
    total_submitted: int = 0
    success_count: int = 0
    partial_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    per_student: List[Dict[str, Any]] = field(default_factory=list)
    report_link: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "processed_at": self.processed_at.isoformat(),
            "total_submitted": self.total_submitted,
            "success_count": self.success_count,
            "partial_count": self.partial_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "per_student": self.per_student,
            "report_link": self.report_link,
        }


@dataclass
class BatchSummary:
    batch_id: str
    status: str
    status_label: str = ""
    class_id: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    student_total: int = 0
    student_generated: int = 0
    student_not_submitted: int = 0
    student_submitted: int = 0
    student_graded: int = 0
    student_needs_review: int = 0
    student_reviewed: int = 0
    student_failed: int = 0
    created_at: Optional[datetime] = None
    reported_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    report_link: str = ""
    per_student: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "status_label": self.status_label,
            "class_id": self.class_id,
            "subject": self.subject,
            "grade": self.grade,
            "student_total": self.student_total,
            "student_generated": self.student_generated,
            "student_not_submitted": self.student_not_submitted,
            "student_submitted": self.student_submitted,
            "student_graded": self.student_graded,
            "student_needs_review": self.student_needs_review,
            "student_reviewed": self.student_reviewed,
            "student_failed": self.student_failed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "report_link": self.report_link,
            "per_student": self.per_student,
        }


@dataclass
class StudentReportSummary:
    student_id: str
    student_name: str = ""
    total_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0
    correct_count: int = 0
    wrong_count: int = 0
    pending_review_count: int = 0
    rank: Optional[int] = None
    grade_level: str = ""
    strong_points: List[str] = field(default_factory=list)
    weak_points: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    review_adjustment: float = 0.0
    tier: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "pending_review_count": self.pending_review_count,
            "rank": self.rank,
            "grade_level": self.grade_level,
            "strong_points": self.strong_points,
            "weak_points": self.weak_points,
            "suggestions": self.suggestions,
            "review_adjustment": self.review_adjustment,
            "tier": self.tier,
        }


@dataclass
class WeakKPMatrixRow:
    knowledge_point: str
    student_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    avg_mastery: float = 0.0
    typical_question_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_point": self.knowledge_point,
            "student_count": self.student_count,
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 2),
            "avg_mastery": round(self.avg_mastery, 2),
            "typical_question_ids": self.typical_question_ids,
        }


@dataclass
class TieredStudents:
    basic_tier: List[StudentReportSummary] = field(default_factory=list)
    advanced_tier: List[StudentReportSummary] = field(default_factory=list)
    review_tier: List[StudentReportSummary] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "basic_tier": [s.to_dict() for s in self.basic_tier],
            "advanced_tier": [s.to_dict() for s in self.advanced_tier],
            "review_tier": [s.to_dict() for s in self.review_tier],
            "basic_count": len(self.basic_tier),
            "advanced_count": len(self.advanced_tier),
            "review_count": len(self.review_tier),
        }


@dataclass
class CommentKPSection:
    knowledge_point: str
    error_rate: float = 0.0
    error_student_count: int = 0
    avg_mastery: float = 0.0
    typical_wrong_questions: List[Dict[str, Any]] = field(default_factory=list)
    affected_students: List[Dict[str, Any]] = field(default_factory=list)
    suggested_order: int = 0
    teaching_tips: List[str] = field(default_factory=list)
    recommended_extra_questions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_point": self.knowledge_point,
            "error_rate": round(self.error_rate, 2),
            "error_student_count": self.error_student_count,
            "avg_mastery": round(self.avg_mastery, 2),
            "typical_wrong_questions": self.typical_wrong_questions,
            "affected_students": self.affected_students,
            "suggested_order": self.suggested_order,
            "teaching_tips": self.teaching_tips,
            "recommended_extra_questions": self.recommended_extra_questions,
        }


@dataclass
class ClassCommentPackage:
    batch_id: str
    class_id: Optional[str]
    subject: Optional[str] = None
    exam_title: str = ""
    class_overview: Dict[str, Any] = field(default_factory=dict)
    kp_sections: List[CommentKPSection] = field(default_factory=list)
    all_affected_students: List[Dict[str, Any]] = field(default_factory=list)
    recommended_review_order: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "class_id": self.class_id,
            "subject": self.subject,
            "exam_title": self.exam_title,
            "class_overview": self.class_overview,
            "kp_sections": [s.to_dict() for s in self.kp_sections],
            "all_affected_students": self.all_affected_students,
            "recommended_review_order": self.recommended_review_order,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ClassReportSummary:
    class_id: Optional[str]
    subject: Optional[str]
    exam_title: str
    batch_id: str = ""
    student_count: int = 0
    average_score: float = 0.0
    max_score: float = 0.0
    min_score: float = 0.0
    pass_rate: float = 0.0
    excellent_rate: float = 0.0
    grade_distribution: Dict[str, int] = field(default_factory=dict)
    class_strong_points: List[str] = field(default_factory=list)
    class_weak_points: List[str] = field(default_factory=list)
    student_reports: List[StudentReportSummary] = field(default_factory=list)
    weak_kp_matrix: List[WeakKPMatrixRow] = field(default_factory=list)
    tiered_students: TieredStudents = field(default_factory=TieredStudents)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "class_id": self.class_id,
            "subject": self.subject,
            "exam_title": self.exam_title,
            "student_count": self.student_count,
            "average_score": round(self.average_score, 2),
            "max_score": round(self.max_score, 2),
            "min_score": round(self.min_score, 2),
            "pass_rate": round(self.pass_rate, 2),
            "excellent_rate": round(self.excellent_rate, 2),
            "grade_distribution": self.grade_distribution,
            "class_strong_points": self.class_strong_points,
            "class_weak_points": self.class_weak_points,
            "student_reports": [s.to_dict() for s in self.student_reports],
            "weak_kp_matrix": [r.to_dict() for r in self.weak_kp_matrix],
            "tiered_students": self.tiered_students.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }


_AVG_MINUTES_BY_TYPE = {
    QuestionType.SINGLE_CHOICE: 1.5,
    QuestionType.MULTIPLE_CHOICE: 2.0,
    QuestionType.FILL_BLANK: 2.5,
    QuestionType.TRUE_FALSE: 1.0,
    QuestionType.SHORT_ANSWER: 6.0,
}

_AVG_MINUTES_BY_DIFFICULTY = {
    Difficulty.EASY: 0.8,
    Difficulty.MEDIUM: 1.0,
    Difficulty.HARD: 1.4,
}


def _estimate_minutes(exam: ExamPaper) -> int:
    total = 0.0
    for q in exam.questions:
        base = _AVG_MINUTES_BY_TYPE.get(q.question_type, 2.0)
        diff = _AVG_MINUTES_BY_DIFFICULTY.get(q.difficulty, 1.0)
        total += base * diff
    return max(1, int(round(total)))


def _build_weak_basis(
    profile: StudentProfile,
    rationale: Optional[AdaptiveRationale],
) -> List[str]:
    basis = []
    if profile.wrong_book:
        basis.append(f"错题本有{len(profile.wrong_book)}道待巩固题目")
    for wq in list(profile.wrong_book.values())[:2]:
        if wq.knowledge_points:
            basis.append(f"曾错过知识点：{'、'.join(wq.knowledge_points[:2])}")
    if profile.weak_knowledge_points:
        weak_names = [w.knowledge_point for w in profile.weak_knowledge_points[:3]]
        if weak_names:
            basis.append(f"薄弱知识点：{'、'.join(weak_names)}")
    if rationale and rationale.overall_mastery < 70:
        basis.append(f"整体掌握度{rationale.overall_mastery:.0f}%，以基础巩固为主")
    elif rationale and rationale.overall_mastery >= 90:
        basis.append(f"整体掌握度{rationale.overall_mastery:.0f}%，增加综合提升题")
    if not basis:
        basis.append("综合练习，全面覆盖知识点")
    return basis


def _kp_teaching_tip(kp: str, error_rate: float) -> List[str]:
    tips: List[str] = []
    if error_rate >= 60:
        tips.append(f"{kp}全班错误率超过60%，建议从核心概念开始重新讲解，并搭配课堂互动小练习。")
    elif error_rate >= 30:
        tips.append(f"{kp}错误率在{error_rate:.0f}%左右，建议精选典型错题进行课堂纠错，再做2-3道同类型变式练习。")
    else:
        tips.append(f"{kp}仅有少量错误，可安排学生互助讲解或作为课后思考题。")
    tips.append(f"讲解时建议强调{kp}的常见易错点，并给出标准解题步骤。")
    return tips


class ClassroomManager:
    def __init__(
        self,
        question_bank: QuestionBank,
        grader: Optional[Grader] = None,
        analytics: Optional[Analytics] = None,
        session_manager: Optional[SessionManager] = None,
    ):
        self._bank = question_bank
        self._grader = grader or Grader()
        self._analytics = analytics or Analytics(question_bank)
        self._sessions = session_manager or SessionManager()
        self._adaptive = AdaptiveBuilder(question_bank)
        self._students: Dict[str, StudentProfile] = {}
        self._class_exams: Dict[str, Dict[str, Any]] = {}
        self._report_links: Dict[str, str] = {}
        self._reported_at: Dict[str, datetime] = {}
        self._archived_at: Dict[str, datetime] = {}

    # ---------- 学生管理 ----------

    def add_student(self, profile: StudentProfile) -> None:
        self._students[profile.student_id] = profile

    def add_students(self, profiles: List[StudentProfile]) -> None:
        for p in profiles:
            self.add_student(p)

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        return self._students.get(student_id)

    def list_students(
        self,
        class_id: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> List[StudentProfile]:
        result = []
        for p in self._students.values():
            if class_id and p.class_id != class_id:
                continue
            if grade and p.grade != grade:
                continue
            result.append(p)
        return result

    # ---------- 批次生命周期工具 ----------

    def _get_batch(self, batch_id: str) -> Dict[str, Any]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")
        return self._class_exams[batch_id]

    def _set_batch_status(self, batch_id: str, status: str) -> None:
        batch = self._get_batch(batch_id)
        batch["meta"].metadata["status"] = status
        batch["status"] = status

    def _auto_update_batch_status(self, batch_id: str) -> str:
        batch = self._get_batch(batch_id)
        current = batch.get("status", BATCH_STATUS_GENERATED)

        if current == BATCH_STATUS_ARCHIVED:
            return current

        items: List[BatchExamItem] = batch["items"]
        total = len(items)
        if total == 0:
            return current

        imported = sum(1 for it in items if it.import_status in ("success", "partial"))
        graded = 0
        needs_review = 0
        reviewed = 0
        for it in items:
            if it.session_id:
                sess = self._sessions.get_session(it.session_id)
                if sess:
                    if sess.status in ("graded", "reviewed", "closed"):
                        graded += 1
                        if sess.status in ("reviewed", "closed"):
                            reviewed += 1
                        if sess.exam_result and any(
                            qr.question_type == QuestionType.SHORT_ANSWER
                            and (qr.review_info is None or qr.review_info.review_status == "auto")
                            for qr in sess.exam_result.question_results
                        ):
                            needs_review += 1

        if imported == 0 and graded == 0:
            if current == BATCH_STATUS_DISTRIBUTED:
                new_status = BATCH_STATUS_DISTRIBUTED
            else:
                new_status = BATCH_STATUS_GENERATED
        elif imported > 0 and imported < total:
            new_status = BATCH_STATUS_IMPORTING
        elif imported >= total and graded == 0:
            new_status = BATCH_STATUS_IMPORTING
        elif graded >= total:
            if needs_review > 0:
                new_status = BATCH_STATUS_NEEDS_REVIEW
            elif reviewed > 0 or batch_id in self._reported_at:
                new_status = BATCH_STATUS_REPORTED
            else:
                new_status = BATCH_STATUS_GRADED
        elif graded > 0:
            if needs_review > 0 and reviewed == 0:
                new_status = BATCH_STATUS_NEEDS_REVIEW
            else:
                new_status = BATCH_STATUS_GRADED
        else:
            new_status = BATCH_STATUS_GRADED

        if batch_id in self._reported_at and new_status in (
            BATCH_STATUS_GRADED,
            BATCH_STATUS_NEEDS_REVIEW,
        ):
            new_status = BATCH_STATUS_REPORTED

        batch["status"] = new_status
        batch["meta"].metadata["status"] = new_status
        return new_status

    # ---------- 批次生成 ----------

    def batch_generate_adaptive(
        self,
        student_ids: Optional[List[str]] = None,
        total_count: int = 10,
        subject: Optional[str] = None,
        title_template: str = "{name}的自适应练习",
        class_id: Optional[str] = None,
        grade: Optional[str] = None,
        batch_id: Optional[str] = None,
        seed: Optional[int] = None,
        creator_id: Optional[str] = None,
    ) -> Tuple[str, List[BatchExamItem], List[SkippedStudent]]:
        bid = batch_id or f"batch_{uuid.uuid4().hex[:10]}"
        items: List[BatchExamItem] = []
        skipped: List[SkippedStudent] = []

        if student_ids is not None:
            target_ids = student_ids
        else:
            target_ids = [p.student_id for p in self.list_students(class_id=class_id, grade=grade)]

        processed_ids = set()
        for i, sid in enumerate(target_ids):
            if sid in processed_ids:
                skipped.append(SkippedStudent(student_id=sid, reason="学生ID重复，已跳过"))
                continue
            processed_ids.add(sid)

            profile = self._students.get(sid)
            if not profile:
                skipped.append(SkippedStudent(student_id=sid, reason="学生档案不存在"))
                continue

            if class_id and profile.class_id != class_id:
                skipped.append(SkippedStudent(
                    student_id=sid,
                    student_name=profile.student_name,
                    reason=f"班级不匹配（档案为{profile.class_id}，要求{class_id}）",
                ))
                continue
            if grade and profile.grade != grade:
                skipped.append(SkippedStudent(
                    student_id=sid,
                    student_name=profile.student_name,
                    reason=f"年级不匹配（档案为{profile.grade}，要求{grade}）",
                ))
                continue

            try:
                paper, rationale = self._adaptive.build_adaptive(
                    wrong_book=profile.wrong_book,
                    weak_knowledge_points=profile.weak_knowledge_points,
                    total_count=total_count,
                    student_id=sid,
                    grade=profile.grade,
                    subject=subject,
                    title=title_template.format(name=profile.student_name or sid),
                    seed=(seed + i) if seed is not None else None,
                )
            except Exception as e:
                skipped.append(SkippedStudent(
                    student_id=sid,
                    student_name=profile.student_name,
                    reason=f"自适应组卷失败：{e}",
                ))
                continue

            if not paper or len(paper.questions) == 0:
                skipped.append(SkippedStudent(
                    student_id=sid,
                    student_name=profile.student_name,
                    reason="题库中未找到符合条件的题目",
                ))
                continue

            session = self._sessions.create_session(
                student_id=sid,
                exam_paper=paper,
                metadata={
                    "batch_id": bid,
                    "class_id": class_id or profile.class_id,
                    "grade": grade or profile.grade,
                },
            )

            item = BatchExamItem(
                student_id=sid,
                exam_paper=paper,
                rationale=rationale,
                session_id=session.id,
                source_type="adaptive",
                question_count=len(paper.questions),
                estimated_minutes=_estimate_minutes(paper),
                weak_basis=_build_weak_basis(profile, rationale),
                status="generated",
                import_status="pending",
            )
            items.append(item)

        meta = BatchMeta(
            batch_id=bid,
            class_id=class_id,
            subject=subject,
            grade=grade,
            title_template=title_template,
            total_count=total_count,
            creator_id=creator_id,
            metadata={"status": BATCH_STATUS_GENERATED},
        )
        self._class_exams[bid] = {
            "meta": meta,
            "items": items,
            "skipped": skipped,
            "status": BATCH_STATUS_GENERATED,
            "distributed_at": None,
            "last_import_at": None,
        }
        return bid, items, skipped

    # ---------- 补卷 / 重卷 ----------

    def regenerate_for_students(
        self,
        batch_id: str,
        student_ids: List[str],
        total_count: Optional[int] = None,
        seed_offset: int = 1000,
    ) -> Tuple[List[BatchExamItem], List[SkippedStudent]]:
        batch = self._get_batch(batch_id)
        meta: BatchMeta = batch["meta"]
        items: List[BatchExamItem] = batch["items"]
        skipped: List[SkippedStudent] = batch.get("skipped", [])
        new_items: List[BatchExamItem] = []
        new_skipped: List[SkippedStudent] = []

        for idx, sid in enumerate(student_ids):
            profile = self._students.get(sid)
            if not profile:
                new_skipped.append(SkippedStudent(student_id=sid, reason="学生档案不存在，无法补卷"))
                continue

            old_idx = next((i for i, it in enumerate(items) if it.student_id == sid), None)
            old_session_id = None
            if old_idx is not None:
                old_item = items[old_idx]
                old_session_id = old_item.session_id
                if old_session_id:
                    try:
                        old_sess = self._sessions.get_session(old_session_id)
                        if old_sess and old_sess.status in ("graded", "reviewed", "closed"):
                            new_skipped.append(SkippedStudent(
                                student_id=sid,
                                student_name=profile.student_name,
                                reason=f"该生会话已是{old_sess.status}状态，不可重卷",
                            ))
                            continue
                    except ValueError:
                        pass

            try:
                paper, rationale = self._adaptive.build_adaptive(
                    wrong_book=profile.wrong_book,
                    weak_knowledge_points=profile.weak_knowledge_points,
                    total_count=total_count or meta.total_count,
                    student_id=sid,
                    grade=profile.grade,
                    subject=meta.subject,
                    title=meta.title_template.format(name=profile.student_name or sid),
                    seed=seed_offset + idx,
                )
            except Exception as e:
                new_skipped.append(SkippedStudent(
                    student_id=sid,
                    student_name=profile.student_name,
                    reason=f"补卷失败：{e}",
                ))
                continue

            if not paper or len(paper.questions) == 0:
                new_skipped.append(SkippedStudent(
                    student_id=sid,
                    student_name=profile.student_name,
                    reason="题库中未找到符合条件的题目",
                ))
                continue

            session = self._sessions.create_session(
                student_id=sid,
                exam_paper=paper,
                metadata={
                    "batch_id": batch_id,
                    "class_id": meta.class_id,
                    "grade": meta.grade,
                    "regenerated": True,
                },
            )

            item = BatchExamItem(
                student_id=sid,
                exam_paper=paper,
                rationale=rationale,
                session_id=session.id,
                source_type="regenerated",
                question_count=len(paper.questions),
                estimated_minutes=_estimate_minutes(paper),
                weak_basis=_build_weak_basis(profile, rationale),
                status="regenerated",
                import_status="pending",
                regenerated_from=old_session_id,
                regenerated_at=datetime.now(),
            )

            if old_idx is not None:
                items[old_idx] = item
            else:
                items.append(item)
            new_items.append(item)

        batch["skipped"] = skipped + new_skipped
        self._auto_update_batch_status(batch_id)
        return new_items, new_skipped

    # ---------- 状态流转显式操作 ----------

    def mark_batch_distributed(self, batch_id: str) -> str:
        batch = self._get_batch(batch_id)
        batch["distributed_at"] = datetime.now()
        self._set_batch_status(batch_id, BATCH_STATUS_DISTRIBUTED)
        return BATCH_STATUS_DISTRIBUTED

    def mark_batch_archived(self, batch_id: str) -> str:
        self._get_batch(batch_id)
        self._set_batch_status(batch_id, BATCH_STATUS_ARCHIVED)
        self._archived_at[batch_id] = datetime.now()
        return BATCH_STATUS_ARCHIVED

    def get_batch_status(self, batch_id: str) -> str:
        self._auto_update_batch_status(batch_id)
        return self._get_batch(batch_id).get("status", BATCH_STATUS_GENERATED)

    def get_batch_status_label(self, batch_id: str) -> str:
        return BATCH_STATUS_LABEL.get(self.get_batch_status(batch_id), "未知")

    # ---------- 阶段查询 ----------

    def get_not_submitted_students(self, batch_id: str) -> List[Dict[str, Any]]:
        items = self.get_batch_items(batch_id)
        result = []
        for it in items:
            if it.import_status in ("success", "partial"):
                continue
            if it.session_id:
                sess = self._sessions.get_session(it.session_id)
                if sess and sess.status in ("created", "answering"):
                    profile = self._students.get(it.student_id)
                    result.append({
                        "student_id": it.student_id,
                        "student_name": profile.student_name if profile else "",
                        "session_id": it.session_id,
                        "status": sess.status,
                        "answers_count": len(sess.answers),
                        "question_count": it.question_count,
                    })
        return result

    def get_import_failed_students(self, batch_id: str) -> List[Dict[str, Any]]:
        items = self.get_batch_items(batch_id)
        result = []
        for it in items:
            if it.import_status in ("error", "skipped") or it.import_errors:
                profile = self._students.get(it.student_id)
                result.append({
                    "student_id": it.student_id,
                    "student_name": profile.student_name if profile else "",
                    "import_status": it.import_status,
                    "errors": it.import_errors,
                    "notes": it.import_notes,
                })
        return result

    def get_needs_teacher_review_students(self, batch_id: str) -> List[Dict[str, Any]]:
        items = self.get_batch_items(batch_id)
        result = []
        for it in items:
            if it.session_id:
                sess = self._sessions.get_session(it.session_id)
                if sess and sess.status in ("graded", "reviewed") and sess.exam_result:
                    pending = [
                        qr for qr in sess.exam_result.question_results
                        if qr.question_type == QuestionType.SHORT_ANSWER
                        and (qr.review_info is None or qr.review_info.review_status == "auto")
                    ]
                    if pending:
                        profile = self._students.get(it.student_id)
                        result.append({
                            "student_id": it.student_id,
                            "student_name": profile.student_name if profile else "",
                            "session_id": it.session_id,
                            "pending_questions": len(pending),
                            "question_ids": [qr.question_id for qr in pending],
                        })
        return result

    # ---------- 批量导入答案 ----------

    def batch_import_answers(
        self,
        batch_id: str,
        answers_by_student: Dict[str, Dict[str, Any]],
        allow_partial: bool = True,
        skip_duplicated: bool = True,
        strict_mode: bool = False,
        idempotent: bool = True,
    ) -> BatchImportResult:
        batch = self._get_batch(batch_id)
        items: List[BatchExamItem] = batch["items"]
        item_by_sid: Dict[str, BatchExamItem] = {it.student_id: it for it in items}

        result = BatchImportResult(batch_id=batch_id)

        for sid, q_answers in answers_by_student.items():
            import_res = StudentImportResult(
                student_id=sid,
                status="pending",
                total_count=len(q_answers) if isinstance(q_answers, dict) else 0,
            )

            item = item_by_sid.get(sid)
            if not item:
                import_res.status = "skipped"
                import_res.errors.append("该学生不在当前批次中，已跳过")
                result.skipped_count += 1
                result.per_student.append(import_res)
                continue

            session = self._sessions.get_session(item.session_id) if item.session_id else None
            if not session:
                import_res.status = "error"
                import_res.errors.append("会话不存在，可能批次已损坏")
                result.error_count += 1
                item.import_status = "error"
                item.import_errors = list(import_res.errors)
                result.per_student.append(import_res)
                continue

            if session.status in ("graded", "reviewed", "closed"):
                if skip_duplicated:
                    import_res.status = "skipped"
                    import_res.errors.append(f"会话已处于{session.status}状态，重复导入已跳过")
                    import_res.was_processed = True
                    result.skipped_count += 1
                    item.import_status = "skipped"
                    item.import_notes = f"重复导入跳过（{session.status}）"
                    result.per_student.append(import_res)
                    continue

            if idempotent and session.answers:
                overlap = [qid for qid in (q_answers or {}) if qid in session.answers]
                if overlap:
                    import_res.was_processed = True
                    import_res.errors.append(
                        f"已存在{len(overlap)}道题的作答，按幂等策略跳过覆盖"
                    )
                    only_new = {qid: a for qid, a in (q_answers or {}).items()
                                if qid not in session.answers}
                    if not only_new:
                        import_res.status = "skipped"
                        result.skipped_count += 1
                        item.import_status = "skipped"
                        item.import_errors = list(import_res.errors)
                        result.per_student.append(import_res)
                        continue
                    q_answers = only_new

            valid_questions = {q.id for q in item.exam_paper.questions} if item.exam_paper else set()
            valid_answers: Dict[str, Any] = {}
            invalid_qids: List[str] = []
            for qid, ans in (q_answers or {}).items():
                if qid not in valid_questions:
                    invalid_qids.append(qid)
                    if strict_mode:
                        break
                    import_res.errors.append(f"题目{qid}不在该试卷中，已忽略")
                    continue
                valid_answers[qid] = ans

            if strict_mode and invalid_qids:
                import_res.status = "error"
                import_res.errors.append(
                    f"严格模式：存在{len(invalid_qids)}道非法题号（如{invalid_qids[0]}），整份不写入"
                )
                result.error_count += 1
                item.import_status = "error"
                item.import_errors = list(import_res.errors)
                result.per_student.append(import_res)
                continue

            if not valid_answers:
                import_res.status = "skipped"
                import_res.errors.append("没有可导入的有效答案")
                result.skipped_count += 1
                item.import_status = "skipped"
                item.import_errors = list(import_res.errors)
                result.per_student.append(import_res)
                continue

            try:
                self._sessions.submit_answers(item.session_id, valid_answers)
                import_res.imported_count = len(valid_answers)
                if len(import_res.errors) == 0:
                    import_res.status = "success"
                    result.success_count += 1
                    item.import_status = "success"
                else:
                    import_res.status = "partial"
                    result.partial_count += 1
                    item.import_status = "partial"
                item.import_errors = list(import_res.errors)
                item.status = "answered"
            except Exception as e:
                import_res.status = "error"
                import_res.errors.append(f"提交答案失败：{e}")
                result.error_count += 1
                item.import_status = "error"
                item.import_errors = list(import_res.errors)

            result.per_student.append(import_res)

        batch["last_import_at"] = datetime.now()
        self._auto_update_batch_status(batch_id)
        return result

    # ---------- 批量批改 ----------

    def batch_grade(
        self,
        batch_id: str,
        skip_already_graded: bool = True,
    ) -> Tuple[Dict[str, ExamResult], List[StudentImportResult]]:
        batch = self._get_batch(batch_id)
        items: List[BatchExamItem] = batch["items"]

        results: Dict[str, ExamResult] = {}
        summaries: List[StudentImportResult] = []

        for item in items:
            summary = StudentImportResult(student_id=item.student_id, status="pending")
            session = self._sessions.get_session(item.session_id) if item.session_id else None
            if not session:
                summary.status = "skipped"
                summary.errors.append("会话不存在")
                summaries.append(summary)
                continue
            if skip_already_graded and session.status in ("graded", "reviewed", "closed"):
                summary.status = "skipped"
                summary.errors.append(f"已处于{session.status}状态，跳过重复批改")
                summary.was_processed = True
                summaries.append(summary)
                if session.exam_result:
                    results[item.student_id] = session.exam_result
                continue
            if session.status not in ("created", "answering"):
                summary.status = "skipped"
                summary.errors.append(f"状态{session.status}不可批改")
                summaries.append(summary)
                continue
            if not session.exam_paper:
                summary.status = "error"
                summary.errors.append("会话无关联试卷")
                summaries.append(summary)
                continue
            try:
                er = self._sessions.grade_session(item.session_id)
                results[item.student_id] = er
                summary.status = "success"
                item.status = "graded"
            except Exception as e:
                summary.status = "error"
                summary.errors.append(f"批改异常：{e}")
            summaries.append(summary)

        self._auto_update_batch_status(batch_id)
        return results, summaries

    # ---------- 班级报告 ----------

    def generate_class_report(
        self,
        batch_id: str,
        class_id: Optional[str] = None,
        pass_line: float = 60.0,
        excellent_line: float = 90.0,
        report_link: str = "",
    ) -> ClassReportSummary:
        batch = self._get_batch(batch_id)
        items: List[BatchExamItem] = batch["items"]
        student_reports: List[StudentReportSummary] = []
        all_results: List[ExamResult] = []
        all_kp_stats: Dict[str, List[KnowledgePointStats]] = {}
        all_kp_errors: Dict[str, Dict[str, Any]] = {}
        basic_tier: List[StudentReportSummary] = []
        advanced_tier: List[StudentReportSummary] = []
        review_tier: List[StudentReportSummary] = []

        for item in items:
            session = self._sessions.get_session(item.session_id) if item.session_id else None
            if not session or not session.exam_result:
                continue

            er = session.exam_result
            all_results.append(er)

            profile = self._students.get(item.student_id)
            name = profile.student_name if profile else ""

            kp_stats = self._analytics.analyze_knowledge_points([er])
            weak_kps = self._analytics.get_weak_knowledge_points([er])
            strong_kps = [kp.knowledge_point for kp in kp_stats if kp.mastery_level >= 80]
            weak_kp_names = [kp.knowledge_point for kp in weak_kps[:5]]

            suggestions = self._analytics.generate_study_suggestions(
                wrong_questions=self._analytics.collect_wrong_questions([er]),
                weak_knowledge_points=weak_kps,
                total_score=er.total_score,
                max_score=er.max_score,
            )

            review_stats = self._analytics.analyze_review_status([er])

            tier = ""
            if review_stats["pending_review"] > 0:
                tier = "needs_review"
            elif er.percentage < pass_line:
                tier = "basic"
            elif er.percentage >= excellent_line:
                tier = "advanced"
            else:
                tier = "stable"

            srs = StudentReportSummary(
                student_id=item.student_id,
                student_name=name,
                total_score=er.total_score,
                max_score=er.max_score,
                percentage=er.percentage,
                correct_count=er.correct_count,
                wrong_count=er.wrong_count,
                pending_review_count=review_stats["pending_review"],
                grade_level=self._grade_level(er.percentage),
                strong_points=strong_kps[:3],
                weak_points=weak_kp_names,
                suggestions=suggestions[:5],
                review_adjustment=review_stats["review_adjustment"],
                tier=tier,
            )
            student_reports.append(srs)

            if tier == "basic":
                basic_tier.append(srs)
            elif tier == "advanced":
                advanced_tier.append(srs)
            if tier == "needs_review":
                review_tier.append(srs)

            for ks in kp_stats:
                if ks.knowledge_point not in all_kp_stats:
                    all_kp_stats[ks.knowledge_point] = []
                all_kp_stats[ks.knowledge_point].append(ks)

            for qr in er.wrong_questions:
                for kp in qr.knowledge_points:
                    if kp not in all_kp_errors:
                        all_kp_errors[kp] = {"error_students": {}, "q_ids": {}}
                    all_kp_errors[kp]["error_students"][item.student_id] = srs
                    all_kp_errors[kp]["q_ids"][qr.question_id] = qr

        student_reports.sort(key=lambda s: s.percentage, reverse=True)
        for i, s in enumerate(student_reports):
            s.rank = i + 1

        n = len(student_reports)
        if n == 0:
            avg = 0.0
            max_s = 0.0
            min_s = 0.0
            pass_r = 0.0
            excellent_r = 0.0
            grade_dist = {}
        else:
            scores = [s.percentage for s in student_reports]
            avg = sum(scores) / n
            max_s = max(scores)
            min_s = min(scores)
            pass_r = sum(1 for s in scores if s >= pass_line) / n * 100
            excellent_r = sum(1 for s in scores if s >= excellent_line) / n * 100

            grade_dist = {"优秀": 0, "良好": 0, "中等": 0, "及格": 0, "不及格": 0}
            for s in student_reports:
                g = s.grade_level
                if g in grade_dist:
                    grade_dist[g] += 1

        class_strong = []
        class_weak = []
        if all_kp_stats:
            avg_mastery = []
            for kp, stats_list in all_kp_stats.items():
                if stats_list:
                    avg_m = sum(s.mastery_level for s in stats_list) / len(stats_list)
                    avg_mastery.append((kp, avg_m))
            avg_mastery.sort(key=lambda x: x[1], reverse=True)
            class_strong = [kp for kp, m in avg_mastery[:3] if m >= 70]
            class_weak = [kp for kp, m in avg_mastery[-3:] if m < 70]

        weak_matrix: List[WeakKPMatrixRow] = []
        for kp, err in all_kp_errors.items():
            stats_list = all_kp_stats.get(kp, [])
            avg_m = (
                sum(s.mastery_level for s in stats_list) / len(stats_list)
                if stats_list
                else 0.0
            )
            weak_matrix.append(WeakKPMatrixRow(
                knowledge_point=kp,
                student_count=n,
                error_count=len(err["error_students"]),
                error_rate=(len(err["error_students"]) / n * 100) if n > 0 else 0.0,
                avg_mastery=avg_m,
                typical_question_ids=list(err["q_ids"].keys())[:5],
            ))
        weak_matrix.sort(key=lambda r: r.error_rate, reverse=True)

        exam_title = items[0].exam_paper.title if items else "班级练习报告"
        subject = items[0].exam_paper.subject if items else None

        report = ClassReportSummary(
            batch_id=batch_id,
            class_id=class_id,
            subject=subject,
            exam_title=exam_title,
            student_count=n,
            average_score=avg,
            max_score=max_s,
            min_score=min_s,
            pass_rate=pass_r,
            excellent_rate=excellent_r,
            grade_distribution=grade_dist,
            class_strong_points=class_strong,
            class_weak_points=class_weak,
            student_reports=student_reports,
            weak_kp_matrix=weak_matrix,
            tiered_students=TieredStudents(
                basic_tier=basic_tier,
                advanced_tier=advanced_tier,
                review_tier=review_tier,
            ),
        )

        self._reported_at[batch_id] = datetime.now()
        if report_link:
            self._report_links[batch_id] = report_link
        self._auto_update_batch_status(batch_id)
        return report

    # ---------- 班级讲评包 ----------

    def generate_class_comment_package(
        self,
        batch_id: str,
        class_id: Optional[str] = None,
        pass_line: float = 60.0,
        extra_questions_per_kp: int = 2,
    ) -> ClassCommentPackage:
        report = self.generate_class_report(
            batch_id=batch_id,
            class_id=class_id,
            pass_line=pass_line,
        )
        batch = self._get_batch(batch_id)
        items: List[BatchExamItem] = batch["items"]
        all_results: List[ExamResult] = []
        kp_to_students: Dict[str, List[StudentReportSummary]] = {}
        kp_to_wrong_qrs: Dict[str, List[Any]] = {}
        kp_to_q_objs: Dict[str, Dict[str, Any]] = {}

        for item in items:
            session = self._sessions.get_session(item.session_id) if item.session_id else None
            if not session or not session.exam_result:
                continue
            er = session.exam_result
            all_results.append(er)
            profile = self._students.get(item.student_id)
            srs = next((s for s in report.student_reports if s.student_id == item.student_id), None)
            if srs is None:
                continue

            for qr in er.wrong_questions:
                for kp in qr.knowledge_points:
                    if kp not in kp_to_students:
                        kp_to_students[kp] = []
                        kp_to_wrong_qrs[kp] = []
                        kp_to_q_objs[kp] = {}
                    if not any(s.student_id == item.student_id for s in kp_to_students[kp]):
                        kp_to_students[kp].append(srs)
                    kp_to_wrong_qrs[kp].append(qr)
                    if item.exam_paper:
                        q_obj = next((q for q in item.exam_paper.questions if q.id == qr.question_id), None)
                        if q_obj and q_obj.id not in kp_to_q_objs[kp]:
                            kp_to_q_objs[kp][q_obj.id] = q_obj

        n = len(report.student_reports) or 1
        kp_sections: List[CommentKPSection] = []
        for kp, students in kp_to_students.items():
            err_rate = len(students) / n * 100
            avg_m = 0.0
            for row in report.weak_kp_matrix:
                if row.knowledge_point == kp:
                    avg_m = row.avg_mastery
                    break

            typical_wrong = []
            for qr in kp_to_wrong_qrs.get(kp, [])[:3]:
                typical_wrong.append({
                    "question_id": qr.question_id,
                    "student_answer": qr.student_answer,
                    "correct_answer": qr.correct_answer,
                    "feedback": qr.feedback,
                })

            affected = [
                {
                    "student_id": s.student_id,
                    "student_name": s.student_name,
                    "percentage": s.percentage,
                    "wrong_count": s.wrong_count,
                }
                for s in sorted(students, key=lambda x: x.percentage)
            ]

            extra_questions = []
            if self._bank:
                try:
                    pool = self._bank.filter_questions(
                        knowledge_points=[kp],
                        subject=report.subject,
                        grade=batch["meta"].grade,
                    )
                    for q in pool[:extra_questions_per_kp]:
                        extra_questions.append({
                            "question_id": q.id,
                            "content": q.content,
                            "question_type": q.question_type.value,
                            "difficulty": q.difficulty.value,
                            "score": q.score,
                        })
                except Exception:
                    pass

            kp_sections.append(CommentKPSection(
                knowledge_point=kp,
                error_rate=err_rate,
                error_student_count=len(students),
                avg_mastery=avg_m,
                typical_wrong_questions=typical_wrong,
                affected_students=affected,
                teaching_tips=_kp_teaching_tip(kp, err_rate),
                recommended_extra_questions=extra_questions,
            ))

        kp_sections.sort(key=lambda s: (-s.error_rate, -s.error_student_count))
        for i, sec in enumerate(kp_sections):
            sec.suggested_order = i + 1

        class_overview = {
            "student_count": report.student_count,
            "average_score": report.average_score,
            "pass_rate": report.pass_rate,
            "excellent_rate": report.excellent_rate,
            "max_score": report.max_score,
            "min_score": report.min_score,
            "class_strong_points": report.class_strong_points,
            "class_weak_points": report.class_weak_points,
            "grade_distribution": report.grade_distribution,
            "basic_count": len(report.tiered_students.basic_tier),
            "advanced_count": len(report.tiered_students.advanced_tier),
            "review_count": len(report.tiered_students.review_tier),
        }

        all_affected_set: Dict[str, Dict[str, Any]] = {}
        for sec in kp_sections:
            for s in sec.affected_students:
                all_affected_set.setdefault(s["student_id"], {
                    "student_id": s["student_id"],
                    "student_name": s["student_name"],
                    "percentage": s["percentage"],
                    "weak_kp_count": 0,
                })
                all_affected_set[s["student_id"]]["weak_kp_count"] += 1
        all_affected = sorted(
            all_affected_set.values(),
            key=lambda x: (-x["weak_kp_count"], x["percentage"]),
        )

        return ClassCommentPackage(
            batch_id=batch_id,
            class_id=class_id or report.class_id,
            subject=report.subject,
            exam_title=report.exam_title,
            class_overview=class_overview,
            kp_sections=kp_sections,
            all_affected_students=all_affected,
            recommended_review_order=[s.knowledge_point for s in kp_sections],
        )

    # ---------- 对外摘要 / 回执 ----------

    def build_batch_summary(
        self,
        batch_id: str,
        include_per_student: bool = True,
    ) -> BatchSummary:
        self._auto_update_batch_status(batch_id)
        batch = self._get_batch(batch_id)
        meta: BatchMeta = batch["meta"]
        items: List[BatchExamItem] = batch["items"]

        total = len(items)
        generated = 0
        not_submitted = 0
        submitted = 0
        graded = 0
        needs_review = 0
        reviewed = 0
        failed = 0
        per_student_list: List[Dict[str, Any]] = []

        for it in items:
            generated += 1
            sess = self._sessions.get_session(it.session_id) if it.session_id else None
            if not sess:
                failed += 1
                if include_per_student:
                    per_student_list.append({
                        "student_id": it.student_id,
                        "student_name": self._students.get(it.student_id, StudentProfile("")).student_name,
                        "status": "error",
                        "import_status": it.import_status,
                        "errors": it.import_errors,
                    })
                continue

            has_answer = bool(sess.answers)
            if sess.status in ("created", "answering") and not has_answer:
                not_submitted += 1
            if has_answer or sess.status in ("answering", "graded", "reviewed", "closed"):
                submitted += 1
            if sess.status in ("graded", "reviewed", "closed"):
                graded += 1
            if sess.status in ("reviewed", "closed"):
                reviewed += 1
            pending = 0
            if sess.exam_result:
                pending = sum(
                    1 for qr in sess.exam_result.question_results
                    if qr.question_type == QuestionType.SHORT_ANSWER
                    and (qr.review_info is None or qr.review_info.review_status == "auto")
                )
            if pending > 0:
                needs_review += 1
            if it.import_status in ("error",):
                failed += 1

            if include_per_student:
                profile = self._students.get(it.student_id)
                per_student_list.append({
                    "student_id": it.student_id,
                    "student_name": profile.student_name if profile else "",
                    "session_id": it.session_id,
                    "session_status": sess.status,
                    "import_status": it.import_status,
                    "pending_review_count": pending,
                    "errors": it.import_errors,
                    "percentage": sess.exam_result.percentage if sess.exam_result else None,
                })

        status = batch.get("status", BATCH_STATUS_GENERATED)
        return BatchSummary(
            batch_id=batch_id,
            status=status,
            status_label=BATCH_STATUS_LABEL.get(status, "未知"),
            class_id=meta.class_id,
            subject=meta.subject,
            grade=meta.grade,
            student_total=total,
            student_generated=generated,
            student_not_submitted=not_submitted,
            student_submitted=submitted,
            student_graded=graded,
            student_needs_review=needs_review,
            student_reviewed=reviewed,
            student_failed=failed,
            created_at=meta.created_at,
            reported_at=self._reported_at.get(batch_id),
            archived_at=self._archived_at.get(batch_id),
            report_link=self._report_links.get(batch_id, ""),
            per_student=per_student_list,
        )

    def build_import_receipt(
        self,
        import_result: BatchImportResult,
        report_link: str = "",
    ) -> ImportReceipt:
        receipt = ImportReceipt(
            batch_id=import_result.batch_id,
            total_submitted=len(import_result.per_student),
            success_count=import_result.success_count,
            partial_count=import_result.partial_count,
            skipped_count=import_result.skipped_count,
            error_count=import_result.error_count,
            per_student=[r.to_dict() for r in import_result.per_student],
            report_link=report_link or self._report_links.get(import_result.batch_id, ""),
        )
        return receipt

    # ---------- 访问器 ----------

    def get_batch_meta(self, batch_id: str) -> BatchMeta:
        return self._get_batch(batch_id)["meta"]

    def get_skipped_students(self, batch_id: str) -> List[SkippedStudent]:
        return self._get_batch(batch_id).get("skipped", [])

    def get_session_manager(self) -> SessionManager:
        return self._sessions

    def get_batch_items(self, batch_id: str) -> List[BatchExamItem]:
        return self._get_batch(batch_id)["items"]

    def _grade_level(self, percentage: float) -> str:
        if percentage >= 90:
            return "优秀"
        elif percentage >= 80:
            return "良好"
        elif percentage >= 70:
            return "中等"
        elif percentage >= 60:
            return "及格"
        else:
            return "不及格"
