from typing import List, Dict, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from .models import (
    Question,
    QuestionResult,
    ExamResult,
    WrongQuestion,
    PracticeRecord,
    PracticeSession,
    QuestionType,
    Difficulty,
    ReviewInfo,
)
from .question_bank import QuestionBank


@dataclass
class KnowledgePointStats:
    knowledge_point: str
    total_questions: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    total_score: float = 0.0
    earned_score: float = 0.0
    wrong_question_ids: List[str] = field(default_factory=list)
    question_ids: List[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return round(self.correct_count / self.total_questions * 100, 2)

    @property
    def mastery_level(self) -> float:
        if self.total_score == 0:
            return 0.0
        return round(self.earned_score / self.total_score * 100, 2)

    @property
    def is_weak(self) -> bool:
        return self.mastery_level < 60.0 or self.accuracy < 50.0

    def to_dict(self) -> Dict:
        return {
            "knowledge_point": self.knowledge_point,
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "accuracy": self.accuracy,
            "total_score": self.total_score,
            "earned_score": self.earned_score,
            "mastery_level": self.mastery_level,
            "is_weak": self.is_weak,
            "wrong_question_ids": self.wrong_question_ids,
        }


class Analytics:
    def __init__(self, question_bank: Optional[QuestionBank] = None):
        self._bank = question_bank

    def collect_wrong_questions(
        self,
        exam_results: List[ExamResult],
        student_id: Optional[str] = None,
    ) -> Dict[str, WrongQuestion]:
        wrong_map: Dict[str, WrongQuestion] = {}

        for er in exam_results:
            if student_id and er.student_id != student_id:
                continue
            seen_in_exam: Set[str] = set()
            for qr in er.question_results:
                if not qr.is_correct:
                    if qr.question_id in seen_in_exam:
                        continue
                    seen_in_exam.add(qr.question_id)
                    self._update_wrong_map(wrong_map, qr, er.student_id)

        return wrong_map

    def _update_wrong_map(
        self,
        wrong_map: Dict[str, WrongQuestion],
        qr: QuestionResult,
        student_id: str,
    ) -> None:
        qid = qr.question_id
        q = self._bank.get_question(qid) if self._bank else None

        if qid in wrong_map:
            wq = wrong_map[qid]
            wq.wrong_count += 1
            wq.last_wrong_at = datetime.now()
            if qr.student_answer not in wq.wrong_answers:
                wq.wrong_answers.append(qr.student_answer)
        else:
            now = datetime.now()
            wrong_map[qid] = WrongQuestion(
                question_id=qid,
                question=q,
                wrong_count=1,
                last_wrong_at=now,
                first_wrong_at=now,
                wrong_answers=[qr.student_answer],
                knowledge_points=list(qr.knowledge_points),
                student_id=student_id,
            )

    def merge_wrong_books(
        self,
        *wrong_maps: Dict[str, WrongQuestion],
    ) -> Dict[str, WrongQuestion]:
        merged: Dict[str, WrongQuestion] = {}
        for wm in wrong_maps:
            for qid, wq in wm.items():
                if qid in merged:
                    existing = merged[qid]
                    existing.wrong_count += wq.wrong_count
                    existing.last_wrong_at = max(existing.last_wrong_at, wq.last_wrong_at)
                    existing.first_wrong_at = min(existing.first_wrong_at, wq.first_wrong_at)
                    for wa in wq.wrong_answers:
                        if wa not in existing.wrong_answers:
                            existing.wrong_answers.append(wa)
                    for kp in wq.knowledge_points:
                        if kp not in existing.knowledge_points:
                            existing.knowledge_points.append(kp)
                else:
                    merged[qid] = wq
        return merged

    def analyze_knowledge_points(
        self,
        exam_results: List[ExamResult],
        student_id: Optional[str] = None,
        min_questions: int = 1,
    ) -> List[KnowledgePointStats]:
        kp_map: Dict[str, KnowledgePointStats] = {}

        for er in exam_results:
            if student_id and er.student_id != student_id:
                continue
            for qr in er.question_results:
                for kp in qr.knowledge_points:
                    if kp not in kp_map:
                        kp_map[kp] = KnowledgePointStats(knowledge_point=kp)
                    stats = kp_map[kp]
                    stats.total_questions += 1
                    stats.total_score += qr.max_score
                    stats.earned_score += qr.score
                    if qr.is_correct:
                        stats.correct_count += 1
                    else:
                        stats.wrong_count += 1
                        stats.wrong_question_ids.append(qr.question_id)
                    stats.question_ids.append(qr.question_id)

        result = [s for s in kp_map.values() if s.total_questions >= min_questions]
        result.sort(key=lambda x: x.mastery_level)
        return result

    def get_weak_knowledge_points(
        self,
        exam_results: List[ExamResult],
        student_id: Optional[str] = None,
        top_n: Optional[int] = 10,
    ) -> List[KnowledgePointStats]:
        all_kps = self.analyze_knowledge_points(exam_results, student_id)
        weak = [kp for kp in all_kps if kp.is_weak]
        weak.sort(key=lambda x: x.mastery_level)
        if top_n:
            weak = weak[:top_n]
        return weak

    def analyze_by_question_type(
        self,
        exam_results: List[ExamResult],
        student_id: Optional[str] = None,
    ) -> Dict[str, Dict]:
        type_stats: Dict[str, Dict] = {}

        for er in exam_results:
            if student_id and er.student_id != student_id:
                continue
            for qr in er.question_results:
                t = qr.question_type.display_name if qr.question_type else "未知"
                if t not in type_stats:
                    type_stats[t] = {
                        "type": qr.question_type.value if qr.question_type else None,
                        "type_name": t,
                        "total": 0,
                        "correct": 0,
                        "wrong": 0,
                        "total_score": 0.0,
                        "earned_score": 0.0,
                    }
                s = type_stats[t]
                s["total"] += 1
                s["total_score"] += qr.max_score
                s["earned_score"] += qr.score
                if qr.is_correct:
                    s["correct"] += 1
                else:
                    s["wrong"] += 1

        for t in type_stats:
            s = type_stats[t]
            s["accuracy"] = round(s["correct"] / s["total"] * 100, 2) if s["total"] > 0 else 0.0
            s["score_rate"] = round(s["earned_score"] / s["total_score"] * 100, 2) if s["total_score"] > 0 else 0.0

        return type_stats

    def analyze_by_difficulty(
        self,
        exam_results: List[ExamResult],
        questions_map: Dict[str, Question],
        student_id: Optional[str] = None,
    ) -> Dict[str, Dict]:
        diff_stats: Dict[str, Dict] = {}

        for er in exam_results:
            if student_id and er.student_id != student_id:
                continue
            for qr in er.question_results:
                q = questions_map.get(qr.question_id)
                if q:
                    d = q.difficulty.display_name
                    if d not in diff_stats:
                        diff_stats[d] = {
                            "difficulty": q.difficulty.value,
                            "difficulty_name": d,
                            "total": 0,
                            "correct": 0,
                            "wrong": 0,
                            "total_score": 0.0,
                            "earned_score": 0.0,
                        }
                    s = diff_stats[d]
                    s["total"] += 1
                    s["total_score"] += qr.max_score
                    s["earned_score"] += qr.score
                    if qr.is_correct:
                        s["correct"] += 1
                    else:
                        s["wrong"] += 1

        for d in diff_stats:
            s = diff_stats[d]
            s["accuracy"] = round(s["correct"] / s["total"] * 100, 2) if s["total"] > 0 else 0.0
            s["score_rate"] = round(s["earned_score"] / s["total_score"] * 100, 2) if s["total_score"] > 0 else 0.0

        return diff_stats

    def build_practice_records(
        self,
        exam_results: List[ExamResult],
        student_id: Optional[str] = None,
    ) -> List[PracticeRecord]:
        records = []
        for idx, er in enumerate(exam_results):
            if student_id and er.student_id != student_id:
                continue
            duration = None
            if er.time_spent_seconds:
                duration = round(er.time_spent_seconds / 60, 1)
            record = PracticeRecord(
                id=f"record_{er.exam_id}_{idx}",
                student_id=er.student_id,
                exam_id=er.exam_id,
                question_results=er.question_results,
                total_score=er.total_score,
                max_score=er.max_score,
                percentage=er.percentage,
                practice_date=er.completed_at or datetime.now(),
                duration_minutes=duration,
            )
            records.append(record)
        records.sort(key=lambda r: r.practice_date)
        return records

    def compare_practice_history(
        self,
        practice_records: List[PracticeRecord],
        window_size: int = 5,
    ) -> Dict[str, Any]:
        if not practice_records:
            return {"error": "没有练习记录"}

        records = sorted(practice_records, key=lambda r: r.practice_date)
        n = len(records)

        recent = records[-window_size:] if n >= window_size else records
        earlier = records[:-window_size] if n > window_size else []

        avg_percentage = sum(r.percentage for r in records) / n
        recent_avg = sum(r.percentage for r in recent) / len(recent)
        earlier_avg = sum(r.percentage for r in earlier) / len(earlier) if earlier else None

        trend = "稳定"
        if earlier_avg is not None:
            delta = recent_avg - earlier_avg
            if delta >= 5:
                trend = "显著进步"
            elif delta >= 2:
                trend = "稳步提升"
            elif delta <= -5:
                trend = "明显退步"
            elif delta <= -2:
                trend = "略有下滑"

        max_record = max(records, key=lambda r: r.percentage)
        min_record = min(records, key=lambda r: r.percentage)

        percentages = [r.percentage for r in records]
        if len(percentages) >= 2:
            variance = sum((p - avg_percentage) ** 2 for p in percentages) / len(percentages)
            std_dev = round(variance ** 0.5, 2)
        else:
            std_dev = 0.0

        history = []
        for i, r in enumerate(records):
            prev_pct = records[i - 1].percentage if i > 0 else None
            delta = round(r.percentage - prev_pct, 2) if prev_pct is not None else None
            history.append({
                "id": r.id,
                "date": r.practice_date.isoformat(),
                "percentage": r.percentage,
                "total_score": r.total_score,
                "max_score": r.max_score,
                "correct_count": r.correct_count,
                "wrong_count": r.wrong_count,
                "delta": delta,
                "duration_minutes": r.duration_minutes,
            })

        return {
            "total_practices": n,
            "average_percentage": round(avg_percentage, 2),
            "recent_average": round(recent_avg, 2),
            "earlier_average": round(earlier_avg, 2) if earlier_avg is not None else None,
            "trend": trend,
            "trend_delta": round(recent_avg - earlier_avg, 2) if earlier_avg is not None else None,
            "best": {
                "id": max_record.id,
                "date": max_record.practice_date.isoformat(),
                "percentage": max_record.percentage,
                "score": f"{max_record.total_score}/{max_record.max_score}",
            },
            "worst": {
                "id": min_record.id,
                "date": min_record.practice_date.isoformat(),
                "percentage": min_record.percentage,
                "score": f"{min_record.total_score}/{min_record.max_score}",
            },
            "stability": {
                "std_deviation": std_dev,
                "level": "很稳定" if std_dev < 5 else ("较稳定" if std_dev < 10 else "波动较大"),
            },
            "history": history,
        }

    def calculate_student_overall_report(
        self,
        exam_results: List[ExamResult],
        student_id: str,
        questions_map: Optional[Dict[str, Question]] = None,
    ) -> Dict[str, Any]:
        student_results = [r for r in exam_results if r.student_id == student_id]
        if not student_results:
            return {"error": f"没有找到学生 {student_id} 的记录"}

        practice_records = self.build_practice_records(student_results, student_id)
        history_comparison = self.compare_practice_history(practice_records)
        kp_stats = self.analyze_knowledge_points(student_results, student_id)
        weak_kps = self.get_weak_knowledge_points(student_results, student_id)
        type_stats = self.analyze_by_question_type(student_results, student_id)
        wrong_book = self.collect_wrong_questions(student_results, student_id)

        diff_stats = {}
        if questions_map:
            diff_stats = self.analyze_by_difficulty(student_results, questions_map, student_id)

        latest = max(student_results, key=lambda r: r.completed_at or r.started_at or datetime.min)
        total_questions_answered = sum(len(r.question_results) for r in student_results)
        total_correct = sum(r.correct_count for r in student_results)
        total_wrong = sum(r.wrong_count for r in student_results)

        return {
            "student_id": student_id,
            "practice_count": len(student_results),
            "summary": {
                "total_questions": total_questions_answered,
                "total_correct": total_correct,
                "total_wrong": total_wrong,
                "overall_accuracy": round(total_correct / total_questions_answered * 100, 2) if total_questions_answered > 0 else 0,
                "total_earned_score": round(sum(r.total_score for r in student_results), 2),
                "total_max_score": round(sum(r.max_score for r in student_results), 2),
                "overall_score_rate": round(
                    sum(r.total_score for r in student_results) / sum(r.max_score for r in student_results) * 100, 2
                ) if sum(r.max_score for r in student_results) > 0 else 0,
            },
            "latest_result": latest.to_dict(),
            "history_comparison": history_comparison,
            "knowledge_point_analysis": [kp.to_dict() for kp in kp_stats],
            "weak_knowledge_points": [kp.to_dict() for kp in weak_kps],
            "question_type_analysis": type_stats,
            "difficulty_analysis": diff_stats,
            "wrong_book_summary": {
                "total_wrong": len(wrong_book),
                "frequently_wrong": sorted(
                    [wq.to_dict() for wq in wrong_book.values() if wq.wrong_count >= 2],
                    key=lambda x: x["wrong_count"],
                    reverse=True,
                ),
            },
            "suggestions": self._generate_suggestions(weak_kps, type_stats, history_comparison),
        }

    def generate_study_suggestions(
        self,
        wrong_questions: List[WrongQuestion],
        weak_knowledge_points: List[KnowledgePointStats],
        total_score: float,
        max_score: float,
    ) -> List[str]:
        suggestions = []
        percentage = (total_score / max_score * 100) if max_score > 0 else 0

        if weak_knowledge_points:
            kp_names = "、".join([kp.knowledge_point for kp in weak_knowledge_points[:5]])
            suggestions.append(f"重点加强薄弱知识点：{kp_names}，建议进行针对性练习。")

        if wrong_questions:
            suggestions.append(f"本次共有{len(wrong_questions)}道错题，建议整理错题本，定期复习巩固。")

        if percentage >= 90:
            suggestions.append("整体掌握良好，可以尝试更高难度的综合题，拓展解题思路。")
        elif percentage >= 70:
            suggestions.append("基础掌握不错，建议适当增加综合题练习，提升知识应用能力。")
        elif percentage >= 60:
            suggestions.append("基础有待加强，建议多做基础题，巩固核心概念和公式。")
        else:
            suggestions.append("基础较为薄弱，建议从基础题开始，循序渐进，逐步提升。")

        return suggestions

    def _generate_suggestions(
        self,
        weak_kps: List[KnowledgePointStats],
        type_stats: Dict[str, Dict],
        history_comparison: Dict[str, Any],
    ) -> List[str]:
        suggestions = []

        if weak_kps:
            kp_names = "、".join([kp.knowledge_point for kp in weak_kps[:5]])
            suggestions.append(f"重点加强薄弱知识点：{kp_names}，建议进行针对性练习。")

        for t, s in type_stats.items():
            if s["accuracy"] < 50:
                suggestions.append(f"{t}正确率较低（{s['accuracy']}%），建议多做此类题目熟悉解题思路。")

        trend = history_comparison.get("trend", "")
        if "进步" in trend or "提升" in trend:
            suggestions.append("近期成绩呈上升趋势，继续保持！可以适当增加难度挑战自己。")
        elif "退步" in trend or "下滑" in trend:
            suggestions.append("近期成绩有所波动，建议复习错题本，巩固基础知识点。")

        stability = history_comparison.get("stability", {}).get("level", "")
        if "波动" in stability:
            suggestions.append("成绩波动较大，建议建立稳定的练习节奏，避免知识遗忘。")

        if not suggestions:
            suggestions.append("表现良好，建议保持现有学习节奏，可尝试更高难度题目挑战自我。")

        return suggestions

    def sessions_to_exam_results(
        self,
        sessions: List[PracticeSession],
        student_id: Optional[str] = None,
    ) -> List[ExamResult]:
        results = []
        for s in sessions:
            if not s.exam_result:
                continue
            if student_id and s.student_id != student_id:
                continue
            results.append(s.exam_result)
        return results

    def analyze_review_status(
        self,
        exam_results: List[ExamResult],
    ) -> Dict[str, Any]:
        total = 0
        auto_count = 0
        pending_count = 0
        reviewed_count = 0
        auto_score_sum = 0.0
        reviewed_score_sum = 0.0
        effective_score_sum = 0.0
        max_score_sum = 0.0

        for er in exam_results:
            for qr in er.question_results:
                total += 1
                max_score_sum += qr.max_score
                if qr.review_info:
                    status = qr.review_info.review_status
                    if status == "auto":
                        auto_count += 1
                        auto_score_sum += qr.review_info.auto_score
                        effective_score_sum += qr.score
                    elif status == "pending_review":
                        pending_count += 1
                        auto_score_sum += qr.review_info.auto_score
                        effective_score_sum += qr.score
                    elif status == "reviewed":
                        reviewed_count += 1
                        auto_score_sum += qr.review_info.auto_score
                        if qr.review_info.reviewed_score is not None:
                            reviewed_score_sum += qr.review_info.reviewed_score
                        effective_score_sum += qr.score
                else:
                    auto_count += 1
                    effective_score_sum += qr.score

        return {
            "total_questions": total,
            "auto_graded": auto_count,
            "pending_review": pending_count,
            "reviewed": reviewed_count,
            "auto_score_total": round(auto_score_sum, 2),
            "reviewed_score_total": round(reviewed_score_sum, 2),
            "effective_score_total": round(effective_score_sum, 2),
            "max_score_total": round(max_score_sum, 2),
            "auto_score_rate": round(auto_score_sum / max_score_sum * 100, 2) if max_score_sum > 0 else 0,
            "effective_score_rate": round(effective_score_sum / max_score_sum * 100, 2) if max_score_sum > 0 else 0,
            "review_adjustment": round(effective_score_sum - auto_score_sum, 2),
        }


@dataclass
class KnowledgePointTrend:
    knowledge_point: str
    previous_mastery: float = 0.0
    current_mastery: float = 0.0
    change: float = 0.0
    previous_count: int = 0
    current_count: int = 0
    trend: str = "stable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_point": self.knowledge_point,
            "previous_mastery": self.previous_mastery,
            "current_mastery": self.current_mastery,
            "change": self.change,
            "previous_count": self.previous_count,
            "current_count": self.current_count,
            "trend": self.trend,
        }


