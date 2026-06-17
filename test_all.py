"""
教育练习题生成与批改类库 - 单元测试
验证核心模块：models, question_bank, exam_builder, grader, analytics, exporter
"""

import os
import sys
import unittest
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edu_exercise import (
    Question,
    SingleChoiceQuestion,
    MultipleChoiceQuestion,
    FillBlankQuestion,
    TrueFalseQuestion,
    ShortAnswerQuestion,
    ExamPaper,
    StudentAnswer,
    QuestionResult,
    ExamResult,
    WrongQuestion,
    PracticeRecord,
    GradingCriterion,
    QuestionType,
    Difficulty,
    QuestionBank,
    ExamBuilder,
    ExamConfig,
    TypeConfig,
    DifficultyConfig,
    AdaptiveBuilder,
    AdaptiveRationale,
    Grader,
    Analytics,
    KnowledgePointStats,
    Exporter,
    ReviewInfo,
    PracticeSession,
    SessionManager,
)


def create_test_bank():
    data = [
        {
            "id": "t_sc_1",
            "question_type": "single_choice",
            "content": "1+1=?",
            "answer": "B",
            "analysis": "1+1=2，故选B",
            "knowledge_points": ["加法", "基础运算"],
            "grade": "一年级",
            "subject": "数学",
            "difficulty": "easy",
            "score": 3,
            "options": [
                {"key": "A", "value": "1"},
                {"key": "B", "value": "2"},
                {"key": "C", "value": "3"},
                {"key": "D", "value": "4"},
            ],
        },
        {
            "id": "t_sc_2",
            "question_type": "single_choice",
            "content": "2+3=?",
            "answer": "C",
            "analysis": "2+3=5",
            "knowledge_points": ["加法", "基础运算"],
            "grade": "一年级",
            "subject": "数学",
            "difficulty": "easy",
            "score": 3,
            "options": [
                {"key": "A", "value": "3"},
                {"key": "B", "value": "4"},
                {"key": "C", "value": "5"},
                {"key": "D", "value": "6"},
            ],
        },
        {
            "id": "t_mc_1",
            "question_type": "multiple_choice",
            "content": "下列哪些是偶数？",
            "answer": ["A", "C", "D"],
            "analysis": "能被2整除的数是偶数，2,4,6都是偶数",
            "knowledge_points": ["偶数", "整除"],
            "grade": "二年级",
            "subject": "数学",
            "difficulty": "medium",
            "score": 5,
            "options": [
                {"key": "A", "value": "2"},
                {"key": "B", "value": "3"},
                {"key": "C", "value": "4"},
                {"key": "D", "value": "6"},
                {"key": "E", "value": "7"},
            ],
        },
        {
            "id": "t_fb_1",
            "question_type": "fill_blank",
            "content": "长方形的周长=___，面积=___。",
            "answer": ["(长+宽)×2", "长×宽"],
            "analysis": "周长公式是(长+宽)×2，面积公式是长×宽",
            "knowledge_points": ["长方形周长", "长方形面积", "公式"],
            "grade": "三年级",
            "subject": "数学",
            "difficulty": "medium",
            "score": 4,
            "blanks": 2,
        },
        {
            "id": "t_tf_1",
            "question_type": "true_false",
            "content": "正方形是特殊的长方形。",
            "answer": True,
            "analysis": "正方形的四条边都相等，是特殊的长方形",
            "knowledge_points": ["正方形", "长方形", "几何图形"],
            "grade": "三年级",
            "subject": "数学",
            "difficulty": "easy",
            "score": 2,
        },
        {
            "id": "t_tf_2",
            "question_type": "true_false",
            "content": "0除以任何数都等于0。",
            "answer": False,
            "analysis": "0不能作为除数，所以应该是0除以任何非零数都等于0",
            "knowledge_points": ["除法", "0的运算"],
            "grade": "三年级",
            "subject": "数学",
            "difficulty": "medium",
            "score": 2,
        },
        {
            "id": "t_sa_1",
            "question_type": "short_answer",
            "content": "小明有5个苹果，给了小红2个，又买了3个，请问现在小明有几个苹果？请写出过程。",
            "answer": "6个",
            "analysis": "5-2+3=6个",
            "knowledge_points": ["加减法应用题", "解决问题"],
            "grade": "二年级",
            "subject": "数学",
            "difficulty": "easy",
            "score": 8,
            "grading_criterion": {
                "keywords": ["5", "2", "3", "6"],
                "key_points": ["理解题意", "列算式", "计算正确", "答句完整"],
                "min_length": 10,
            },
        },
    ]
    return QuestionBank.from_list(data)


