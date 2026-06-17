import uuid
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from .models import (
    Question,
    QuestionType,
    Difficulty,
    ExamPaper,
)
from .question_bank import QuestionBank


@dataclass
class TypeConfig:
    question_type: QuestionType
    count: int
    score_per_question: Optional[float] = None


@dataclass
class DifficultyConfig:
    difficulty: Difficulty
    ratio: float


@dataclass
class ExamConfig:
    title: str = "练习卷"
    total_questions: Optional[int] = None
    grades: Optional[List[str]] = None
    knowledge_points: Optional[List[str]] = None
    knowledge_mode: str = "any"
    subjects: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    type_configs: Optional[List[TypeConfig]] = None
    difficulty_configs: Optional[List[DifficultyConfig]] = None
    duration_minutes: Optional[int] = None
    total_score: Optional[float] = None
    exclude_question_ids: Optional[List[str]] = None
    shuffle: bool = True
    seed: Optional[int] = None
    metadata: Dict = field(default_factory=dict)

    def validate(self) -> Tuple[bool, str]:
        if self.total_questions is None and not self.type_configs:
            return False, "必须指定 total_questions 或 type_configs"
        if self.type_configs:
            for tc in self.type_configs:
                if tc.count <= 0:
                    return False, f"题型 {tc.question_type.display_name} 的数量必须大于0"
        if self.difficulty_configs:
            total_ratio = sum(dc.ratio for dc in self.difficulty_configs)
            if abs(total_ratio - 1.0) > 0.01:
                return False, f"难度比例之和必须为1.0，当前为 {total_ratio}"
        return True, ""


