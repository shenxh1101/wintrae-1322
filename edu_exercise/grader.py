import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from .models import (
    Question,
    QuestionType,
    ExamPaper,
    StudentAnswer,
    QuestionResult,
    ExamResult,
    ReviewInfo,
)


class Grader:
    def __init__(self, case_sensitive: bool = False, strip_whitespace: bool = True):
        self.case_sensitive = case_sensitive
        self.strip_whitespace = strip_whitespace

    def grade_exam(
        self,
        exam: ExamPaper,
        student_answers: List[StudentAnswer],
        student_id: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        time_spent_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExamResult:
        answer_map: Dict[str, Any] = {}
        answer_time_map: Dict[str, int] = {}
        for sa in student_answers:
            answer_map[sa.question_id] = sa.answer
            if sa.time_spent_seconds:
                answer_time_map[sa.question_id] = sa.time_spent_seconds

        question_results: List[QuestionResult] = []
        for q in exam.questions:
            sa = answer_map.get(q.id)
            ts = answer_time_map.get(q.id)
            qr = self.grade_question(q, sa, time_spent_seconds=ts)
            question_results.append(qr)

        return ExamResult(
            exam_id=exam.id,
            student_id=student_id,
            question_results=question_results,
            started_at=started_at,
            completed_at=completed_at or datetime.now(),
            time_spent_seconds=time_spent_seconds,
            metadata=metadata or {},
            _exam_total_score=exam.total_score,
        )

    def grade_question(
        self,
        question: Question,
        student_answer: Any,
        time_spent_seconds: Optional[int] = None,
    ) -> QuestionResult:
        q_type = question.question_type

        if q_type == QuestionType.SINGLE_CHOICE:
            return self._grade_single_choice(question, student_answer)
        elif q_type == QuestionType.MULTIPLE_CHOICE:
            return self._grade_multiple_choice(question, student_answer)
        elif q_type == QuestionType.FILL_BLANK:
            return self._grade_fill_blank(question, student_answer)
        elif q_type == QuestionType.TRUE_FALSE:
            return self._grade_true_false(question, student_answer)
        elif q_type == QuestionType.SHORT_ANSWER:
            return self._grade_short_answer(question, student_answer)
        else:
            return QuestionResult(
                question_id=question.id,
                student_answer=student_answer,
                correct_answer=question.answer,
                is_correct=False,
                score=0.0,
                max_score=question.score,
                feedback="未知题型",
                knowledge_points=question.knowledge_points,
                question_type=q_type,
            )

    def _normalize_answer(self, answer: Any) -> str:
        if answer is None:
            return ""
        s = str(answer)
        if self.strip_whitespace:
            s = s.strip()
        if not self.case_sensitive:
            s = s.lower()
        return s

    def _grade_single_choice(
        self, question: Question, student_answer: Any
    ) -> QuestionResult:
        correct = question.answer
        sa_norm = self._normalize_answer(student_answer)
        ca_norm = self._normalize_answer(correct)
        is_correct = sa_norm == ca_norm and sa_norm != ""
        score = question.score if is_correct else 0.0
        feedback = "回答正确！" if is_correct else self._build_incorrect_feedback(
            question, student_answer, correct
        )
        return QuestionResult(
            question_id=question.id,
            student_answer=student_answer,
            correct_answer=correct,
            is_correct=is_correct,
            score=score,
            max_score=question.score,
            feedback=feedback,
            knowledge_points=question.knowledge_points,
            question_type=QuestionType.SINGLE_CHOICE,
            review_info=ReviewInfo(auto_score=score, review_status="auto"),
        )

    def _grade_multiple_choice(
        self, question: Question, student_answer: Any
    ) -> QuestionResult:
        correct = question.answer
        if isinstance(correct, str):
            correct_list = sorted(re.findall(r"[A-Za-z]", self._normalize_answer(correct)))
        elif isinstance(correct, (list, tuple, set)):
            correct_list = sorted([self._normalize_answer(x) for x in correct])
        else:
            correct_list = [self._normalize_answer(correct)]

        if student_answer is None or student_answer == "":
            sa_list = []
        elif isinstance(student_answer, str):
            sa_list = sorted(re.findall(r"[A-Za-z]", self._normalize_answer(student_answer)))
        elif isinstance(student_answer, (list, tuple, set)):
            sa_list = sorted([self._normalize_answer(x) for x in student_answer])
        else:
            sa_list = []

        correct_set = set(correct_list)
        sa_set = set(sa_list)

        is_correct = correct_set == sa_set and len(sa_set) > 0

        if is_correct:
            score = question.score
            partial = None
            feedback = "回答正确！"
        else:
            if correct_set and sa_set:
                intersection = correct_set & sa_set
                union = correct_set | sa_set
                if len(union) > 0:
                    ratio = len(intersection) / len(correct_set)
                    if sa_set.issubset(correct_set) and ratio > 0:
                        partial = round(question.score * ratio * 0.8, 2)
                        score = partial
                        feedback = f"部分正确，漏选了 {sorted(correct_set - sa_set)}，获得部分分数。"
                    else:
                        score = 0.0
                        partial = None
                        feedback = self._build_incorrect_feedback(question, student_answer, correct)
                else:
                    score = 0.0
                    partial = None
                    feedback = self._build_incorrect_feedback(question, student_answer, correct)
            else:
                score = 0.0
                partial = None
                feedback = self._build_incorrect_feedback(question, student_answer, correct)

        return QuestionResult(
            question_id=question.id,
            student_answer=student_answer,
            correct_answer=correct,
            is_correct=is_correct,
            score=score,
            max_score=question.score,
            partial_points=partial,
            feedback=feedback,
            knowledge_points=question.knowledge_points,
            question_type=QuestionType.MULTIPLE_CHOICE,
            review_info=ReviewInfo(auto_score=score, review_status="auto"),
        )

    def _grade_fill_blank(
        self, question: Question, student_answer: Any
    ) -> QuestionResult:
        correct = question.answer
        blanks = question.blanks or 1

        if isinstance(correct, str):
            correct_list = [correct]
        else:
            correct_list = list(correct)

        if student_answer is None or student_answer == "":
            sa_list = [""] * blanks
        elif isinstance(student_answer, str):
            sa_list = [student_answer] if blanks == 1 else [student_answer] * blanks
        else:
            try:
                sa_list = list(student_answer)
            except TypeError:
                sa_list = [str(student_answer)]

        while len(sa_list) < blanks:
            sa_list.append("")

        while len(correct_list) < blanks:
            correct_list.append(correct_list[-1] if correct_list else "")

        correct_count = 0
        total_blanks = blanks
        for i in range(total_blanks):
            ca = correct_list[i]
            sa = sa_list[i] if i < len(sa_list) else ""
            if isinstance(ca, (list, tuple)):
                acceptable = [self._normalize_answer(a) for a in ca]
                if self._normalize_answer(sa) in acceptable:
                    correct_count += 1
            else:
                if self._normalize_answer(sa) == self._normalize_answer(ca):
                    correct_count += 1

        is_correct = correct_count == total_blanks and total_blanks > 0
        score_per_blank = question.score / total_blanks if total_blanks > 0 else question.score
        score = round(correct_count * score_per_blank, 2)
        partial = score if 0 < score < question.score else None

        if is_correct:
            feedback = "回答正确！"
        elif correct_count > 0:
            feedback = f"部分正确，答对 {correct_count}/{total_blanks} 个空。"
        else:
            feedback = self._build_incorrect_feedback(question, student_answer, correct)

        return QuestionResult(
            question_id=question.id,
            student_answer=student_answer,
            correct_answer=correct,
            is_correct=is_correct,
            score=score,
            max_score=question.score,
            partial_points=partial,
            feedback=feedback,
            knowledge_points=question.knowledge_points,
            question_type=QuestionType.FILL_BLANK,
            review_info=ReviewInfo(auto_score=score, review_status="auto"),
        )

    def _grade_true_false(
        self, question: Question, student_answer: Any
    ) -> QuestionResult:
        correct = question.answer
        sa_norm = self._normalize_answer(student_answer)
        ca_norm = self._normalize_answer(correct)

        true_vals = {"true", "t", "1", "对", "正确", "是"}
        false_vals = {"false", "f", "0", "错", "错误", "否"}

        ca_bool = None
        if ca_norm in true_vals:
            ca_bool = True
        elif ca_norm in false_vals:
            ca_bool = False
        elif isinstance(correct, bool):
            ca_bool = correct

        sa_bool = None
        answer_recognized = False
        if isinstance(student_answer, bool):
            sa_bool = student_answer
            answer_recognized = True
        elif sa_norm in true_vals:
            sa_bool = True
            answer_recognized = True
        elif sa_norm in false_vals:
            sa_bool = False
            answer_recognized = True
        elif sa_norm == "":
            answer_recognized = False
        else:
            answer_recognized = False

        if ca_bool is None:
            ca_bool = True

        if not answer_recognized and sa_norm != "":
            is_correct = False
            score = 0.0
            feedback = f"答案格式无法识别（'{student_answer}'），判断题请使用：对/错、正确/错误、T/F、是/否。"
        elif sa_bool is None:
            is_correct = False
            score = 0.0
            feedback = "未作答。" + self._build_incorrect_feedback(question, student_answer, correct)
        else:
            is_correct = sa_bool == ca_bool
            score = question.score if is_correct else 0.0
            if is_correct:
                feedback = "回答正确！"
            else:
                feedback = self._build_incorrect_feedback(question, student_answer, correct)

        return QuestionResult(
            question_id=question.id,
            student_answer=student_answer,
            correct_answer=correct,
            is_correct=is_correct,
            score=score,
            max_score=question.score,
            feedback=feedback,
            knowledge_points=question.knowledge_points,
            question_type=QuestionType.TRUE_FALSE,
            review_info=ReviewInfo(auto_score=score, review_status="auto"),
        )

    def _grade_short_answer(
        self, question: Question, student_answer: Any
    ) -> QuestionResult:
        correct = question.answer
        sa = "" if student_answer is None else str(student_answer).strip()
        gc = question.grading_criterion

        matched = []
        missed = []
        score = 0.0
        feedback_parts = []

        if not sa:
            feedback = "未作答。"
            if question.analysis:
                feedback += f" 参考解析：{question.analysis}"
            return QuestionResult(
                question_id=question.id,
                student_answer=student_answer,
                correct_answer=correct,
                is_correct=False,
                score=0.0,
                max_score=question.score,
                feedback=feedback,
                knowledge_points=question.knowledge_points,
                question_type=QuestionType.SHORT_ANSWER,
                review_info=ReviewInfo(
                    auto_score=0.0,
                    review_status="pending_review",
                ),
            )

        sa_norm = self._normalize_answer(sa)

        if gc:
            if gc.min_length is not None and len(sa) < gc.min_length:
                feedback_parts.append(f"答案长度不足（至少 {gc.min_length} 字）。")

            if gc.max_length is not None and len(sa) > gc.max_length:
                feedback_parts.append(f"答案长度超过限制（最多 {gc.max_length} 字）。")

            if gc.keywords:
                keyword_score = 0.0
                kw_weight = question.score / len(gc.keywords) if gc.keywords else 0
                for kw in gc.keywords:
                    kw_norm = self._normalize_answer(kw)
                    if kw_norm in sa_norm:
                        matched.append(kw)
                        keyword_score += kw_weight
                    else:
                        missed.append(kw)
                score += keyword_score

            if gc.key_points:
                kp_count = len(gc.key_points)
                kp_weight = question.score * (1 - (gc.partial_score_ratio or 0)) / kp_count if kp_count else 0
                kp_matched = 0
                for kp in gc.key_points:
                    kp_norm = self._normalize_answer(kp)
                    if kp_norm in sa_norm:
                        kp_matched += 1
                        if kp not in matched:
                            matched.append(kp)
                    else:
                        if kp not in missed:
                            missed.append(kp)
                score += kp_matched * kp_weight

        ca_str = self._normalize_answer(correct if isinstance(correct, str) else str(correct))
        if ca_str and sa_norm == ca_str:
            score = question.score

        score = min(round(score, 2), question.score)
        is_correct = score >= question.score

        if is_correct:
            feedback = "回答正确！"
        elif score > 0:
            feedback_parts.insert(0, f"自动评分建议 {score}/{question.score} 分（待教师复核）。")
            if matched:
                feedback_parts.append(f"命中要点：{', '.join(matched)}。")
            if missed:
                feedback_parts.append(f"遗漏要点：{', '.join(missed)}。")
            feedback = " ".join(feedback_parts)
        else:
            feedback = self._build_incorrect_feedback(question, student_answer, correct)
            feedback += "（自动评分 0 分，待教师复核）"
            if matched:
                feedback += f" 注意到相关关键词：{', '.join(matched)}。"

        if question.analysis and not is_correct:
            feedback += f" 参考解析：{question.analysis}"

        review_info = ReviewInfo(
            auto_score=score,
            review_status="pending_review",
        )

        return QuestionResult(
            question_id=question.id,
            student_answer=student_answer,
            correct_answer=correct,
            is_correct=is_correct,
            score=score,
            max_score=question.score,
            partial_points=score if 0 < score < question.score else None,
            feedback=feedback,
            matched_key_points=matched if matched else None,
            missed_key_points=missed if missed else None,
            knowledge_points=question.knowledge_points,
            question_type=QuestionType.SHORT_ANSWER,
            review_info=review_info,
        )

    def _build_incorrect_feedback(
        self, question: Question, student_answer: Any, correct_answer: Any
    ) -> str:
        parts = []
        if student_answer is None or student_answer == "":
            parts.append("未作答。")
        else:
            parts.append("回答错误。")
        parts.append(f"正确答案：{correct_answer}。")
        if question.analysis:
            parts.append(f"解析：{question.analysis}")
        return " ".join(parts)

    def get_summary(self, result: ExamResult) -> Dict[str, Any]:
        by_type: Dict[str, Dict[str, float]] = {}
        for qr in result.question_results:
            t = qr.question_type.display_name if qr.question_type else "未知"
            if t not in by_type:
                by_type[t] = {"score": 0, "max_score": 0, "correct": 0, "total": 0}
            by_type[t]["score"] += qr.score
            by_type[t]["max_score"] += qr.max_score
            by_type[t]["total"] += 1
            if qr.is_correct:
                by_type[t]["correct"] += 1

        for t in by_type:
            d = by_type[t]
            d["accuracy"] = round(d["correct"] / d["total"] * 100, 2) if d["total"] > 0 else 0
            d["score_rate"] = round(d["score"] / d["max_score"] * 100, 2) if d["max_score"] > 0 else 0

        level = "优秀"
        if result.percentage < 60:
            level = "不及格"
        elif result.percentage < 70:
            level = "及格"
        elif result.percentage < 80:
            level = "良好"
        elif result.percentage < 90:
            level = "较好"

        return {
            "total_score": result.total_score,
            "max_score": result.max_score,
            "percentage": result.percentage,
            "level": level,
            "correct_count": result.correct_count,
            "wrong_count": result.wrong_count,
            "total_count": len(result.question_results),
            "accuracy": round(result.correct_count / len(result.question_results) * 100, 2)
            if result.question_results else 0,
            "by_type": by_type,
        }
