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
class BatchExamItem:
    student_id: str
    exam_paper: ExamPaper
    rationale: Optional[AdaptiveRationale] = None
    session_id: Optional[str] = None


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
        }


@dataclass
class ClassReportSummary:
    class_id: Optional[str]
    subject: Optional[str]
    exam_title: str
    student_count: int
    average_score: float
    max_score: float
    min_score: float
    pass_rate: float
    excellent_rate: float
    grade_distribution: Dict[str, int] = field(default_factory=dict)
    class_strong_points: List[str] = field(default_factory=list)
    class_weak_points: List[str] = field(default_factory=dict)
    student_reports: List[StudentReportSummary] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
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
            "generated_at": self.generated_at.isoformat(),
        }


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
        self._class_exams: Dict[str, List[BatchExamItem]] = {}

    def add_student(self, profile: StudentProfile) -> None:
        self._students[profile.student_id] = profile

    def add_students(self, profiles: List[StudentProfile]) -> None:
        for p in profiles:
            self.add_student(p)

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        return self._students.get(student_id)

    def batch_generate_adaptive(
        self,
        student_ids: Optional[List[str]] = None,
        total_count: int = 10,
        subject: Optional[str] = None,
        title_template: str = "{name}的自适应练习",
        class_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Tuple[str, List[BatchExamItem]]:
        bid = batch_id or f"batch_{uuid.uuid4().hex[:10]}"
        items: List[BatchExamItem] = []

        targets = student_ids if student_ids else list(self._students.keys())

        for i, sid in enumerate(targets):
            profile = self._students.get(sid)
            if not profile:
                continue

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

            session = self._sessions.create_session(
                student_id=sid,
                exam_paper=paper,
                metadata={"batch_id": bid, "class_id": class_id},
            )

            items.append(BatchExamItem(
                student_id=sid,
                exam_paper=paper,
                rationale=rationale,
                session_id=session.id,
            ))

        self._class_exams[bid] = items
        return bid, items

    def batch_import_answers(
        self,
        batch_id: str,
        answers_by_student: Dict[str, Dict[str, Any]],
    ) -> Dict[str, PracticeSession]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")

        results: Dict[str, PracticeSession] = {}
        for item in self._class_exams[batch_id]:
            if item.student_id in answers_by_student and item.session_id:
                answers = answers_by_student[item.student_id]
                session = self._sessions.submit_answers(item.session_id, answers)
                results[item.student_id] = session
        return results

    def batch_grade(
        self,
        batch_id: str,
    ) -> Dict[str, ExamResult]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")

        results: Dict[str, ExamResult] = {}
        for item in self._class_exams[batch_id]:
            if item.session_id:
                result = self._sessions.grade_session(item.session_id)
                results[item.student_id] = result
        return results

    def generate_class_report(
        self,
        batch_id: str,
        class_id: Optional[str] = None,
        pass_line: float = 60.0,
        excellent_line: float = 90.0,
    ) -> ClassReportSummary:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")

        items = self._class_exams[batch_id]
        student_reports: List[StudentReportSummary] = []
        all_results: List[ExamResult] = []
        all_kp_stats: Dict[str, List[KnowledgePointStats]] = {}

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
            )
            student_reports.append(srs)

            for ks in kp_stats:
                if ks.knowledge_point not in all_kp_stats:
                    all_kp_stats[ks.knowledge_point] = []
                all_kp_stats[ks.knowledge_point].append(ks)

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

        exam_title = items[0].exam_paper.title if items else "班级练习报告"
        subject = items[0].exam_paper.subject if items else None

        return ClassReportSummary(
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
        )

    def get_session_manager(self) -> SessionManager:
        return self._sessions

    def get_batch_items(self, batch_id: str) -> List[BatchExamItem]:
        if batch_id not in self._class_exams:
            raise ValueError(f"未找到批次 {batch_id}")
        return self._class_exams[batch_id]

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
