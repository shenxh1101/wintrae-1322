import json
import uuid
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from .models import (
    ExamPaper,
    ExamResult,
    StudentAnswer,
    QuestionResult,
    PracticeSession,
    ReviewInfo,
    QuestionType,
)
from .grader import Grader


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, PracticeSession] = {}

    def create_session(
        self,
        student_id: str,
        exam_paper: ExamPaper,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PracticeSession:
        sid = session_id or f"session_{uuid.uuid4().hex[:12]}"
        kps: List[str] = []
        if exam_paper:
            for q in exam_paper.questions:
                for kp in q.knowledge_points:
                    if kp not in kps:
                        kps.append(kp)
        session = PracticeSession(
            id=sid,
            student_id=student_id,
            exam_paper=exam_paper,
            status="created",
            grade=exam_paper.grade if exam_paper else None,
            subject=exam_paper.subject if exam_paper else None,
            knowledge_points=kps,
            metadata=metadata or {},
        )
        self._sessions[sid] = session
        return session

    def start_answering(self, session_id: str) -> PracticeSession:
        session = self._get_session(session_id)
        if session.status != "created":
            raise ValueError(f"会话 {session_id} 当前状态为 {session.status}，无法开始作答")
        session.status = "answering"
        session.answering_started_at = datetime.now()
        return session

    def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any,
    ) -> PracticeSession:
        session = self._get_session(session_id)
        if session.status not in ("created", "answering"):
            raise ValueError(f"会话 {session_id} 当前状态为 {session.status}，无法提交答案")
        if session.status == "created":
            session.status = "answering"
            session.answering_started_at = datetime.now()
        session.answers[question_id] = answer
        session.answer_timestamps[question_id] = datetime.now().isoformat()
        return session

    def submit_answers(
        self,
        session_id: str,
        answers: Dict[str, Any],
    ) -> PracticeSession:
        for qid, ans in answers.items():
            self.submit_answer(session_id, qid, ans)
        return self._get_session(session_id)

    def grade_session(
        self,
        session_id: str,
        grader: Optional[Grader] = None,
    ) -> ExamResult:
        session = self._get_session(session_id)
        if session.status not in ("created", "answering"):
            raise ValueError(f"会话 {session_id} 当前状态为 {session.status}，无法批改")
        if not session.exam_paper:
            raise ValueError("会话没有关联试卷")

        g = grader or Grader()
        student_answers = []
        for qid, ans in session.answers.items():
            sa = StudentAnswer(question_id=qid, answer=ans)
            student_answers.append(sa)

        result = g.grade_exam(
            exam=session.exam_paper,
            student_answers=student_answers,
            student_id=session.student_id,
            started_at=session.answering_started_at,
            completed_at=datetime.now(),
        )

        session.exam_result = result
        session.status = "graded"
        session.graded_at = datetime.now()
        session.submitted_at = session.submitted_at or datetime.now()
        return result

    def review_question(
        self,
        session_id: str,
        question_id: str,
        reviewed_score: float,
        reviewer_id: str,
        review_comment: Optional[str] = None,
    ) -> QuestionResult:
        session = self._get_session(session_id)
        if session.status not in ("graded", "reviewed"):
            raise ValueError(f"会话 {session_id} 当前状态为 {session.status}，无法复核")
        if not session.exam_result:
            raise ValueError("会话尚未批改，无法复核")

        qr = None
        for r in session.exam_result.question_results:
            if r.question_id == question_id:
                qr = r
                break
        if qr is None:
            raise ValueError(f"未找到题目 {question_id} 的批改结果")

        if qr.review_info is None:
            qr.review_info = ReviewInfo(auto_score=qr.score, review_status="auto")

        qr.review_info.reviewed_score = reviewed_score
        qr.review_info.reviewer_id = reviewer_id
        qr.review_info.review_comment = review_comment
        qr.review_info.reviewed_at = datetime.now()
        qr.review_info.review_status = "reviewed"

        old_score = qr.score
        qr.score = reviewed_score
        if reviewed_score >= qr.max_score:
            qr.is_correct = True
        else:
            qr.is_correct = False

        self._recalculate_exam_result(session)
        session.status = "reviewed"
        return qr

    def close_session(self, session_id: str) -> PracticeSession:
        session = self._get_session(session_id)
        if session.status in ("created", "answering"):
            raise ValueError(f"会话 {session_id} 尚未批改，无法关闭")
        session.status = "closed"
        session.closed_at = datetime.now()
        return session

    def get_session(self, session_id: str) -> Optional[PracticeSession]:
        return self._sessions.get(session_id)

    def query_history(
        self,
        student_id: Optional[str] = None,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        knowledge_point: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[PracticeSession]:
        results = []
        for session in self._sessions.values():
            if student_id and session.student_id != student_id:
                continue
            if grade and session.grade != grade:
                continue
            if subject and session.subject != subject:
                continue
            if knowledge_point and knowledge_point not in session.knowledge_points:
                continue
            if status and session.status != status:
                continue
            if date_from and session.created_at < date_from:
                continue
            if date_to and session.created_at > date_to:
                continue
            results.append(session)
        results.sort(key=lambda s: s.created_at, reverse=True)
        return results

    def get_student_sessions(self, student_id: str) -> List[PracticeSession]:
        return self.query_history(student_id=student_id)

    def get_graded_sessions(self, student_id: Optional[str] = None) -> List[PracticeSession]:
        return self.query_history(student_id=student_id, status="graded") + \
               self.query_history(student_id=student_id, status="reviewed") + \
               self.query_history(student_id=student_id, status="closed")

    def save_to_json(self, filepath: str) -> None:
        data = []
        for session in self._sessions.values():
            s_data: Dict[str, Any] = {
                "id": session.id,
                "student_id": session.student_id,
                "status": session.status,
                "grade": session.grade,
                "subject": session.subject,
                "knowledge_points": session.knowledge_points,
                "answers": session.answers,
                "answer_timestamps": session.answer_timestamps,
                "created_at": session.created_at.isoformat(),
                "answering_started_at": session.answering_started_at.isoformat() if session.answering_started_at else None,
                "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
                "graded_at": session.graded_at.isoformat() if session.graded_at else None,
                "closed_at": session.closed_at.isoformat() if session.closed_at else None,
                "metadata": session.metadata,
            }
            if session.exam_paper:
                s_data["exam_id"] = session.exam_paper.id
                s_data["exam_title"] = session.exam_paper.title
                s_data["exam_total_score"] = session.exam_paper.total_score
                s_data["exam_question_count"] = len(session.exam_paper.questions)
            if session.exam_result:
                s_data["exam_result"] = session.exam_result.to_dict()
                if "exam_id" not in s_data:
                    s_data["exam_id"] = session.exam_result.exam_id
                s_data["total_score"] = session.exam_result.total_score
                s_data["max_score"] = session.exam_result.max_score
                s_data["percentage"] = session.exam_result.percentage
            data.append(s_data)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_json(
        self,
        filepath: str,
        exam_papers: Optional[Dict[str, ExamPaper]] = None,
    ) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s_data in data:
            exam_paper = None
            if exam_papers and s_data.get("exam_id"):
                exam_paper = exam_papers.get(s_data["exam_id"])

            exam_result = None
            if s_data.get("exam_result"):
                er_data = s_data["exam_result"]
                qrs = []
                for qr_d in er_data.get("question_results", []):
                    ri = None
                    if qr_d.get("review_info"):
                        ri_data = qr_d["review_info"]
                        ri = ReviewInfo(
                            auto_score=ri_data.get("auto_score", 0.0),
                            reviewed_score=ri_data.get("reviewed_score"),
                            review_status=ri_data.get("review_status", "auto"),
                            reviewer_id=ri_data.get("reviewer_id"),
                            review_comment=ri_data.get("review_comment"),
                            reviewed_at=datetime.fromisoformat(ri_data["reviewed_at"]) if ri_data.get("reviewed_at") else None,
                        )
                    qrs.append(QuestionResult(
                        question_id=qr_d["question_id"],
                        student_answer=qr_d["student_answer"],
                        correct_answer=qr_d["correct_answer"],
                        is_correct=qr_d["is_correct"],
                        score=qr_d["score"],
                        max_score=qr_d["max_score"],
                        partial_points=qr_d.get("partial_points"),
                        feedback=qr_d.get("feedback", ""),
                        matched_key_points=qr_d.get("matched_key_points"),
                        missed_key_points=qr_d.get("missed_key_points"),
                        knowledge_points=qr_d.get("knowledge_points", []),
                        question_type=QuestionType(qr_d["question_type"]) if qr_d.get("question_type") else None,
                        review_info=ri,
                    ))
                exam_result = ExamResult(
                    exam_id=er_data["exam_id"],
                    student_id=er_data["student_id"],
                    question_results=qrs,
                    total_score=er_data.get("total_score", 0),
                    max_score=er_data.get("max_score", 0),
                    percentage=er_data.get("percentage", 0),
                    started_at=datetime.fromisoformat(er_data["started_at"]) if er_data.get("started_at") else None,
                    completed_at=datetime.fromisoformat(er_data["completed_at"]) if er_data.get("completed_at") else None,
                    time_spent_seconds=er_data.get("time_spent_seconds"),
                    metadata=er_data.get("metadata", {}),
                    _exam_total_score=er_data.get("max_score", 0),
                )

            session = PracticeSession(
                id=s_data["id"],
                student_id=s_data["student_id"],
                exam_paper=exam_paper,
                answers=s_data.get("answers", {}),
                answer_timestamps=s_data.get("answer_timestamps", {}),
                exam_result=exam_result,
                status=s_data.get("status", "created"),
                grade=s_data.get("grade"),
                subject=s_data.get("subject"),
                knowledge_points=s_data.get("knowledge_points", []),
                created_at=datetime.fromisoformat(s_data["created_at"]) if s_data.get("created_at") else datetime.now(),
                answering_started_at=datetime.fromisoformat(s_data["answering_started_at"]) if s_data.get("answering_started_at") else None,
                submitted_at=datetime.fromisoformat(s_data["submitted_at"]) if s_data.get("submitted_at") else None,
                graded_at=datetime.fromisoformat(s_data["graded_at"]) if s_data.get("graded_at") else None,
                closed_at=datetime.fromisoformat(s_data["closed_at"]) if s_data.get("closed_at") else None,
                metadata=s_data.get("metadata", {}),
            )
            self._sessions[session.id] = session

    def _get_session(self, session_id: str) -> PracticeSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"未找到会话 {session_id}")
        return session

    def _recalculate_exam_result(self, session: PracticeSession) -> None:
        if not session.exam_result:
            return
        result = session.exam_result
        result.total_score = round(sum(qr.score for qr in result.question_results), 2)
        if result.max_score > 0:
            result.percentage = round((result.total_score / result.max_score) * 100, 2)