@dataclass
class PracticePlan:
    total_count: int = 10
    difficulty_weights: Dict[str, float] = field(default_factory=dict)
    type_ratio: Dict[str, float] = field(default_factory=dict)
    focus_knowledge_points: List[str] = field(default_factory=list)
    review_knowledge_points: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    expected_effect: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_count": self.total_count,
            "difficulty_weights": self.difficulty_weights,
            "type_ratio": self.type_ratio,
            "focus_knowledge_points": self.focus_knowledge_points,
            "review_knowledge_points": self.review_knowledge_points,
            "suggestions": self.suggestions,
            "expected_effect": self.expected_effect,
        }


@dataclass
class StudentReportRender:
    student_id: str
    student_name: str
    exam_title: str
    total_score: float
    max_score: float
    percentage: float
    grade_level: str
    rank: Optional[int] = None
    correct_count: int = 0
    wrong_count: int = 0
    pending_review_count: int = 0
    time_spent_seconds: Optional[int] = None
    knowledge_point_trends: List[KnowledgePointTrend] = field(default_factory=list)
    strong_points: List[str] = field(default_factory=list)
    weak_points: List[str] = field(default_factory=list)
    wrong_question_ids: List[str] = field(default_factory=list)
    review_adjustment: float = 0.0
    study_suggestions: List[str] = field(default_factory=list)
    next_practice_plan: Optional[PracticePlan] = None
    grade_tips: str = ""
    report_generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "exam_title": self.exam_title,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "grade_level": self.grade_level,
            "rank": self.rank,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "pending_review_count": self.pending_review_count,
            "time_spent_seconds": self.time_spent_seconds,
            "knowledge_point_trends": [k.to_dict() for k in self.knowledge_point_trends],
            "strong_points": self.strong_points,
            "weak_points": self.weak_points,
            "wrong_question_ids": self.wrong_question_ids,
            "review_adjustment": self.review_adjustment,
            "study_suggestions": self.study_suggestions,
            "next_practice_plan": self.next_practice_plan.to_dict() if self.next_practice_plan else None,
            "grade_tips": self.grade_tips,
            "report_generated_at": self.report_generated_at.isoformat(),
        }


