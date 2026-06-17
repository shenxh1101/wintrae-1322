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
