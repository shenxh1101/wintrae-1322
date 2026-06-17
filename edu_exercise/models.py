from enum import Enum
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"

    @classmethod
    def from_str(cls, s: str) -> "QuestionType":
        mapping = {
            "单选": cls.SINGLE_CHOICE,
            "single": cls.SINGLE_CHOICE,
            "单选选择题": cls.SINGLE_CHOICE,
            "多选": cls.MULTIPLE_CHOICE,
            "multiple": cls.MULTIPLE_CHOICE,
            "多项选择题": cls.MULTIPLE_CHOICE,
            "填空": cls.FILL_BLANK,
            "fill": cls.FILL_BLANK,
            "填空题": cls.FILL_BLANK,
            "判断": cls.TRUE_FALSE,
            "true_false": cls.TRUE_FALSE,
            "判断题": cls.TRUE_FALSE,
            "简答": cls.SHORT_ANSWER,
            "short": cls.SHORT_ANSWER,
            "简答题": cls.SHORT_ANSWER,
        }
        s_lower = s.lower().strip()
        if s_lower in mapping:
            return mapping[s_lower]
        for k, v in mapping.items():
            if s_lower in k.lower() or k.lower() in s_lower:
                return v
        return cls(s_lower)

    @property
    def display_name(self) -> str:
        names = {
            QuestionType.SINGLE_CHOICE: "单选题",
            QuestionType.MULTIPLE_CHOICE: "多选题",
            QuestionType.FILL_BLANK: "填空题",
            QuestionType.TRUE_FALSE: "判断题",
            QuestionType.SHORT_ANSWER: "简答题",
        }
        return names.get(self, self.value)


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @classmethod
    def from_str(cls, s: str) -> "Difficulty":
        mapping = {
            "简单": cls.EASY,
            "易": cls.EASY,
            "基础": cls.EASY,
            "中等": cls.MEDIUM,
            "中": cls.MEDIUM,
            "普通": cls.MEDIUM,
            "困难": cls.HARD,
            "难": cls.HARD,
            "挑战": cls.HARD,
        }
        s_lower = s.lower().strip()
        if s_lower in mapping:
            return mapping[s_lower]
        for k, v in mapping.items():
            if s_lower in k.lower() or k.lower() in s_lower:
                return v
        return cls(s_lower)

    @property
    def display_name(self) -> str:
        names = {
            Difficulty.EASY: "简单",
            Difficulty.MEDIUM: "中等",
            Difficulty.HARD: "困难",
        }
        return names.get(self, self.value)

    @property
    def weight(self) -> float:
        weights = {
            Difficulty.EASY: 1.0,
            Difficulty.MEDIUM: 1.5,
            Difficulty.HARD: 2.0,
        }
        return weights.get(self, 1.0)


@dataclass
class GradingCriterion:
    keywords: Optional[List[str]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    key_points: Optional[List[str]] = None
    partial_score_ratio: float = 0.0
    custom_validator: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.keywords:
            d["keywords"] = self.keywords
        if self.min_length is not None:
            d["min_length"] = self.min_length
        if self.max_length is not None:
            d["max_length"] = self.max_length
        if self.key_points:
            d["key_points"] = self.key_points
        if self.partial_score_ratio > 0:
            d["partial_score_ratio"] = self.partial_score_ratio
        if self.custom_validator:
            d["custom_validator"] = self.custom_validator
        return d


@dataclass
class Question:
    id: str
    question_type: QuestionType
    content: str
    answer: Any
    analysis: str = ""
    knowledge_points: List[str] = field(default_factory=list)
    grade: Optional[str] = None
    subject: Optional[str] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    score: float = 5.0
    options: Optional[List[Dict[str, str]]] = None
    blanks: Optional[int] = None
    grading_criterion: Optional[GradingCriterion] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_render_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question_type": self.question_type.value,
            "question_type_name": self.question_type.display_name,
            "content": self.content,
            "analysis": self.analysis,
            "knowledge_points": self.knowledge_points,
            "grade": self.grade,
            "subject": self.subject,
            "difficulty": self.difficulty.value,
            "difficulty_name": self.difficulty.display_name,
            "score": self.score,
            "options": self.options,
            "blanks": self.blanks,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def to_answer_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "answer": self.answer,
            "analysis": self.analysis,
            "grading_criterion": self.grading_criterion.to_dict() if self.grading_criterion else None,
        }


