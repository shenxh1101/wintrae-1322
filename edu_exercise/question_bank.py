import json
import os
import random
from typing import List, Dict, Optional, Set, Union, Callable, Any
from .models import (
    Question,
    QuestionType,
    Difficulty,
    SingleChoiceQuestion,
    MultipleChoiceQuestion,
    FillBlankQuestion,
    TrueFalseQuestion,
    ShortAnswerQuestion,
    GradingCriterion,
)


class QuestionBank:
    def __init__(self, questions: Optional[List[Question]] = None):
        self._questions: Dict[str, Question] = {}
        if questions:
            for q in questions:
                self.add_question(q)

    @property
    def questions(self) -> List[Question]:
        return list(self._questions.values())

    @property
    def count(self) -> int:
        return len(self._questions)

    def add_question(self, question: Question) -> None:
        if question.id in self._questions:
            raise ValueError(f"题目ID {question.id} 已存在")
        self._questions[question.id] = question

    def add_questions(self, questions: List[Question]) -> None:
        for q in questions:
            self.add_question(q)

    def remove_question(self, question_id: str) -> bool:
        if question_id in self._questions:
            del self._questions[question_id]
            return True
        return False

    def get_question(self, question_id: str) -> Optional[Question]:
        return self._questions.get(question_id)

    def filter(
        self,
        grades: Optional[List[str]] = None,
        knowledge_points: Optional[List[str]] = None,
        knowledge_mode: str = "any",
        question_types: Optional[List[QuestionType]] = None,
        difficulties: Optional[List[Difficulty]] = None,
        subjects: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        tag_mode: str = "any",
        exclude_ids: Optional[Set[str]] = None,
        custom_filter: Optional[Callable[[Question], bool]] = None,
    ) -> List[Question]:
        result = []
        for q in self._questions.values():
            if exclude_ids and q.id in exclude_ids:
                continue
            if grades and q.grade not in grades:
                continue
            if subjects and q.subject not in subjects:
                continue
            if question_types and q.question_type not in question_types:
                continue
            if difficulties and q.difficulty not in difficulties:
                continue
            if knowledge_points:
                if knowledge_mode == "all":
                    if not all(kp in q.knowledge_points for kp in knowledge_points):
                        continue
                else:
                    if not any(kp in q.knowledge_points for kp in knowledge_points):
                        continue
            if tags:
                if tag_mode == "all":
                    if not all(t in q.tags for t in tags):
                        continue
                else:
                    if not any(t in q.tags for t in tags):
                        continue
            if custom_filter and not custom_filter(q):
                continue
            result.append(q)
        return result

    def filter_by_score_range(
        self, min_score: float = 0, max_score: float = float("inf")
    ) -> List[Question]:
        return [q for q in self._questions.values() if min_score <= q.score <= max_score]

    def get_all_grades(self) -> Set[str]:
        return {q.grade for q in self._questions.values() if q.grade}

    def get_all_subjects(self) -> Set[str]:
        return {q.subject for q in self._questions.values() if q.subject}

    def get_all_knowledge_points(self) -> Set[str]:
        kps = set()
        for q in self._questions.values():
            kps.update(q.knowledge_points)
        return kps

    def get_all_tags(self) -> Set[str]:
        tags = set()
        for q in self._questions.values():
            tags.update(q.tags)
        return tags

    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total": self.count,
            "by_type": {},
            "by_difficulty": {},
            "by_grade": {},
            "by_subject": {},
        }
        for q in self._questions.values():
            t = q.question_type.display_name
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            d = q.difficulty.display_name
            stats["by_difficulty"][d] = stats["by_difficulty"].get(d, 0) + 1
            if q.grade:
                stats["by_grade"][q.grade] = stats["by_grade"].get(q.grade, 0) + 1
            if q.subject:
                stats["by_subject"][q.subject] = stats["by_subject"].get(q.subject, 0) + 1
        return stats

    def sample(
        self,
        count: int,
        grades: Optional[List[str]] = None,
        knowledge_points: Optional[List[str]] = None,
        question_types: Optional[List[QuestionType]] = None,
        difficulties: Optional[List[Difficulty]] = None,
        subjects: Optional[List[str]] = None,
        exclude_ids: Optional[Set[str]] = None,
        seed: Optional[int] = None,
    ) -> List[Question]:
        candidates = self.filter(
            grades=grades,
            knowledge_points=knowledge_points,
            question_types=question_types,
            difficulties=difficulties,
            subjects=subjects,
            exclude_ids=exclude_ids,
        )
        if seed is not None:
            random.seed(seed)
        sample_count = min(count, len(candidates))
        return random.sample(candidates, sample_count) if sample_count > 0 else []

    def load_from_json(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        questions_data = data.get("questions", data)
        for qd in questions_data:
            q = self._dict_to_question(qd)
            self.add_question(q)

    def save_to_json(self, filepath: str) -> None:
        data = [self._question_to_dict(q) for q in self._questions.values()]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"questions": data}, f, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> "QuestionBank":
        bank = cls()
        bank.load_from_json(filepath)
        return bank

    def load_from_list(self, data: List[Dict]) -> None:
        for qd in data:
            q = self._dict_to_question(qd)
            self.add_question(q)

    @classmethod
    def from_list(cls, data: List[Dict]) -> "QuestionBank":
        bank = cls()
        bank.load_from_list(data)
        return bank

    @staticmethod
    def _dict_to_question(data: Dict) -> Question:
        q_type = data.get("question_type", "")
        if isinstance(q_type, str):
            try:
                q_type_enum = QuestionType.from_str(q_type)
            except ValueError:
                q_type_enum = QuestionType(q_type)
        else:
            q_type_enum = q_type

        difficulty = data.get("difficulty", "medium")
        if isinstance(difficulty, str):
            try:
                diff_enum = Difficulty.from_str(difficulty)
            except ValueError:
                diff_enum = Difficulty(difficulty)
        else:
            diff_enum = difficulty

        gc_data = data.get("grading_criterion")
        grading_criterion = GradingCriterion(**gc_data) if gc_data else None

        common_kwargs = {
            "id": data["id"],
            "question_type": q_type_enum,
            "content": data["content"],
            "answer": data["answer"],
            "analysis": data.get("analysis", ""),
            "knowledge_points": data.get("knowledge_points", []),
            "grade": data.get("grade"),
            "subject": data.get("subject"),
            "difficulty": diff_enum,
            "score": data.get("score", 5.0),
            "options": data.get("options"),
            "blanks": data.get("blanks"),
            "grading_criterion": grading_criterion,
            "tags": data.get("tags", []),
            "metadata": data.get("metadata", {}),
        }

        type_map = {
            QuestionType.SINGLE_CHOICE: SingleChoiceQuestion,
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceQuestion,
            QuestionType.FILL_BLANK: FillBlankQuestion,
            QuestionType.TRUE_FALSE: TrueFalseQuestion,
            QuestionType.SHORT_ANSWER: ShortAnswerQuestion,
        }
        cls_ = type_map.get(q_type_enum, Question)
        if cls_ is not Question:
            kwargs = {k: v for k, v in common_kwargs.items() if k != "question_type"}
        else:
            kwargs = common_kwargs
        return cls_(**kwargs)

    @staticmethod
    def _question_to_dict(q: Question) -> Dict:
        d = {
            "id": q.id,
            "question_type": q.question_type.value,
            "content": q.content,
            "answer": q.answer,
            "analysis": q.analysis,
            "knowledge_points": q.knowledge_points,
            "grade": q.grade,
            "subject": q.subject,
            "difficulty": q.difficulty.value,
            "score": q.score,
            "tags": q.tags,
            "metadata": q.metadata,
        }
        if q.options:
            d["options"] = q.options
        if q.blanks:
            d["blanks"] = q.blanks
        if q.grading_criterion:
            d["grading_criterion"] = q.grading_criterion.to_dict()
        return d

    def merge(self, other: "QuestionBank", overwrite: bool = False) -> None:
        for qid, q in other._questions.items():
            if qid in self._questions and not overwrite:
                continue
            self._questions[qid] = q

    def __len__(self) -> int:
        return self.count

    def __iter__(self):
        return iter(self._questions.values())

    def __contains__(self, question_id: str) -> bool:
        return question_id in self._questions
