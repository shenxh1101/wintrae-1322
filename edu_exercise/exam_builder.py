import uuid
import random
from typing import List, Dict, Optional, Tuple, Any
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
        seed: Optional[int] = None,
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
            seed=seed,
        )
        return self.build(config)


@dataclass
class AdaptiveRationale:
    knowledge_point_allocations: Dict[str, Dict] = field(default_factory=dict)
    difficulty_distribution: Dict[str, int] = field(default_factory=dict)
    difficulty_strategy: str = ""
    difficulty_reason: str = ""
    type_distribution: Dict[str, int] = field(default_factory=dict)
    type_strategy: str = ""
    type_reason: str = ""
    overall_mastery: float = 0.0
    summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "knowledge_point_allocations": self.knowledge_point_allocations,
            "difficulty_distribution": self.difficulty_distribution,
            "difficulty_strategy": self.difficulty_strategy,
            "difficulty_reason": self.difficulty_reason,
            "type_distribution": self.type_distribution,
            "type_strategy": self.type_strategy,
            "type_reason": self.type_reason,
            "overall_mastery": self.overall_mastery,
            "summary": self.summary,
        }


class AdaptiveBuilder:
    OBJECTIVE_TYPES = {
        QuestionType.SINGLE_CHOICE,
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.TRUE_FALSE,
        QuestionType.FILL_BLANK,
    }
    SUBJECTIVE_TYPES = {QuestionType.SHORT_ANSWER}

    def __init__(self, question_bank: QuestionBank):
        self._bank = question_bank

    def _compute_overall_mastery(
        self,
        wrong_kps: Dict[str, int],
        weak_kp_mastery: Dict[str, float],
    ) -> float:
        if not weak_kp_mastery and not wrong_kps:
            return 60.0
        total_weight = 0.0
        weighted_sum = 0.0
        all_kps = set(list(wrong_kps.keys()) + list(weak_kp_mastery.keys()))
        for kp in all_kps:
            w = 1.0
            if kp in wrong_kps:
                w += wrong_kps[kp] * 0.5
            mastery = weak_kp_mastery.get(kp)
            if mastery is None:
                mastery = max(30.0, 80.0 - wrong_kps.get(kp, 0) * 10)
            weighted_sum += mastery * w
            total_weight += w
        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 60.0

    def _get_type_strategy(self, overall_mastery: float) -> Dict[str, Any]:
        if overall_mastery < 40:
            objective_ratio = 0.9
            label = "基础薄弱阶段，以客观题为主，快速巩固基础概念"
            reason = f"整体掌握度 {overall_mastery:.0f}% < 40%，客观题占比 90%，便于集中强化基础知识点"
        elif overall_mastery < 70:
            objective_ratio = 0.7
            label = "稳步提升阶段，客观题为主，适度加入主观题训练表达"
            reason = f"整体掌握度 {overall_mastery:.0f}%（40%-70%），客观题占比 70%，搭配主观题练习解题思路"
        elif overall_mastery < 90:
            objective_ratio = 0.5
            label = "进阶巩固阶段，客观题与主观题并重，训练综合应用"
            reason = f"整体掌握度 {overall_mastery:.0f}%（70%-90%），客观题与主观题各占 50%，强化知识迁移与表达"
        else:
            objective_ratio = 0.3
            label = "优秀拓展阶段，以主观题为主，挑战综合应用与深度理解"
            reason = f"整体掌握度 {overall_mastery:.0f}% ≥ 90%，主观题占比 70%，侧重综合分析与深度解答"
        return {
            "objective_ratio": objective_ratio,
            "subjective_ratio": 1 - objective_ratio,
            "label": label,
            "reason": reason,
        }

    def _get_difficulty_strategy(self, overall_mastery: float) -> Dict[str, Any]:
        if overall_mastery < 40:
            weights = {"easy": 0.6, "medium": 0.3, "hard": 0.1}
            label = "侧重基础巩固，以简单题为主，搭配少量中等题建立信心"
            reason = f"掌握度 {overall_mastery:.0f}% 较低，简单题占比 60%，从基础入手逐步提升"
        elif overall_mastery < 70:
            weights = {"easy": 0.3, "medium": 0.5, "hard": 0.2}
            label = "基础与提升并重，中等难度为主，逐步提升挑战"
            reason = f"掌握度 {overall_mastery:.0f}% 中等，中等题占比 50%，在巩固基础的同时适度提升"
        elif overall_mastery < 90:
            weights = {"easy": 0.15, "medium": 0.55, "hard": 0.3}
            label = "进阶挑战，中等和较难题为主，训练综合应用"
            reason = f"掌握度 {overall_mastery:.0f}% 良好，较难题占比 30%，强化综合运用能力"
        else:
            weights = {"easy": 0.05, "medium": 0.35, "hard": 0.6}
            label = "高难度挑战，以难题为主，冲击满分能力"
            reason = f"掌握度 {overall_mastery:.0f}% 优秀，难题占比 60%，侧重深度理解与综合拓展"
        return {
            "weights": weights,
            "label": label,
            "reason": reason,
        }

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

        overall_mastery = self._compute_overall_mastery(wrong_kps, weak_kp_mastery)
        rationale.overall_mastery = overall_mastery

        type_strategy = self._get_type_strategy(overall_mastery)
        rationale.type_strategy = type_strategy["label"]
        rationale.type_reason = type_strategy["reason"]

        diff_strategy = self._get_difficulty_strategy(overall_mastery)
        rationale.difficulty_strategy = diff_strategy["label"]
        rationale.difficulty_reason = diff_strategy["reason"]

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

        diff_weights = diff_strategy["weights"]
        obj_ratio = type_strategy["objective_ratio"]

        selected: List[Question] = []
        used_ids: set = set()
        diff_actual: Dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        type_actual: Dict[str, int] = {}

        for kp, cnt in kp_counts.items():
            if cnt <= 0:
                continue

            kp_mastery = weak_kp_mastery.get(kp, overall_mastery)
            kp_diff_weights = self._kp_difficulty_adjust(diff_weights, kp_mastery, kp in wrong_kps)

            kp_obj_count = max(1, round(cnt * obj_ratio)) if cnt >= 2 else cnt
            kp_subj_count = cnt - kp_obj_count

            kp_selected: List[Question] = []

            obj_needed_by_diff = self._allocate_by_difficulty(kp_obj_count, kp_diff_weights)
            for diff_lvl, diff_cnt in obj_needed_by_diff.items():
                if diff_cnt <= 0:
                    continue
                candidates = self._bank.filter(
                    knowledge_points=[kp],
                    grades=[grade] if grade else None,
                    subjects=[subject] if subject else None,
                    difficulties=[diff_lvl] if diff_lvl != "medium" else None,
                    question_types=[qt for qt in QuestionType if qt in self.OBJECTIVE_TYPES],
                    exclude_ids=used_ids | set(q.id for q in kp_selected),
                )
                if not candidates and diff_lvl == "hard":
                    candidates = self._bank.filter(
                        knowledge_points=[kp],
                        grades=[grade] if grade else None,
                        subjects=[subject] if subject else None,
                        question_types=[qt for qt in QuestionType if qt in self.OBJECTIVE_TYPES],
                        exclude_ids=used_ids | set(q.id for q in kp_selected),
                    )
                if candidates:
                    actual = min(diff_cnt, len(candidates))
                    sampled = random.sample(candidates, actual)
                    kp_selected.extend(sampled)

            if kp_subj_count > 0:
                subj_needed_by_diff = self._allocate_by_difficulty(kp_subj_count, kp_diff_weights)
                for diff_lvl, diff_cnt in subj_needed_by_diff.items():
                    if diff_cnt <= 0:
                        continue
                    candidates = self._bank.filter(
                        knowledge_points=[kp],
                        grades=[grade] if grade else None,
                        subjects=[subject] if subject else None,
                        difficulties=[diff_lvl] if diff_lvl != "medium" else None,
                        question_types=[qt for qt in QuestionType if qt in self.SUBJECTIVE_TYPES],
                        exclude_ids=used_ids | set(q.id for q in kp_selected),
                    )
                    if not candidates and diff_lvl == "hard":
                        candidates = self._bank.filter(
                            knowledge_points=[kp],
                            grades=[grade] if grade else None,
                            subjects=[subject] if subject else None,
                            question_types=[qt for qt in QuestionType if qt in self.SUBJECTIVE_TYPES],
                            exclude_ids=used_ids | set(q.id for q in kp_selected),
                        )
                    if candidates:
                        actual = min(diff_cnt, len(candidates))
                        sampled = random.sample(candidates, actual)
                        kp_selected.extend(sampled)

            if not kp_selected and cnt > 0:
                fallback = self._bank.filter(
                    knowledge_points=[kp],
                    grades=[grade] if grade else None,
                    subjects=[subject] if subject else None,
                    exclude_ids=used_ids,
                )
                if fallback:
                    actual = min(cnt, len(fallback))
                    kp_selected = random.sample(fallback, actual)

            for q in kp_selected:
                diff_actual[q.difficulty.value] = diff_actual.get(q.difficulty.value, 0) + 1
                tname = q.question_type.display_name
                type_actual[tname] = type_actual.get(tname, 0) + 1

            selected.extend(kp_selected)
            used_ids.update(q.id for q in kp_selected)

            reason_parts = []
            if kp in wrong_kps:
                reason_parts.append(f"错题出现{wrong_kps[kp]}次")
            if kp in weak_kp_mastery:
                reason_parts.append(f"掌握度{weak_kp_mastery[kp]:.0f}%")
            if kp_selected:
                obj_n = sum(1 for q in kp_selected if q.question_type in self.OBJECTIVE_TYPES)
                subj_n = len(kp_selected) - obj_n
                reason_parts.append(f"客{obj_n}/主{subj_n}")
                diff_str = "/".join([f"{k}{diff_actual.get(k,0)}" for k in ["easy", "medium", "hard"] if diff_actual.get(k, 0) > 0 and any(q.difficulty.value == k for q in kp_selected)])
                if diff_str:
                    reason_parts.append(f"难度{diff_str}")
            kp_alloc[kp] = {
                "requested": cnt,
                "actual": len(kp_selected),
                "reason": "；".join(reason_parts) if reason_parts else "一般覆盖",
                "mastery": weak_kp_mastery.get(kp, overall_mastery),
                "objective_count": sum(1 for q in kp_selected if q.question_type in self.OBJECTIVE_TYPES),
                "subjective_count": sum(1 for q in kp_selected if q.question_type in self.SUBJECTIVE_TYPES),
                "easy_count": sum(1 for q in kp_selected if q.difficulty == Difficulty.EASY),
                "medium_count": sum(1 for q in kp_selected if q.difficulty == Difficulty.MEDIUM),
                "hard_count": sum(1 for q in kp_selected if q.difficulty == Difficulty.HARD),
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
                for q in extra_sampled:
                    diff_actual[q.difficulty.value] = diff_actual.get(q.difficulty.value, 0) + 1
                    tname = q.question_type.display_name
                    type_actual[tname] = type_actual.get(tname, 0) + 1

        if not selected:
            raise ValueError("自适应组卷未能从题库中选取任何题目")

        rationale.knowledge_point_allocations = kp_alloc
        rationale.difficulty_distribution = diff_actual
        rationale.type_distribution = type_actual

        kp_desc = "、".join([f"{kp}({info['actual']}题)" for kp, info in kp_alloc.items() if info.get("actual", 0) > 0])
        rationale.summary = (
            f"本次练习共{len(selected)}题，针对{len(all_kps)}个知识点组卷。"
            f"整体掌握度评估{overall_mastery:.0f}%，{diff_strategy['label']}；{type_strategy['label']}。"
            f"涵盖知识点：{kp_desc}"
        )

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

    def _kp_difficulty_adjust(
        self,
        base_weights: Dict[str, float],
        kp_mastery: float,
        has_wrong: bool,
    ) -> Dict[str, float]:
        w = dict(base_weights)
        if has_wrong:
            w["easy"] += 0.2
            w["hard"] -= 0.1
        mastery_delta = kp_mastery - 60
        if mastery_delta < -20:
            w["easy"] += 0.15
            w["hard"] -= 0.1
        elif mastery_delta > 20:
            w["hard"] += 0.15
            w["easy"] -= 0.1
        total = sum(max(v, 0) for v in w.values())
        if total <= 0:
            return {"easy": 0.3, "medium": 0.5, "hard": 0.2}
        return {k: max(v, 0) / total for k, v in w.items()}

    def _allocate_by_difficulty(
        self,
        total: int,
        weights: Dict[str, float],
    ) -> Dict[str, int]:
        result: Dict[str, int] = {}
        remaining = total
        levels = ["easy", "medium", "hard"]
        float_alloc: Dict[str, float] = {}
        for lv in levels:
            float_alloc[lv] = total * weights.get(lv, 0)
        int_alloc: Dict[str, int] = {}
        for lv in levels:
            int_alloc[lv] = int(float_alloc[lv])
            remaining -= int_alloc[lv]
        residuals = sorted(levels, key=lambda lv: float_alloc[lv] - int_alloc[lv], reverse=True)
        for i in range(remaining):
            int_alloc[residuals[i % len(residuals)]] += 1
        for lv in levels:
            result[lv] = max(0, int_alloc.get(lv, 0))
        return result