@dataclass
class SingleChoiceQuestion(Question):
    question_type: QuestionType = field(default=QuestionType.SINGLE_CHOICE, init=False)

    def __post_init__(self):
        if self.options is None:
            raise ValueError("单选题必须提供选项")


@dataclass
class MultipleChoiceQuestion(Question):
    question_type: QuestionType = field(default=QuestionType.MULTIPLE_CHOICE, init=False)

    def __post_init__(self):
        if self.options is None:
            raise ValueError("多选题必须提供选项")


@dataclass
class FillBlankQuestion(Question):
    question_type: QuestionType = field(default=QuestionType.FILL_BLANK, init=False)

    def __post_init__(self):
        if self.blanks is None:
            self.blanks = self.content.count("___") if "___" in self.content else 1


@dataclass
class TrueFalseQuestion(Question):
    question_type: QuestionType = field(default=QuestionType.TRUE_FALSE, init=False)

    def __post_init__(self):
        pass


@dataclass
class ShortAnswerQuestion(Question):
    question_type: QuestionType = field(default=QuestionType.SHORT_ANSWER, init=False)

    def __post_init__(self):
        if self.grading_criterion is None:
            self.grading_criterion = GradingCriterion()


@dataclass
class ExamPaper:
    id: str
    title: str
    questions: List[Question]
    total_score: float = 0.0
    grade: Optional[str] = None
    subject: Optional[str] = None
    duration_minutes: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.total_score == 0:
            self.total_score = sum(q.score for q in self.questions)

    def get_questions_by_type(self, q_type: QuestionType) -> List[Question]:
        return [q for q in self.questions if q.question_type == q_type]

    def get_question_count_by_type(self) -> Dict[QuestionType, int]:
        result: Dict[QuestionType, int] = {}
        for q in self.questions:
            result[q.question_type] = result.get(q.question_type, 0) + 1
        return result

    def to_render_dict(self) -> Dict[str, Any]:
        sections = {}
        for q_type in QuestionType:
            qs = self.get_questions_by_type(q_type)
            if qs:
                sections[q_type.display_name] = {
                    "type": q_type.value,
                    "questions": [q.to_render_dict() for q in qs],
                    "count": len(qs),
                    "section_score": sum(q.score for q in qs),
                }
        return {
            "id": self.id,
            "title": self.title,
            "total_score": self.total_score,
            "grade": self.grade,
            "subject": self.subject,
            "duration_minutes": self.duration_minutes,
            "question_count": len(self.questions),
            "sections": sections,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_answer_key_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "total_score": self.total_score,
            "answers": {q.id: q.to_answer_dict() for q in self.questions},
        }


@dataclass
class StudentAnswer:
    question_id: str
    answer: Any
    answered_at: datetime = field(default_factory=datetime.now)
    time_spent_seconds: Optional[int] = None


@dataclass
class ReviewInfo:
    auto_score: float = 0.0
    reviewed_score: Optional[float] = None
    review_status: str = "auto"
    reviewer_id: Optional[str] = None
    review_comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    @property
    def effective_score(self) -> float:
        if self.review_status == "reviewed" and self.reviewed_score is not None:
            return self.reviewed_score
        return self.auto_score

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "auto_score": self.auto_score,
            "review_status": self.review_status,
        }
        if self.reviewed_score is not None:
            d["reviewed_score"] = self.reviewed_score
        if self.reviewer_id is not None:
            d["reviewer_id"] = self.reviewer_id
        if self.review_comment is not None:
            d["review_comment"] = self.review_comment
        if self.reviewed_at is not None:
            d["reviewed_at"] = self.reviewed_at.isoformat()
        return d


@dataclass
class QuestionResult:
    question_id: str
    student_answer: Any
    correct_answer: Any
    is_correct: bool
    score: float
    max_score: float
    partial_points: Optional[float] = None
    feedback: str = ""
    matched_key_points: Optional[List[str]] = None
    missed_key_points: Optional[List[str]] = None
    knowledge_points: List[str] = field(default_factory=list)
    question_type: Optional[QuestionType] = None
    review_info: Optional[ReviewInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "question_id": self.question_id,
            "student_answer": self.student_answer,
            "correct_answer": self.correct_answer,
            "is_correct": self.is_correct,
            "score": self.score,
            "max_score": self.max_score,
            "partial_points": self.partial_points,
            "feedback": self.feedback,
            "matched_key_points": self.matched_key_points,
            "missed_key_points": self.missed_key_points,
            "knowledge_points": self.knowledge_points,
            "question_type": self.question_type.value if self.question_type else None,
        }
        if self.review_info is not None:
            d["review_info"] = self.review_info.to_dict()
        return d