class TestModels(unittest.TestCase):
    def test_question_type_display(self):
        self.assertEqual(QuestionType.SINGLE_CHOICE.display_name, "单选题")
        self.assertEqual(QuestionType.MULTIPLE_CHOICE.display_name, "多选题")
        self.assertEqual(QuestionType.FILL_BLANK.display_name, "填空题")
        self.assertEqual(QuestionType.TRUE_FALSE.display_name, "判断题")
        self.assertEqual(QuestionType.SHORT_ANSWER.display_name, "简答题")

    def test_question_type_from_str(self):
        self.assertEqual(QuestionType.from_str("单选"), QuestionType.SINGLE_CHOICE)
        self.assertEqual(QuestionType.from_str("多选题"), QuestionType.MULTIPLE_CHOICE)
        self.assertEqual(QuestionType.from_str("填空"), QuestionType.FILL_BLANK)
        self.assertEqual(QuestionType.from_str("判断"), QuestionType.TRUE_FALSE)
        self.assertEqual(QuestionType.from_str("简答"), QuestionType.SHORT_ANSWER)

    def test_difficulty_weight(self):
        self.assertEqual(Difficulty.EASY.weight, 1.0)
        self.assertEqual(Difficulty.MEDIUM.weight, 1.5)
        self.assertEqual(Difficulty.HARD.weight, 2.0)

    def test_grading_criterion_to_dict(self):
        gc = GradingCriterion(
            keywords=["a", "b"],
            key_points=["要点1"],
            min_length=10,
            partial_score_ratio=0.5,
        )
        d = gc.to_dict()
        self.assertEqual(d["keywords"], ["a", "b"])
        self.assertEqual(d["min_length"], 10)
        self.assertEqual(d["partial_score_ratio"], 0.5)

    def test_question_to_render_dict(self):
        q = SingleChoiceQuestion(
            id="test1",
            content="test",
            answer="A",
            options=[{"key": "A", "value": "1"}],
            knowledge_points=["kp1"],
            score=5,
        )
        d = q.to_render_dict()
        self.assertEqual(d["id"], "test1")
        self.assertEqual(d["question_type"], "single_choice")
        self.assertEqual(d["score"], 5)

    def test_exam_paper_auto_score(self):
        bank = create_test_bank()
        qs = [bank.get_question("t_sc_1"), bank.get_question("t_sc_2")]
        exam = ExamPaper(id="e1", title="test", questions=qs)
        self.assertEqual(exam.total_score, 6)

    def test_exam_result_calculated_fields(self):
        qrs = [
            QuestionResult("q1", "A", "A", True, 5, 5),
            QuestionResult("q2", "B", "A", False, 0, 5),
        ]
        er = ExamResult("e1", "s1", qrs)
        self.assertEqual(er.correct_count, 1)
        self.assertEqual(er.wrong_count, 1)
        self.assertEqual(er.percentage, 50.0)


