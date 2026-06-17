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
            "overall_mastery": self.rationale.overall_mastery if self.rationale else None,
            "rationale": self.rationale,
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "status": self.status,
            "imported_count": self.imported_count,
            "total_count": self.total_count,
            "errors": self.errors,
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
        )
        self._class_exams[bid] = {
            "meta": meta,
            "items": items,
            "skipped": skipped,
        }
        return bid, items, skipped

    def batch_import_answers(
        self,
        batch_id: str,
        answers_by_student: Dict[str, Dict[str, Any]],
        allow_partial: bool = True,
        skip_duplicated: bool = True,
    ) -> BatchImportResult:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")

        batch = self._class_exams[batch_id]
        items = batch["items"]
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
                result.per_student.append(import_res)
                continue

            if skip_duplicated and session.status in ("graded", "reviewed", "closed"):
                import_res.status = "skipped"
                import_res.errors.append(f"会话已处于{session.status}状态，重复导入已跳过")
                result.skipped_count += 1
                result.per_student.append(import_res)
                continue

            valid_questions = {q.id for q in item.exam_paper.questions} if item.exam_paper else set()
            valid_answers: Dict[str, Any] = {}
            for qid, ans in (q_answers or {}).items():
                if qid not in valid_questions:
                    import_res.errors.append(f"题目{qid}不在该试卷中，已忽略")
                    if not allow_partial:
                        break
                    continue
                valid_answers[qid] = ans
            else:
                if not allow_partial and len(import_res.errors) > 0:
                    import_res.status = "error"
                    result.error_count += 1
                    result.per_student.append(import_res)
                    continue

            if not valid_answers and allow_partial:
                import_res.status = "skipped"
                import_res.errors.append("没有可导入的有效答案")
                result.skipped_count += 1
                result.per_student.append(import_res)
                continue

            try:
                self._sessions.submit_answers(item.session_id, valid_answers)
                import_res.imported_count = len(valid_answers)
                if len(import_res.errors) == 0:
                    import_res.status = "success"
                    result.success_count += 1
                else:
                    import_res.status = "partial"
                    result.partial_count += 1
                item.status = "answered"
            except Exception as e:
                import_res.status = "error"
                import_res.errors.append(f"提交答案失败：{e}")
                result.error_count += 1

            result.per_student.append(import_res)

        return result

    def batch_grade(
        self,
        batch_id: str,
        skip_already_graded: bool = True,
    ) -> Tuple[Dict[str, ExamResult], List[StudentImportResult]]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")

        batch = self._class_exams[batch_id]
        items = batch["items"]

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
        return results, summaries

    def generate_class_report(
        self,
        batch_id: str,
        class_id: Optional[str] = None,
        pass_line: float = 60.0,
        excellent_line: float = 90.0,
    ) -> ClassReportSummary:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")

        batch = self._class_exams[batch_id]
        items = batch["items"]
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
                        all_kp_errors[kp] = {"error_students": set(), "q_ids": set()}
                    all_kp_errors[kp]["error_students"].add(item.student_id)
                    all_kp_errors[kp]["q_ids"].add(qr.question_id)

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
                typical_question_ids=list(err["q_ids"])[:5],
            ))
        weak_matrix.sort(key=lambda r: r.error_rate, reverse=True)

        exam_title = items[0].exam_paper.title if items else "班级练习报告"
        subject = items[0].exam_paper.subject if items else None

        return ClassReportSummary(
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

    def get_batch_meta(self, batch_id: str) -> BatchMeta:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")
        return self._class_exams[batch_id]["meta"]

    def get_skipped_students(self, batch_id: str) -> List[SkippedStudent]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")
        return self._class_exams[batch_id].get("skipped", [])

    def get_session_manager(self) -> SessionManager:
        return self._sessions

    def get_batch_items(self, batch_id: str) -> List[BatchExamItem]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")
        return self._class_exams[batch_id]["items"]

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