@dataclass
class ExamResult:
    exam_id: str
    student_id: str
    question_results: List[QuestionResult]
    total_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_spent_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _exam_total_score: float = field(default=0.0, repr=False)

    def __post_init__(self):
        questions_max = sum(r.max_score for r in self.question_results)
        if self.max_score == 0:
            self.max_score = self._exam_total_score if self._exam_total_score > 0 else questions_max
        if self.total_score == 0:
            self.total_score = sum(r.score for r in self.question_results)
        if self.percentage == 0 and self.max_score > 0:
            self.percentage = round((self.total_score / self.max_score) * 100, 2)

    @property
    def correct_count(self) -> int:
        return sum(1 for r in self.question_results if r.is_correct)

    @property
    def wrong_count(self) -> int:
        return len(self.question_results) - self.correct_count

    @property
    def wrong_questions(self) -> List[QuestionResult]:
        return [r for r in self.question_results if not r.is_correct]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "question_results": [r.to_dict() for r in self.question_results],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "time_spent_seconds": self.time_spent_seconds,
            "metadata": self.metadata,
        }


@dataclass
class WrongQuestion:
    question_id: str
    question: Optional[Question] = None
    wrong_count: int = 1
    last_wrong_at: datetime = field(default_factory=datetime.now)
    first_wrong_at: datetime = field(default_factory=datetime.now)
    wrong_answers: List[Any] = field(default_factory=list)
    knowledge_points: List[str] = field(default_factory=list)
    student_id: Optional[str] = None
    is_mastered: bool = False
    mastery_level: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question.to_render_dict() if self.question else None,
            "wrong_count": self.wrong_count,
            "last_wrong_at": self.last_wrong_at.isoformat(),
            "first_wrong_at": self.first_wrong_at.isoformat(),
            "wrong_answers": self.wrong_answers,
            "knowledge_points": self.knowledge_points,
            "student_id": self.student_id,
            "is_mastered": self.is_mastered,
            "mastery_level": self.mastery_level,
            "tags": self.tags,
        }


@dataclass
class PracticeRecord:
    id: str
    student_id: str
    exam_id: Optional[str] = None
    question_results: List[QuestionResult] = field(default_factory=list)
    total_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0
    practice_date: datetime = field(default_factory=datetime.now)
    duration_minutes: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.question_results and self.max_score == 0:
            self.max_score = sum(r.max_score for r in self.question_results)
        if self.question_results and self.total_score == 0:
            self.total_score = sum(r.score for r in self.question_results)
        if self.percentage == 0 and self.max_score > 0:
            self.percentage = round((self.total_score / self.max_score) * 100, 2)

    @property
    def correct_count(self) -> int:
        return sum(1 for r in self.question_results if r.is_correct)

    @property
    def wrong_count(self) -> int:
        return len(self.question_results) - self.correct_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "exam_id": self.exam_id,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "practice_date": self.practice_date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "tags": self.tags,
        }


@dataclass
class PracticeSession:
    id: str
    student_id: str
    exam_paper: Optional[ExamPaper] = None
    answers: Dict[str, Any] = field(default_factory=dict)
    answer_timestamps: Dict[str, str] = field(default_factory=dict)
    exam_result: Optional[ExamResult] = None
    status: str = "created"
    grade: Optional[str] = None
    subject: Optional[str] = None
    knowledge_points: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    answering_started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "student_id": self.student_id,
            "status": self.status,
            "grade": self.grade,
            "subject": self.subject,
            "knowledge_points": self.knowledge_points,
            "answers": self.answers,
            "answer_timestamps": self.answer_timestamps,
            "created_at": self.created_at.isoformat(),
            "answering_started_at": self.answering_started_at.isoformat() if self.answering_started_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
        if self.exam_paper:
            d["exam_paper_id"] = self.exam_paper.id
            d["exam_title"] = self.exam_paper.title
            d["total_score"] = self.exam_paper.total_score
            d["question_count"] = len(self.exam_paper.questions)
        if self.exam_result:
            d["result"] = self.exam_result.to_dict()
        return d