class ExamBuilder:
    def __init__(self, question_bank: QuestionBank):
        self._bank = question_bank

    def build(self, config: ExamConfig) -> ExamPaper:
        valid, msg = config.validate()
        if not valid:
            raise ValueError(f"试卷配置无效: {msg}")

        if config.seed is not None:
            random.seed(config.seed)

        exclude_ids = set(config.exclude_question_ids or [])

        if config.type_configs:
            questions = self._build_by_type_configs(config, exclude_ids)
        else:
            questions = self._build_by_total_count(config, exclude_ids)

        if not questions:
            raise ValueError("未能从题库中筛选出符合条件的题目")

        if config.shuffle:
            random.shuffle(questions)

        if config.type_configs:
            for idx, tc in enumerate(config.type_configs):
                if tc.score_per_question is not None:
                    type_questions = [q for q in questions if q.question_type == tc.question_type]
                    for q in type_questions:
                        q.score = tc.score_per_question

        total_score = config.total_score
        if total_score is None:
            total_score = sum(q.score for q in questions)
        elif config.type_configs is None and total_score > 0:
            auto_score = total_score / len(questions)
            for q in questions:
                q.score = round(auto_score, 2)
            total_score = sum(q.score for q in questions)

        exam_id = config.metadata.get("exam_id") or f"exam_{uuid.uuid4().hex[:12]}"

        return ExamPaper(
            id=exam_id,
            title=config.title,
            questions=questions,
            total_score=total_score,
            grade=config.grades[0] if config.grades and len(config.grades) == 1 else None,
            subject=config.subjects[0] if config.subjects and len(config.subjects) == 1 else None,
            duration_minutes=config.duration_minutes,
            metadata=config.metadata,
        )

    def _build_by_type_configs(
        self, config: ExamConfig, exclude_ids: set
    ) -> List[Question]:
        selected: List[Question] = []
        used_ids = set(exclude_ids)

        for tc in config.type_configs:
            base_filter = self._bank.filter(
                grades=config.grades,
                knowledge_points=config.knowledge_points,
                knowledge_mode=config.knowledge_mode,
                question_types=[tc.question_type],
                subjects=config.subjects,
                tags=config.tags,
                exclude_ids=used_ids,
            )

            type_questions = self._apply_difficulty_filter(
                base_filter, tc.count, config.difficulty_configs
            )

            actual_count = min(tc.count, len(type_questions))
            sampled = random.sample(type_questions, actual_count)
            selected.extend(sampled)
            used_ids.update(q.id for q in sampled)

        return selected

    def _build_by_total_count(
        self, config: ExamConfig, exclude_ids: set
    ) -> List[Question]:
        base_filter = self._bank.filter(
            grades=config.grades,
            knowledge_points=config.knowledge_points,
            knowledge_mode=config.knowledge_mode,
            subjects=config.subjects,
            tags=config.tags,
            exclude_ids=exclude_ids,
        )

        filtered = self._apply_difficulty_filter(
            base_filter, config.total_questions or 0, config.difficulty_configs
        )

        actual_count = min(config.total_questions or 0, len(filtered))
        return random.sample(filtered, actual_count) if actual_count > 0 else []

    def _apply_difficulty_filter(
        self,
        candidates: List[Question],
        total_count: int,
        difficulty_configs: Optional[List[DifficultyConfig]],
    ) -> List[Question]:
        if not difficulty_configs or total_count <= 0:
            return candidates

        result: List[Question] = []
        used_ids = set()

        for dc in difficulty_configs:
            target_count = max(1, round(total_count * dc.ratio))
            dc_candidates = [
                q for q in candidates
                if q.difficulty == dc.difficulty and q.id not in used_ids
            ]
            actual = min(target_count, len(dc_candidates))
            if actual > 0:
                sampled = random.sample(dc_candidates, actual)
                result.extend(sampled)
                used_ids.update(q.id for q in sampled)

        if len(result) < total_count:
            remaining = [q for q in candidates if q.id not in used_ids]
            need = total_count - len(result)
            if remaining:
                actual = min(need, len(remaining))
                sampled = random.sample(remaining, actual)
                result.extend(sampled)

        return result

    def build_from_question_ids(
        self,
        question_ids: List[str],
        title: str = "练习卷",
        total_score: Optional[float] = None,
        duration_minutes: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> ExamPaper:
        questions = []
        for qid in question_ids:
            q = self._bank.get_question(qid)
            if q:
                questions.append(q)
        if not questions:
            raise ValueError("未找到指定ID的题目")

        if total_score is None:
            total_score = sum(q.score for q in questions)

        exam_id = (metadata or {}).get("exam_id") or f"exam_{uuid.uuid4().hex[:12]}"

        return ExamPaper(
            id=exam_id,
            title=title,
            questions=questions,
            total_score=total_score,
            duration_minutes=duration_minutes,
            metadata=metadata or {},
        )

    def build_wrong_practice(
        self,
        wrong_question_ids: List[str],
        title: str = "错题练习",
        max_count: Optional[int] = None,
        shuffle: bool = True,
        metadata: Optional[Dict] = None,
    ) -> ExamPaper:
        questions = []
        for qid in wrong_question_ids:
            q = self._bank.get_question(qid)
            if q:
                questions.append(q)

        if not questions:
            raise ValueError("错题ID列表中没有找到有效题目")

        if max_count and len(questions) > max_count:
            if shuffle:
                random.shuffle(questions)
            questions = questions[:max_count]
        elif shuffle:
            random.shuffle(questions)

        total_score = sum(q.score for q in questions)
        exam_id = (metadata or {}).get("exam_id") or f"wrong_exam_{uuid.uuid4().hex[:12]}"

        return ExamPaper(
            id=exam_id,
            title=title,
            questions=questions,
            total_score=total_score,
            metadata=metadata or {},
        )

    def quick_build(
        self,
        count: int,
        grade: Optional[str] = None,
        knowledge_points: Optional[List[str]] = None,
        question_type: Optional[QuestionType] = None,
        difficulty: Optional[Difficulty] = None,
        subject: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ExamPaper:
        type_configs = None
        if question_type:
            type_configs = [TypeConfig(question_type=question_type, count=count)]

        diff_configs = None
        if difficulty:
            diff_configs = [DifficultyConfig(difficulty=difficulty, ratio=1.0)]

        config = ExamConfig(
            title=title or f"{grade or ''}{subject or ''}练习卷",
            total_questions=None if type_configs else count,
            grades=[grade] if grade else None,
            knowledge_points=knowledge_points,
            subjects=[subject] if subject else None,
            type_configs=type_configs,
            difficulty_configs=diff_configs,
        )
        return self.build(config)


@dataclass
class AdaptiveRationale:
    knowledge_point_allocations: Dict[str, Dict] = field(default_factory=dict)
    difficulty_strategy: str = ""
    type_distribution: Dict[str, int] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "knowledge_point_allocations": self.knowledge_point_allocations,
            "difficulty_strategy": self.difficulty_strategy,
            "type_distribution": self.type_distribution,
            "summary": self.summary,
        }


class AdaptiveBuilder:
    def __init__(self, question_bank: QuestionBank):
        self._bank = question_bank

    def build_adaptive(
        self,
        wrong_book: Dict[str, "WrongQuestion"],
        weak_knowledge_points: List["KnowledgePointStats"],
        total_count: int = 10,
        student_id: Optional[str] = None,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        title: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Tuple[ExamPaper, AdaptiveRationale]:
        if seed is not None:
            random.seed(seed)

        rationale = AdaptiveRationale()
        kp_alloc: Dict[str, Dict] = {}

        wrong_kps: Dict[str, int] = {}
        for wq in wrong_book.values():
            for kp in wq.knowledge_points:
                wrong_kps[kp] = wrong_kps.get(kp, 0) + wq.wrong_count

        weak_kp_names: List[str] = []
        weak_kp_mastery: Dict[str, float] = {}
        for wkp in weak_knowledge_points:
            weak_kp_names.append(wkp.knowledge_point)
            weak_kp_mastery[wkp.knowledge_point] = wkp.mastery_level

        all_kps = list(set(list(wrong_kps.keys()) + weak_kp_names))
        if not all_kps:
            all_kps = list(self._bank.get_all_knowledge_points())
        if not all_kps:
            raise ValueError("题库中没有可用的知识点")

        kp_weights: Dict[str, float] = {}
        for kp in all_kps:
            w = 1.0
            if kp in wrong_kps:
                w += wrong_kps[kp] * 2.0
            if kp in weak_kp_mastery:
                w += (100.0 - weak_kp_mastery[kp]) / 20.0
            kp_weights[kp] = w

        total_weight = sum(kp_weights.values())
        kp_counts: Dict[str, int] = {}
        remaining = total_count
        sorted_kps = sorted(kp_weights.keys(), key=lambda k: kp_weights[k], reverse=True)

        for i, kp in enumerate(sorted_kps):
            if i == len(sorted_kps) - 1:
                kp_counts[kp] = remaining
            else:
                alloc = max(1, round(total_count * kp_weights[kp] / total_weight))
                alloc = min(alloc, remaining - (len(sorted_kps) - i - 1))
                alloc = max(alloc, 1)
                kp_counts[kp] = alloc
                remaining -= alloc
            if remaining <= 0:
                break

        for kp in sorted_kps:
            if kp not in kp_counts:
                kp_counts[kp] = 0

        selected: List[Question] = []
        used_ids: set = set()
        for kp, cnt in kp_counts.items():
            if cnt <= 0:
                continue
            candidates = self._bank.filter(
                knowledge_points=[kp],
                grades=[grade] if grade else None,
                subjects=[subject] if subject else None,
                exclude_ids=used_ids,
            )
            if not candidates:
                kp_alloc[kp] = {"requested": cnt, "actual": 0, "reason": "题库无匹配题目"}
                continue

            actual = min(cnt, len(candidates))
            sampled = random.sample(candidates, actual)
            selected.extend(sampled)
            used_ids.update(q.id for q in sampled)
            reason_parts = []
            if kp in wrong_kps:
                reason_parts.append(f"错题出现{wrong_kps[kp]}次")
            if kp in weak_kp_mastery:
                reason_parts.append(f"掌握度{weak_kp_mastery[kp]:.0f}%")
            kp_alloc[kp] = {
                "requested": cnt,
                "actual": actual,
                "reason": "；".join(reason_parts) if reason_parts else "一般覆盖",
            }

        if len(selected) < total_count:
            extra_needed = total_count - len(selected)
            extras = self._bank.filter(
                grades=[grade] if grade else None,
                subjects=[subject] if subject else None,
                exclude_ids=used_ids,
            )
            if extras:
                actual = min(extra_needed, len(extras))
                extra_sampled = random.sample(extras, actual)
                selected.extend(extra_sampled)

        if not selected:
            raise ValueError("自适应组卷未能从题库中选取任何题目")

        type_dist: Dict[str, int] = {}
        for q in selected:
            t = q.question_type.display_name
            type_dist[t] = type_dist.get(t, 0) + 1

        weak_count = len([kp for kp in all_kps if kp in weak_kp_names or kp in wrong_kps])
        if weak_count > total_count * 0.6:
            diff_strategy = "侧重基础巩固，以简单和中等难度为主"
        elif weak_count > total_count * 0.3:
            diff_strategy = "基础与提升并重，中等难度为主"
        else:
            diff_strategy = "适度提升挑战，中等和较难为主"

        rationale.knowledge_point_allocations = kp_alloc
        rationale.difficulty_strategy = diff_strategy
        rationale.type_distribution = type_dist

        kp_desc = "、".join([f"{kp}({info['actual']}题)" for kp, info in kp_alloc.items() if info.get("actual", 0) > 0])
        rationale.summary = f"本次练习共{len(selected)}题，针对{len(all_kps)}个知识点组卷。{diff_strategy}。涵盖知识点：{kp_desc}"

        total_score = sum(q.score for q in selected)
        exam_id = f"adaptive_{uuid.uuid4().hex[:12]}"

        paper = ExamPaper(
            id=exam_id,
            title=title or "自适应练习卷",
            questions=selected,
            total_score=total_score,
            grade=grade,
            subject=subject,
            metadata={"adaptive_rationale": rationale.to_dict()},
        )

        return paper, rationale