@dataclass
class TeacherReportRender:
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
    class_weak_points: List[str] = field(default_factory=list)
    top_students: List[Dict[str, Any]] = field(default_factory=list)
    bottom_students: List[Dict[str, Any]] = field(default_factory=list)
    review_pending_count: int = 0
    review_adjustment_avg: float = 0.0
    teacher_actions: List[str] = field(default_factory=list)
    report_generated_at: datetime = field(default_factory=datetime.now)

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
            "top_students": self.top_students,
            "bottom_students": self.bottom_students,
            "review_pending_count": self.review_pending_count,
            "review_adjustment_avg": round(self.review_adjustment_avg, 2),
            "teacher_actions": self.teacher_actions,
            "report_generated_at": self.report_generated_at.isoformat(),
        }


class AdvancedAnalytics(Analytics):
    def compare_knowledge_points_trend(
        self,
        previous_results: List[ExamResult],
        current_results: List[ExamResult],
    ) -> List[KnowledgePointTrend]:
        prev_stats = self.analyze_knowledge_points(previous_results)
        curr_stats = self.analyze_knowledge_points(current_results)

        prev_map = {s.knowledge_point: s for s in prev_stats}
        curr_map = {s.knowledge_point: s for s in curr_stats}

        all_kps = set(list(prev_map.keys()) + list(curr_map.keys()))
        trends: List[KnowledgePointTrend] = []

        for kp in all_kps:
            prev = prev_map.get(kp)
            curr = curr_map.get(kp)
            prev_mastery = prev.mastery_level if prev else 0.0
            curr_mastery = curr.mastery_level if curr else 0.0
            prev_count = prev.total_questions if prev else 0
            curr_count = curr.total_questions if curr else 0
            change = round(curr_mastery - prev_mastery, 2)

            if change > 5:
                trend = "improving"
            elif change < -5:
                trend = "declining"
            else:
                trend = "stable"

            trends.append(KnowledgePointTrend(
                knowledge_point=kp,
                previous_mastery=prev_mastery,
                current_mastery=curr_mastery,
                change=change,
                previous_count=prev_count,
                current_count=curr_count,
                trend=trend,
            ))

        trends.sort(key=lambda t: t.change, reverse=True)
        return trends

    def generate_next_practice_plan(
        self,
        current_results: List[ExamResult],
        previous_results: Optional[List[ExamResult]] = None,
        total_count: int = 10,
    ) -> PracticePlan:
        kp_stats = self.analyze_knowledge_points(current_results)
        weak_kps = self.get_weak_knowledge_points(current_results)

        trends: List[KnowledgePointTrend] = []
        if previous_results:
            trends = self.compare_knowledge_points_trend(previous_results, current_results)

        declining_kps = [t.knowledge_point for t in trends if t.trend == "declining"]
        improving_kps = [t.knowledge_point for t in trends if t.trend == "improving"]

        weak_kp_names = [kp.knowledge_point for kp in weak_kps[:5]]
        strong_kp_names = [kp.knowledge_point for kp in kp_stats if kp.mastery_level >= 80][:3]

        avg_score = 0.0
        total_max = 0.0
        for er in current_results:
            avg_score += er.total_score
            total_max += er.max_score
        avg_percentage = (avg_score / total_max * 100) if total_max > 0 else 0.0

        if avg_percentage < 40:
            diff_weights = {"easy": 0.6, "medium": 0.3, "hard": 0.1}
            type_ratio = {"objective": 0.9, "subjective": 0.1}
            expected = "聚焦基础概念巩固，通过大量客观题快速建立信心"
        elif avg_percentage < 70:
            diff_weights = {"easy": 0.3, "medium": 0.5, "hard": 0.2}
            type_ratio = {"objective": 0.7, "subjective": 0.3}
            expected = "巩固基础的同时提升中等难度题目，逐步加入主观题训练"
        elif avg_percentage < 90:
            diff_weights = {"easy": 0.15, "medium": 0.55, "hard": 0.3}
            type_ratio = {"objective": 0.5, "subjective": 0.5}
            expected = "中等和较难题并重，强化知识迁移与综合应用能力"
        else:
            diff_weights = {"easy": 0.05, "medium": 0.35, "hard": 0.6}
            type_ratio = {"objective": 0.3, "subjective": 0.7}
            expected = "挑战高难度综合题，侧重深度理解与拓展应用"

        suggestions = []
        if weak_kp_names:
            suggestions.append(f"重点突破薄弱知识点：{', '.join(weak_kp_names[:3])}")
        if declining_kps:
            suggestions.append(f"特别关注退步知识点：{', '.join(declining_kps[:3])}")
        if strong_kp_names:
            suggestions.append(f"继续保持优势知识点：{', '.join(strong_kp_names)}")
        if improving_kps:
            suggestions.append(f"进步明显，继续保持：{', '.join(improving_kps[:3])}")
        if avg_percentage < 60:
            suggestions.append("建议每天至少练习 15 分钟，从基础题入手逐步提升")
        elif avg_percentage < 85:
            suggestions.append("建议每周 3-4 次练习，适量增加中等难度题目")
        else:
            suggestions.append("基础扎实，可以挑战更多综合应用题和拓展题")

        review_kps = declining_kps + [kp for kp in weak_kp_names if kp not in declining_kps]

        return PracticePlan(
            total_count=total_count,
            difficulty_weights=diff_weights,
            type_ratio=type_ratio,
            focus_knowledge_points=weak_kp_names,
            review_knowledge_points=review_kps,
            suggestions=suggestions,
            expected_effect=expected,
        )

    def build_student_report(
        self,
        exam_result: ExamResult,
        exam_title: str = "",
        student_name: str = "",
        previous_results: Optional[List[ExamResult]] = None,
        rank: Optional[int] = None,
    ) -> StudentReportRender:
        er = exam_result

        kp_stats = self.analyze_knowledge_points([er])
        weak_kps = self.get_weak_knowledge_points([er])
        wrong_q = self.collect_wrong_questions([er])

        strong_points = [kp.knowledge_point for kp in kp_stats if kp.mastery_level >= 80]
        weak_points = [kp.knowledge_point for kp in weak_kps[:5]]
        wrong_ids = list(wrong_q.keys())

        review_stats = self.analyze_review_status([er])

        trends = []
        if previous_results:
            trends = self.compare_knowledge_points_trend(previous_results, [er])

        suggestions = self.generate_study_suggestions(
            wrong_questions=wrong_q,
            weak_knowledge_points=weak_kps,
            total_score=er.total_score,
            max_score=er.max_score,
        )

        next_plan = self.generate_next_practice_plan([er], previous_results)

        grade_level = self._grade_level(er.percentage)
        grade_tips = self._grade_tips(er.percentage)

        return StudentReportRender(
            student_id=er.student_id,
            student_name=student_name or er.student_id,
            exam_title=exam_title,
            total_score=er.total_score,
            max_score=er.max_score,
            percentage=er.percentage,
            grade_level=grade_level,
            rank=rank,
            correct_count=er.correct_count,
            wrong_count=er.wrong_count,
            pending_review_count=review_stats["pending_review"],
            time_spent_seconds=er.time_spent_seconds,
            knowledge_point_trends=trends,
            strong_points=strong_points,
            weak_points=weak_points,
            wrong_question_ids=wrong_ids,
            review_adjustment=review_stats["review_adjustment"],
            study_suggestions=suggestions,
            next_practice_plan=next_plan,
            grade_tips=grade_tips,
        )

    def build_teacher_report(
        self,
        exam_results: List[ExamResult],
        class_id: Optional[str] = None,
        subject: Optional[str] = None,
        exam_title: str = "班级练习报告",
        pass_line: float = 60.0,
        excellent_line: float = 90.0,
        top_n: int = 5,
        bottom_n: int = 5,
    ) -> TeacherReportRender:
        n = len(exam_results)
        if n == 0:
            return TeacherReportRender(
                class_id=class_id, subject=subject, exam_title=exam_title,
                student_count=0, average_score=0, max_score=0, min_score=0,
                pass_rate=0, excellent_rate=0,
            )

        scores = [er.percentage for er in exam_results]
        avg_score = sum(scores) / n
        max_s = max(scores)
        min_s = min(scores)
        pass_r = sum(1 for s in scores if s >= pass_line) / n * 100
        excellent_r = sum(1 for s in scores if s >= excellent_line) / n * 100

        grade_dist = {"优秀": 0, "良好": 0, "中等": 0, "及格": 0, "不及格": 0}
        for s in scores:
            grade_dist[self._grade_level(s)] += 1

        all_kp_stats = {}
        total_review_pending = 0
        total_review_adj = 0.0

        for er in exam_results:
            kp_stats = self.analyze_knowledge_points([er])
            for ks in kp_stats:
                if ks.knowledge_point not in all_kp_stats:
                    all_kp_stats[ks.knowledge_point] = []
                all_kp_stats[ks.knowledge_point].append(ks.mastery_level)
            review_s = self.analyze_review_status([er])
            total_review_pending += review_s["pending_review"]
            total_review_adj += review_s["review_adjustment"]

        avg_mastery = []
        for kp, levels in all_kp_stats.items():
            avg_mastery.append((kp, sum(levels) / len(levels)))
        avg_mastery.sort(key=lambda x: x[1], reverse=True)

        class_strong = [kp for kp, m in avg_mastery[:3] if m >= 70]
        class_weak = [kp for kp, m in avg_mastery[-3:] if m < 70]

        sorted_results = sorted(exam_results, key=lambda er: er.percentage, reverse=True)
        top_students = []
        for i, er in enumerate(sorted_results[:top_n]):
            top_students.append({
                "rank": i + 1,
                "student_id": er.student_id,
                "score": er.total_score,
                "percentage": er.percentage,
                "grade_level": self._grade_level(er.percentage),
            })

        bottom_students = []
        for er in sorted_results[-bottom_n:]:
            bottom_students.append({
                "student_id": er.student_id,
                "score": er.total_score,
                "percentage": er.percentage,
                "grade_level": self._grade_level(er.percentage),
            })

        actions = []
        if class_weak:
            actions.append(f"班级薄弱知识点：{', '.join(class_weak)}，建议集中讲解和专项训练")
        if pass_r < 80:
            actions.append(f"及格率仅 {pass_r:.1f}%，建议对 {int(n * (1-pass_r/100))} 名未达标学生进行个别辅导")
        if total_review_pending > 0:
            actions.append(f"待人工复核题目 {total_review_pending} 道，请及时完成批改")
        if total_review_adj != 0:
            direction = "加分" if total_review_adj > 0 else "减分"
            actions.append(f"复核后累计调整 {abs(total_review_adj):.1f} 分（{direction}），需关注评分标准一致性")
        if class_strong:
            actions.append(f"班级优势知识点：{', '.join(class_strong)}，可安排拓展提升")

        return TeacherReportRender(
            class_id=class_id,
            subject=subject,
            exam_title=exam_title,
            student_count=n,
            average_score=avg_score,
            max_score=max_s,
            min_score=min_s,
            pass_rate=pass_r,
            excellent_rate=excellent_r,
            grade_distribution=grade_dist,
            class_strong_points=class_strong,
            class_weak_points=class_weak,
            top_students=top_students,
            bottom_students=bottom_students,
            review_pending_count=total_review_pending,
            review_adjustment_avg=total_review_adj / n if n > 0 else 0,
            teacher_actions=actions,
        )

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

    def _grade_tips(self, percentage: float) -> str:
        if percentage >= 95:
            return "太棒了！你已经掌握得非常扎实，继续保持并挑战更高难度！"
        elif percentage >= 85:
            return "表现优秀！继续巩固薄弱知识点，冲击满分吧！"
        elif percentage >= 75:
            return "成绩良好，再努力一把就能达到优秀！"
        elif percentage >= 60:
            return "及格了，但还有提升空间，重点复习错题和薄弱知识点。"
        else:
            return "别灰心，从基础开始，每天进步一点点，一定能赶上来！"