class TestQuestionBank(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()

    def test_bank_count(self):
        self.assertEqual(self.bank.count, 7)

    def test_add_question(self):
        q = SingleChoiceQuestion(
            id="new",
            content="new q",
            answer="A",
            options=[{"key": "A", "value": "x"}],
        )
        self.bank.add_question(q)
        self.assertEqual(self.bank.count, 8)
        with self.assertRaises(ValueError):
            self.bank.add_question(q)

    def test_filter_by_grade(self):
        result = self.bank.filter(grades=["一年级"])
        self.assertEqual(len(result), 2)
        for q in result:
            self.assertEqual(q.grade, "一年级")

    def test_filter_by_subject(self):
        result = self.bank.filter(subjects=["数学"])
        self.assertEqual(len(result), 7)

    def test_filter_by_type(self):
        result = self.bank.filter(question_types=[QuestionType.SINGLE_CHOICE])
        self.assertEqual(len(result), 2)

    def test_filter_by_difficulty(self):
        result = self.bank.filter(difficulties=[Difficulty.HARD])
        self.assertEqual(len(result), 0)
        result = self.bank.filter(difficulties=[Difficulty.EASY])
        self.assertGreaterEqual(len(result), 4)

    def test_filter_by_knowledge_points_any(self):
        result = self.bank.filter(knowledge_points=["加法"])
        self.assertEqual(len(result), 2)

    def test_filter_exclude_ids(self):
        result = self.bank.filter(exclude_ids={"t_sc_1", "t_sc_2"})
        self.assertEqual(len(result), 5)

    def test_filter_custom(self):
        result = self.bank.filter(custom_filter=lambda q: q.score >= 5)
        self.assertGreaterEqual(len(result), 2)

    def test_sample(self):
        sampled = self.bank.sample(3, seed=42)
        self.assertEqual(len(sampled), 3)
        ids = [q.id for q in sampled]
        self.assertEqual(len(set(ids)), 3)

    def test_get_all_knowledge_points(self):
        kps = self.bank.get_all_knowledge_points()
        self.assertIn("加法", kps)
        self.assertIn("偶数", kps)

    def test_get_statistics(self):
        stats = self.bank.get_statistics()
        self.assertEqual(stats["total"], 7)
        self.assertIn("单选题", stats["by_type"])

    def test_json_save_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
        try:
            self.bank.save_to_json(tmp_path)
            new_bank = QuestionBank.from_json(tmp_path)
            self.assertEqual(new_bank.count, self.bank.count)
            self.assertIsNotNone(new_bank.get_question("t_sc_1"))
        finally:
            os.unlink(tmp_path)

    def test_merge(self):
        bank2 = QuestionBank()
        q = SingleChoiceQuestion(
            id="merged_q",
            content="merged",
            answer="A",
            options=[{"key": "A", "value": "x"}],
        )
        bank2.add_question(q)
        self.bank.merge(bank2)
        self.assertEqual(self.bank.count, 8)


class TestExamBuilder(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = ExamBuilder(self.bank)

    def test_quick_build(self):
        exam = self.builder.quick_build(
            count=3,
            grade="一年级",
            subject="数学",
            title="单元测试",
        )
        self.assertEqual(len(exam.questions), 2)
        self.assertEqual(exam.title, "单元测试")

    def test_build_with_type_configs(self):
        config = ExamConfig(
            title="混合测试",
            type_configs=[
                TypeConfig(QuestionType.SINGLE_CHOICE, 2, 4),
                TypeConfig(QuestionType.TRUE_FALSE, 2, 2),
            ],
            seed=123,
        )
        exam = self.builder.build(config)
        self.assertEqual(len(exam.questions), 4)
        type_count = exam.get_question_count_by_type()
        self.assertEqual(type_count[QuestionType.SINGLE_CHOICE], 2)
        self.assertEqual(type_count[QuestionType.TRUE_FALSE], 2)
        for q in exam.get_questions_by_type(QuestionType.SINGLE_CHOICE):
            self.assertEqual(q.score, 4)

    def test_build_with_difficulty_configs(self):
        config = ExamConfig(
            title="难度测试",
            total_questions=5,
            difficulty_configs=[
                DifficultyConfig(Difficulty.EASY, 0.6),
                DifficultyConfig(Difficulty.MEDIUM, 0.4),
            ],
            seed=456,
        )
        exam = self.builder.build(config)
        self.assertLessEqual(len(exam.questions), 5)

    def test_build_from_question_ids(self):
        exam = self.builder.build_from_question_ids(
            ["t_sc_1", "t_fb_1", "t_tf_1"],
            title="指定题目卷",
            total_score=100,
        )
        self.assertEqual(len(exam.questions), 3)

    def test_build_invalid_config(self):
        config = ExamConfig(title="no params")
        with self.assertRaises(ValueError):
            self.builder.build(config)

    def test_build_shuffle(self):
        config1 = ExamConfig(
            title="s1",
            total_questions=5,
            shuffle=False,
            seed=1,
        )
        config2 = ExamConfig(
            title="s2",
            total_questions=5,
            shuffle=True,
            seed=999,
        )
        e1 = self.builder.build(config1)
        e2 = self.builder.build(config2)
        ids1 = [q.id for q in e1.questions]
        ids2 = [q.id for q in e2.questions]
        self.assertNotEqual(ids1, ids2)


class TestGrader(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = ExamBuilder(self.bank)
        self.grader = Grader()

    def test_grade_single_choice_correct(self):
        q = self.bank.get_question("t_sc_1")
        result = self.grader.grade_question(q, "B")
        self.assertTrue(result.is_correct)
        self.assertEqual(result.score, 3)

    def test_grade_single_choice_wrong(self):
        q = self.bank.get_question("t_sc_1")
        result = self.grader.grade_question(q, "A")
        self.assertFalse(result.is_correct)
        self.assertEqual(result.score, 0)

    def test_grade_single_choice_none(self):
        q = self.bank.get_question("t_sc_1")
        result = self.grader.grade_question(q, None)
        self.assertFalse(result.is_correct)

    def test_grade_multiple_choice_full(self):
        q = self.bank.get_question("t_mc_1")
        result = self.grader.grade_question(q, ["A", "C", "D"])
        self.assertTrue(result.is_correct)
        self.assertEqual(result.score, 5)

    def test_grade_multiple_choice_partial(self):
        q = self.bank.get_question("t_mc_1")
        result = self.grader.grade_question(q, ["A", "C"])
        self.assertFalse(result.is_correct)
        self.assertGreater(result.score, 0)
        self.assertLess(result.score, 5)

    def test_grade_multiple_choice_wrong(self):
        q = self.bank.get_question("t_mc_1")
        result = self.grader.grade_question(q, ["B", "E"])
        self.assertFalse(result.is_correct)
        self.assertEqual(result.score, 0)

    def test_grade_multiple_choice_string(self):
        q = self.bank.get_question("t_mc_1")
        result = self.grader.grade_question(q, "ACD")
        self.assertTrue(result.is_correct)

    def test_grade_fill_blank_all_correct(self):
        q = self.bank.get_question("t_fb_1")
        result = self.grader.grade_question(q, ["(长+宽)×2", "长×宽"])
        self.assertTrue(result.is_correct)
        self.assertEqual(result.score, 4)

    def test_grade_fill_blank_partial(self):
        q = self.bank.get_question("t_fb_1")
        result = self.grader.grade_question(q, ["(长+宽)×2", "错"])
        self.assertFalse(result.is_correct)
        self.assertEqual(result.score, 2)

    def test_grade_true_false_bool(self):
        q = self.bank.get_question("t_tf_1")
        result = self.grader.grade_question(q, True)
        self.assertTrue(result.is_correct)
        q2 = self.bank.get_question("t_tf_2")
        result2 = self.grader.grade_question(q2, False)
        self.assertTrue(result2.is_correct)

    def test_grade_true_false_string(self):
        q = self.bank.get_question("t_tf_1")
        r1 = self.grader.grade_question(q, "对")
        self.assertTrue(r1.is_correct)
        r2 = self.grader.grade_question(q, "T")
        self.assertTrue(r2.is_correct)
        r3 = self.grader.grade_question(q, "错误")
        self.assertFalse(r3.is_correct)

    def test_grade_short_answer_full(self):
        q = self.bank.get_question("t_sa_1")
        ans = "原来有5个，给了2个，剩5-2=3个，又买3个，3+3=6个。答：现在有6个苹果。"
        result = self.grader.grade_question(q, ans)
        self.assertTrue(result.is_correct)

    def test_grade_short_answer_empty(self):
        q = self.bank.get_question("t_sa_1")
        result = self.grader.grade_question(q, "")
        self.assertFalse(result.is_correct)
        self.assertEqual(result.score, 0)

    def test_grade_exam_full(self):
        exam = self.builder.build_from_question_ids(
            ["t_sc_1", "t_sc_2", "t_tf_1", "t_fb_1"],
            title="测试卷",
        )
        answers = [
            StudentAnswer("t_sc_1", "B"),
            StudentAnswer("t_sc_2", "C"),
            StudentAnswer("t_tf_1", True),
            StudentAnswer("t_fb_1", ["(长+宽)×2", "长×宽"]),
        ]
        result = self.grader.grade_exam(
            exam=exam,
            student_answers=answers,
            student_id="s_test",
        )
        self.assertEqual(result.correct_count, 4)
        self.assertEqual(result.wrong_count, 0)
        self.assertEqual(result.percentage, 100.0)
        self.assertIsNotNone(result.completed_at)

    def test_grade_summary(self):
        exam = self.builder.build_from_question_ids(
            ["t_sc_1", "t_tf_1", "t_fb_1"],
        )
        answers = [
            StudentAnswer("t_sc_1", "B"),
            StudentAnswer("t_tf_1", False),
            StudentAnswer("t_fb_1", ["a", "b"]),
        ]
        result = self.grader.grade_exam(exam, answers, "s1")
        summary = self.grader.get_summary(result)
        self.assertIn("level", summary)
        self.assertIn("by_type", summary)
        self.assertIn("accuracy", summary)


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = ExamBuilder(self.bank)
        self.grader = Grader()
        self.analytics = Analytics(self.bank)

    def _make_results(self):
        results = []
        for i in range(3):
            exam = self.builder.build_from_question_ids(
                ["t_sc_1", "t_sc_2", "t_mc_1", "t_tf_1", "t_tf_2"],
                title=f"练习{i+1}",
            )
            answers = []
            for q in exam.questions:
                if i == 0:
                    if q.question_type == QuestionType.SINGLE_CHOICE:
                        ans = "A"
                    elif q.question_type == QuestionType.MULTIPLE_CHOICE:
                        ans = ["B"]
                    elif q.question_type == QuestionType.TRUE_FALSE:
                        ans = False
                    else:
                        ans = ""
                elif i == 1:
                    if q.id in ["t_sc_1", "t_tf_1"]:
                        ans = q.answer
                    elif q.question_type == QuestionType.SINGLE_CHOICE:
                        ans = "A"
                    elif q.question_type == QuestionType.MULTIPLE_CHOICE:
                        ans = ["B", "E"]
                    else:
                        ans = q.answer
                else:
                    ans = q.answer
                answers.append(StudentAnswer(q.id, ans))
            result = self.grader.grade_exam(
                exam, answers, "stu_1",
                completed_at=datetime.now() - timedelta(days=3 - i),
            )
            results.append(result)
        return results

    def test_collect_wrong_questions(self):
        results = self._make_results()
        wb = self.analytics.collect_wrong_questions(results, "stu_1")
        self.assertGreater(len(wb), 0)
        for qid, wq in wb.items():
            self.assertGreaterEqual(wq.wrong_count, 1)

    def test_merge_wrong_books(self):
        wb1: Dict[str, WrongQuestion] = {
            "q1": WrongQuestion(question_id="q1", wrong_count=2, knowledge_points=["kp1"]),
            "q2": WrongQuestion(question_id="q2", wrong_count=1, knowledge_points=["kp2"]),
        }
        wb2: Dict[str, WrongQuestion] = {
            "q2": WrongQuestion(question_id="q2", wrong_count=3, knowledge_points=["kp2", "kp3"]),
            "q3": WrongQuestion(question_id="q3", wrong_count=1, knowledge_points=["kp4"]),
        }
        merged = self.analytics.merge_wrong_books(wb1, wb2)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged["q1"].wrong_count, 2)
        self.assertEqual(merged["q2"].wrong_count, 4)
        self.assertEqual(merged["q3"].wrong_count, 1)
        for kp in ["kp2", "kp3"]:
            self.assertIn(kp, merged["q2"].knowledge_points)
        wb3: Dict[str, WrongQuestion] = {
            "q1": WrongQuestion(question_id="q1", wrong_count=5, knowledge_points=["kp5"]),
        }
        merged2 = self.analytics.merge_wrong_books(wb1, wb2, wb3)
        self.assertEqual(merged2["q1"].wrong_count, 7)

    def test_analyze_knowledge_points(self):
        results = self._make_results()
        kps = self.analytics.analyze_knowledge_points(results, "stu_1")
        self.assertGreater(len(kps), 0)
        for kp in kps:
            self.assertGreaterEqual(kp.total_questions, 1)

    def test_get_weak_knowledge_points(self):
        results = self._make_results()
        weak = self.analytics.get_weak_knowledge_points(results, "stu_1")
        for w in weak:
            self.assertTrue(w.is_weak)

    def test_analyze_by_type(self):
        results = self._make_results()
        type_stats = self.analytics.analyze_by_question_type(results, "stu_1")
        self.assertIn("单选题", type_stats)
        for t, s in type_stats.items():
            self.assertIn("accuracy", s)

    def test_analyze_by_difficulty(self):
        results = self._make_results()
        qmap = {q.id: q for q in self.bank.questions}
        diff_stats = self.analytics.analyze_by_difficulty(results, qmap, "stu_1")
        self.assertIsInstance(diff_stats, dict)

    def test_compare_practice_history(self):
        results = self._make_results()
        records = self.analytics.build_practice_records(results, "stu_1")
        comparison = self.analytics.compare_practice_history(records)
        self.assertIn("average_percentage", comparison)
        self.assertIn("trend", comparison)
        self.assertIn("best", comparison)

    def test_calculate_student_overall_report(self):
        results = self._make_results()
        qmap = {q.id: q for q in self.bank.questions}
        report = self.analytics.calculate_student_overall_report(results, "stu_1", qmap)
        self.assertEqual(report["student_id"], "stu_1")
        self.assertIn("summary", report)
        self.assertIn("suggestions", report)
        self.assertIn("wrong_book_summary", report)


class TestExporter(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = ExamBuilder(self.bank)
        self.grader = Grader()
        self.exporter = Exporter()
        self.exam = self.builder.build_from_question_ids(
            ["t_sc_1", "t_mc_1", "t_tf_1", "t_sa_1"],
            title="导出测试卷",
        )
        answers = [
            StudentAnswer("t_sc_1", "B"),
            StudentAnswer("t_mc_1", ["A", "C"]),
            StudentAnswer("t_tf_1", True),
            StudentAnswer("t_sa_1", "5-2+3=6，现在有6个苹果"),
        ]
        self.result = self.grader.grade_exam(self.exam, answers, "stu_export")

    def test_export_exam_student_all_formats(self):
        for fmt in ["text", "markdown", "html"]:
            content = self.exporter.export_exam_student(self.exam, format=fmt)
            self.assertIn("导出测试卷", content)

    def test_export_exam_teacher_all_formats(self):
        for fmt in ["text", "markdown", "html"]:
            content = self.exporter.export_exam_teacher(self.exam, format=fmt)
            self.assertIn("教师答案版", content)
            self.assertIn("正确答案", content)

    def test_export_exam_result_all_formats(self):
        for fmt in ["text", "markdown", "html"]:
            content = self.exporter.export_exam_result(
                self.result, self.exam, format=fmt
            )
            self.assertIn(str(self.result.percentage), content)

    def test_export_wrong_book(self):
        analytics = Analytics(self.bank)
        wb = analytics.collect_wrong_questions([self.result], "stu_export")
        for fmt in ["text", "markdown", "html"]:
            content = self.exporter.export_wrong_book(
                list(wb.values()), format=fmt, student_id="stu_export"
            )
            self.assertIn("错题", content)

    def test_export_practice_report(self):
        analytics = Analytics(self.bank)
        qmap = {q.id: q for q in self.bank.questions}
        report = analytics.calculate_student_overall_report(
            [self.result], "stu_export", qmap
        )
        for fmt in ["text", "markdown", "html"]:
            content = self.exporter.export_practice_report(report, format=fmt)
            self.assertGreater(len(content), 10)

    def test_save_to_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
        try:
            content = self.exporter.export_exam_student(self.exam)
            self.exporter.save_to_file(content, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, "r", encoding="utf-8") as f:
                read_back = f.read()
            self.assertEqual(read_back, content)
        finally:
            os.unlink(tmp_path)


class TestReviewInfo(unittest.TestCase):
    def test_auto_status(self):
        ri = ReviewInfo(auto_score=5.0, review_status="auto")
        self.assertEqual(ri.effective_score, 5.0)

    def test_reviewed_status(self):
        ri = ReviewInfo(auto_score=3.0, reviewed_score=5.0, review_status="reviewed")
        self.assertEqual(ri.effective_score, 5.0)

    def test_pending_status(self):
        ri = ReviewInfo(auto_score=4.0, review_status="pending_review")
        self.assertEqual(ri.effective_score, 4.0)

    def test_to_dict(self):
        ri = ReviewInfo(auto_score=3.0, reviewed_score=5.0, review_status="reviewed", reviewer_id="teacher1")
        d = ri.to_dict()
        self.assertEqual(d["auto_score"], 3.0)
        self.assertEqual(d["reviewed_score"], 5.0)
        self.assertEqual(d["reviewer_id"], "teacher1")

    def test_question_result_with_review_info(self):
        qr = QuestionResult(
            question_id="q1", student_answer="ans", correct_answer="ans2",
            is_correct=False, score=3, max_score=5,
            review_info=ReviewInfo(auto_score=3, review_status="pending_review"),
        )
        self.assertIsNotNone(qr.review_info)
        d = qr.to_dict()
        self.assertIn("review_info", d)
        self.assertEqual(d["review_info"]["review_status"], "pending_review")


class TestTrueFalseSafety(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.grader = Grader()

    def test_valid_true_answers(self):
        q = self.bank.get_question("t_tf_1")
        for ans in ["对", "正确", "T", "t", "1", "是", True]:
            r = self.grader.grade_question(q, ans)
            self.assertTrue(r.is_correct, f"Expected True for answer '{ans}'")

    def test_valid_false_answers(self):
        q = self.bank.get_question("t_tf_2")
        for ans in ["错", "错误", "F", "f", "0", "否", False]:
            r = self.grader.grade_question(q, ans)
            self.assertTrue(r.is_correct, f"Expected True for answer '{ans}'")

    def test_unrecognized_answer(self):
        q = self.bank.get_question("t_tf_1")
        r = self.grader.grade_question(q, "maybe")
        self.assertFalse(r.is_correct)
        self.assertIn("无法识别", r.feedback)

    def test_no_eval_on_arbitrary_string(self):
        q = self.bank.get_question("t_tf_1")
        r = self.grader.grade_question(q, "__import__('os').system('echo hack')")
        self.assertFalse(r.is_correct)
        self.assertIn("无法识别", r.feedback)


class TestShortAnswerReviewStatus(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.grader = Grader()

    def test_short_answer_has_pending_review(self):
        q = self.bank.get_question("t_sa_1")
        ans = "原来有5个，给了2个，剩3个，又买3个，3+3=6个。"
        r = self.grader.grade_question(q, ans)
        self.assertIsNotNone(r.review_info)
        self.assertEqual(r.review_info.review_status, "pending_review")
        self.assertEqual(r.review_info.auto_score, r.score)

    def test_short_answer_empty_has_pending_review(self):
        q = self.bank.get_question("t_sa_1")
        r = self.grader.grade_question(q, "")
        self.assertIsNotNone(r.review_info)
        self.assertEqual(r.review_info.review_status, "pending_review")

    def test_other_types_have_auto_status(self):
        q = self.bank.get_question("t_sc_1")
        r = self.grader.grade_question(q, "B")
        self.assertIsNotNone(r.review_info)
        self.assertEqual(r.review_info.review_status, "auto")


class TestExamResultMaxScore(unittest.TestCase):
    def test_max_score_uses_exam_total(self):
        bank = create_test_bank()
        builder = ExamBuilder(bank)
        exam = builder.build_from_question_ids(
            ["t_sc_1", "t_tf_1"],
            total_score=100,
        )
        self.assertEqual(exam.total_score, 100)
        answers = [
            StudentAnswer("t_sc_1", "B"),
            StudentAnswer("t_tf_1", True),
        ]
        grader = Grader()
        result = grader.grade_exam(exam, answers, "s1")
        self.assertEqual(result.max_score, 100)

    def test_max_score_auto_when_no_override(self):
        bank = create_test_bank()
        builder = ExamBuilder(bank)
        exam = builder.build_from_question_ids(["t_sc_1", "t_tf_1"])
        self.assertEqual(exam.total_score, 5)
        answers = [
            StudentAnswer("t_sc_1", "B"),
            StudentAnswer("t_tf_1", True),
        ]
        grader = Grader()
        result = grader.grade_exam(exam, answers, "s1")
        self.assertEqual(result.max_score, 5)


class TestAdaptiveBuilder(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = AdaptiveBuilder(self.bank)

    def test_build_adaptive_basic(self):
        wrong_book = {
            "t_sc_1": WrongQuestion(question_id="t_sc_1", wrong_count=3, knowledge_points=["加法"]),
            "t_tf_2": WrongQuestion(question_id="t_tf_2", wrong_count=2, knowledge_points=["除法"]),
        }
        weak_kps = [
            KnowledgePointStats(knowledge_point="加法", total_questions=3, correct_count=1, wrong_count=2, total_score=10, earned_score=3),
        ]
        paper, rationale = self.builder.build_adaptive(
            wrong_book=wrong_book,
            weak_knowledge_points=weak_kps,
            total_count=5,
            subject="数学",
            seed=42,
        )
        self.assertGreater(len(paper.questions), 0)
        self.assertIsNotNone(rationale.summary)
        self.assertIn("加法", rationale.knowledge_point_allocations)
        self.assertGreater(len(rationale.type_distribution), 0)

    def test_build_adaptive_rationale_to_dict(self):
        wrong_book = {
            "t_sc_1": WrongQuestion(question_id="t_sc_1", wrong_count=2, knowledge_points=["加法"]),
        }
        weak_kps = []
        paper, rationale = self.builder.build_adaptive(
            wrong_book=wrong_book,
            weak_knowledge_points=weak_kps,
            total_count=3,
            seed=42,
        )
        d = rationale.to_dict()
        self.assertIn("knowledge_point_allocations", d)
        self.assertIn("difficulty_strategy", d)
        self.assertIn("summary", d)

    def test_build_adaptive_with_no_weak(self):
        paper, rationale = self.builder.build_adaptive(
            wrong_book={},
            weak_knowledge_points=[],
            total_count=4,
            subject="数学",
            seed=42,
        )
        self.assertGreater(len(paper.questions), 0)
        self.assertGreater(len(rationale.summary), 0)

    def test_paper_has_rationale_metadata(self):
        wrong_book = {
            "t_sc_1": WrongQuestion(question_id="t_sc_1", wrong_count=1, knowledge_points=["加法"]),
        }
        paper, _ = self.builder.build_adaptive(
            wrong_book=wrong_book,
            weak_knowledge_points=[],
            total_count=3,
            seed=42,
        )
        self.assertIn("adaptive_rationale", paper.metadata)


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = ExamBuilder(self.bank)
        self.mgr = SessionManager()
        self.grader = Grader()

    def test_create_session(self):
        exam = self.builder.build_from_question_ids(["t_sc_1", "t_tf_1"], title="会话测试")
        session = self.mgr.create_session("stu_1", exam)
        self.assertEqual(session.student_id, "stu_1")
        self.assertEqual(session.status, "created")
        self.assertIsNotNone(session.exam_paper)

    def test_submit_answer_and_grade(self):
        exam = self.builder.build_from_question_ids(["t_sc_1", "t_tf_1"], title="会话测试")
        session = self.mgr.create_session("stu_1", exam)
        self.mgr.submit_answer(session.id, "t_sc_1", "B")
        self.mgr.submit_answer(session.id, "t_tf_1", True)
        result = self.mgr.grade_session(session.id)
        self.assertEqual(session.status, "graded")
        self.assertEqual(result.correct_count, 2)

    def test_submit_answers_bulk(self):
        exam = self.builder.build_from_question_ids(["t_sc_1", "t_tf_1"], title="会话测试")
        session = self.mgr.create_session("stu_1", exam)
        self.mgr.submit_answers(session.id, {"t_sc_1": "B", "t_tf_1": True})
        result = self.mgr.grade_session(session.id)
        self.assertEqual(result.correct_count, 2)

    def test_review_question(self):
        exam = self.builder.build_from_question_ids(["t_sa_1"], title="复核测试")
        session = self.mgr.create_session("stu_1", exam)
        self.mgr.submit_answer(session.id, "t_sa_1", "5-2+3=6")
        result = self.mgr.grade_session(session.id)
        sa_qr = result.question_results[0]
        self.assertEqual(sa_qr.review_info.review_status, "pending_review")
        reviewed = self.mgr.review_question(
            session.id, "t_sa_1",
            reviewed_score=7.0,
            reviewer_id="teacher_zhang",
            review_comment="过程正确但答句不够完整",
        )
        self.assertEqual(reviewed.review_info.review_status, "reviewed")
        self.assertEqual(reviewed.review_info.reviewed_score, 7.0)
        self.assertEqual(reviewed.review_info.reviewer_id, "teacher_zhang")
        self.assertEqual(session.status, "reviewed")

    def test_close_session(self):
        exam = self.builder.build_from_question_ids(["t_sc_1"], title="关闭测试")
        session = self.mgr.create_session("stu_1", exam)
        self.mgr.submit_answer(session.id, "t_sc_1", "B")
        self.mgr.grade_session(session.id)
        self.mgr.close_session(session.id)
        self.assertEqual(session.status, "closed")

    def test_query_history(self):
        exam = self.builder.build_from_question_ids(["t_sc_1"], title="历史测试", total_score=100)
        self.mgr.create_session("stu_A", exam)
        self.mgr.create_session("stu_B", exam)
        results = self.mgr.query_history(student_id="stu_A")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].student_id, "stu_A")

    def test_query_by_knowledge_point(self):
        exam = self.builder.build_from_question_ids(["t_sc_1", "t_tf_1"], title="知识点查询")
        session = self.mgr.create_session("stu_1", exam)
        results = self.mgr.query_history(knowledge_point="加法")
        self.assertGreater(len(results), 0)

    def test_session_persistence(self):
        exam = self.builder.build_from_question_ids(["t_sc_1", "t_tf_1"], title="持久化测试")
        session = self.mgr.create_session("stu_1", exam)
        self.mgr.submit_answers(session.id, {"t_sc_1": "B", "t_tf_1": True})
        self.mgr.grade_session(session.id)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp_path = f.name
        try:
            self.mgr.save_to_json(tmp_path)
            mgr2 = SessionManager()
            exam_papers = {exam.id: exam}
            mgr2.load_from_json(tmp_path, exam_papers)
            loaded = mgr2.get_session(session.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.student_id, "stu_1")
            self.assertEqual(loaded.status, "graded")
            self.assertIsNotNone(loaded.exam_result)
            self.assertEqual(loaded.exam_result.correct_count, 2)
        finally:
            os.unlink(tmp_path)

    def test_status_transitions_invalid(self):
        exam = self.builder.build_from_question_ids(["t_sc_1"], title="状态测试")
        session = self.mgr.create_session("stu_1", exam)
        with self.assertRaises(ValueError):
            self.mgr.close_session(session.id)
        with self.assertRaises(ValueError):
            self.mgr.review_question(session.id, "t_sc_1", 5.0, "t1")


class TestAnalyticsReview(unittest.TestCase):
    def test_sessions_to_exam_results(self):
        bank = create_test_bank()
        builder = ExamBuilder(bank)
        grader = Grader()
        mgr = SessionManager()

        exam = builder.build_from_question_ids(["t_sc_1", "t_tf_1"], title="分析测试")
        s1 = mgr.create_session("stu_1", exam)
        mgr.submit_answers(s1.id, {"t_sc_1": "B", "t_tf_1": True})
        mgr.grade_session(s1.id)

        analytics = Analytics(bank)
        results = analytics.sessions_to_exam_results([s1], "stu_1")
        self.assertEqual(len(results), 1)

    def test_analyze_review_status(self):
        bank = create_test_bank()
        builder = ExamBuilder(bank)
        grader = Grader()
        analytics = Analytics(bank)

        exam = builder.build_from_question_ids(["t_sc_1", "t_sa_1"], title="复核分析测试")
        answers = [
            StudentAnswer("t_sc_1", "B"),
            StudentAnswer("t_sa_1", "5-2+3=6，有6个苹果"),
        ]
        result = grader.grade_exam(exam, answers, "stu_1")

        review_stats = analytics.analyze_review_status([result])
        self.assertGreater(review_stats["total_questions"], 0)
        self.assertGreater(review_stats["auto_graded"], 0)
        self.assertGreaterEqual(review_stats["pending_review"], 1)


class TestExporterReviewAndAdaptive(unittest.TestCase):
    def setUp(self):
        self.bank = create_test_bank()
        self.builder = ExamBuilder(self.bank)
        self.grader = Grader()
        self.exporter = Exporter()

    def test_result_text_shows_review_info(self):
        exam = self.builder.build_from_question_ids(["t_sa_1"], title="复核导出测试")
        result = self.grader.grade_exam(
            exam, [StudentAnswer("t_sa_1", "5-2+3=6")], "stu_1"
        )
        content = self.exporter.export_exam_result(result, exam, format="text")
        self.assertIn("待复核", content)

    def test_result_markdown_shows_review_info(self):
        exam = self.builder.build_from_question_ids(["t_sa_1"], title="复核导出测试")
        result = self.grader.grade_exam(
            exam, [StudentAnswer("t_sa_1", "5-2+3=6")], "stu_1"
        )
        content = self.exporter.export_exam_result(result, exam, format="markdown")
        self.assertIn("待复核", content)

    def test_result_html_shows_review_info(self):
        exam = self.builder.build_from_question_ids(["t_sa_1"], title="复核导出测试")
        result = self.grader.grade_exam(
            exam, [StudentAnswer("t_sa_1", "5-2+3=6")], "stu_1"
        )
        content = self.exporter.export_exam_result(result, exam, format="html")
        self.assertIn("待复核", content)

    def test_export_adaptive_rationale(self):
        wrong_book = {
            "t_sc_1": WrongQuestion(question_id="t_sc_1", wrong_count=2, knowledge_points=["加法"]),
        }
        adaptive = AdaptiveBuilder(self.bank)
        paper, rationale = adaptive.build_adaptive(
            wrong_book=wrong_book,
            weak_knowledge_points=[],
            total_count=3,
            seed=42,
        )
        for fmt in ["text", "markdown", "html"]:
            content = self.exporter.export_adaptive_rationale(rationale, format=fmt)
            self.assertGreater(len(content), 10)
            self.assertIn("自适应组卷说明", content)


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestModels))
    suite.addTests(loader.loadTestsFromTestCase(TestQuestionBank))
    suite.addTests(loader.loadTestsFromTestCase(TestExamBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestGrader))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalytics))
    suite.addTests(loader.loadTestsFromTestCase(TestExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestReviewInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestTrueFalseSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestShortAnswerReviewStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestExamResultMaxScore))
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptiveBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyticsReview))
    suite.addTests(loader.loadTestsFromTestCase(TestExporterReviewAndAdaptive))

    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    print("=" * 70)
    print("教育练习题生成与批改类库 - 单元测试")
    print("=" * 70)
    result = run_tests()
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("[PASS] 所有测试通过！")
    else:
        print("[FAIL] 有测试未通过，请检查输出。")
    sys.exit(0 if result.wasSuccessful() else 1)
