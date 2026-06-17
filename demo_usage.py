"""
教育练习题生成与批改类库 - 完整使用示例
演示题库读取、试卷组装、答案批改、统计分析和导出功能
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edu_exercise import (
    QuestionBank,
    ExamBuilder,
    ExamConfig,
    TypeConfig,
    DifficultyConfig,
    QuestionType,
    Difficulty,
    Grader,
    StudentAnswer,
    Analytics,
    Exporter,
)


def demo_1_basic_workflow():
    print("=" * 70)
    print("【示例1】基本工作流：题库加载 -> 试卷组装 -> 学生作答 -> 批改评分")
    print("=" * 70)

    bank = QuestionBank.from_json("sample_questions.json")
    print(f"\n✓ 题库加载成功，共 {bank.count} 道题目")
    stats = bank.get_statistics()
    print(f"  - 按题型分布：{stats['by_type']}")
    print(f"  - 按难度分布：{stats['by_difficulty']}")
    print(f"  - 可用知识点：{sorted(bank.get_all_knowledge_points())}")

    builder = ExamBuilder(bank)

    config = ExamConfig(
        title="五年级数学综合练习卷",
        grades=["五年级"],
        subjects=["数学"],
        type_configs=[
            TypeConfig(question_type=QuestionType.SINGLE_CHOICE, count=1, score_per_question=5),
            TypeConfig(question_type=QuestionType.MULTIPLE_CHOICE, count=1, score_per_question=8),
            TypeConfig(question_type=QuestionType.FILL_BLANK, count=1, score_per_question=6),
            TypeConfig(question_type=QuestionType.TRUE_FALSE, count=1, score_per_question=4),
            TypeConfig(question_type=QuestionType.SHORT_ANSWER, count=1, score_per_question=15),
        ],
        difficulty_configs=[
            DifficultyConfig(difficulty=Difficulty.EASY, ratio=0.4),
            DifficultyConfig(difficulty=Difficulty.MEDIUM, ratio=0.4),
            DifficultyConfig(difficulty=Difficulty.HARD, ratio=0.2),
        ],
        duration_minutes=45,
        seed=42,
    )

    exam = builder.build(config)
    print(f"\n✓ 试卷生成成功：{exam.title}")
    print(f"  - 总分：{exam.total_score}分，共{len(exam.questions)}题")
    print(f"  - 题型分布：{ {k.display_name: v for k, v in exam.get_question_count_by_type().items()} }")

    student_answers = [
        StudentAnswer(question_id=exam.questions[0].id, answer="C"),
        StudentAnswer(question_id=exam.questions[1].id, answer=["A", "B", "D"]),
        StudentAnswer(question_id=exam.questions[2].id, answer=["6", "36"]),
        StudentAnswer(question_id=exam.questions[3].id, answer=True),
        StudentAnswer(
            question_id=exam.questions[4].id,
            answer="第一天看120×1/4=30页，第二天看120×1/3=40页，剩下120-30-40=50页。答：还剩50页没看。"
        ),
    ]

    grader = Grader()
    result = grader.grade_exam(
        exam=exam,
        student_answers=student_answers,
        student_id="stu_1001",
        started_at=datetime.now() - timedelta(minutes=35),
        completed_at=datetime.now(),
        time_spent_seconds=35 * 60,
    )

    print(f"\n✓ 批改完成！")
    print(f"  - 得分：{result.total_score} / {result.max_score} 分 ({result.percentage}%)")
    print(f"  - 正确 {result.correct_count} 题，错误 {result.wrong_count} 题")

    summary = grader.get_summary(result)
    print(f"  - 评级：{summary['level']}")
    print(f"  - 整体正确率：{summary['accuracy']}%")

    print("\n--- 各题得分详情 ---")
    for idx, qr in enumerate(result.question_results, 1):
        status = "✅ 正确" if qr.is_correct else "❌ 错误"
        print(f"  {idx}. [{status}] {qr.score}/{qr.max_score}分 (ID:{qr.question_id})")
        if not qr.is_correct and qr.feedback:
            print(f"      反馈：{qr.feedback[:80]}...")

    return bank, exam, result


def demo_2_exam_variants():
    print("\n" + "=" * 70)
    print("【示例2】多种组卷方式：快速组卷 / 指定题目 / 错题练习 / 按难度比例")
    print("=" * 70)

    bank = QuestionBank.from_json("sample_questions.json")
    builder = ExamBuilder(bank)

    print("\n--- 快速组卷（简洁版）---")
    quick_exam = builder.quick_build(
        count=3,
        grade="五年级",
        subject="数学",
        question_type=QuestionType.SINGLE_CHOICE,
        difficulty=Difficulty.EASY,
        title="五年级数学单选题专项练习",
    )
    print(f"  生成试卷：{quick_exam.title}，{len(quick_exam.questions)}题，{quick_exam.total_score}分")

    print("\n--- 指定题目ID组卷 ---")
    id_exam = builder.build_from_question_ids(
        question_ids=["math_001", "math_005", "math_007", "chn_002"],
        title="混合学科针对性练习",
        total_score=20,
    )
    print(f"  生成试卷：{id_exam.title}，{len(id_exam.questions)}题")
    for q in id_exam.questions:
        print(f"    - [{q.question_type.display_name}] {q.subject}: {q.content[:40]}...")

    print("\n--- 按难度比例智能组卷 ---")
    diff_config = ExamConfig(
        title="分层难度练习卷",
        total_questions=5,
        subjects=["数学"],
        difficulty_configs=[
            DifficultyConfig(difficulty=Difficulty.EASY, ratio=0.4),
            DifficultyConfig(difficulty=Difficulty.MEDIUM, ratio=0.4),
            DifficultyConfig(difficulty=Difficulty.HARD, ratio=0.2),
        ],
    )
    diff_exam = builder.build(diff_config)
    dist = {}
    for q in diff_exam.questions:
        d = q.difficulty.display_name
        dist[d] = dist.get(d, 0) + 1
    print(f"  生成试卷：{diff_exam.title}，难度分布：{dist}")

    return quick_exam, id_exam, diff_exam


def demo_3_analytics_and_wrong_book():
    print("\n" + "=" * 70)
    print("【示例3】统计分析：错题本、薄弱知识点、练习历史对比")
    print("=" * 70)

    bank = QuestionBank.from_json("sample_questions.json")
    builder = ExamBuilder(bank)
    grader = Grader()
    analytics = Analytics(bank)

    print("\n--- 模拟生成3次练习记录 ---")
    exam_results = []
    base_date = datetime.now() - timedelta(days=10)

    for i in range(3):
        exam = builder.quick_build(
            count=5,
            subject="数学",
            title=f"数学周练 {i+1}",
        )

        ans_list = []
        for q in exam.questions:
            if i == 0:
                if q.id in ["math_001", "math_005"]:
                    ans = q.answer
                elif q.question_type == QuestionType.SINGLE_CHOICE:
                    ans = "A"
                elif q.question_type == QuestionType.MULTIPLE_CHOICE:
                    ans = ["A", "B"]
                elif q.question_type == QuestionType.FILL_BLANK:
                    ans = ["0", "0"]
                elif q.question_type == QuestionType.TRUE_FALSE:
                    ans = False
                else:
                    ans = "不会做这道题"
            elif i == 1:
                if q.id in ["math_001", "math_005", "math_007"]:
                    ans = q.answer
                else:
                    ans = q.answer if i % 2 == 0 else "部分正确的答案"
            else:
                ans = q.answer

            ans_list.append(StudentAnswer(question_id=q.id, answer=ans))

        result = grader.grade_exam(
            exam=exam,
            student_answers=ans_list,
            student_id="stu_1001",
            completed_at=base_date + timedelta(days=i * 4, minutes=i * 30),
        )
        exam_results.append(result)
        print(f"  第{i+1}次练习：得分 {result.total_score}/{result.max_score} ({result.percentage}%)")

    print("\n--- 错题本收集与合并 ---")
    wrong_book = analytics.collect_wrong_questions(exam_results, student_id="stu_1001")
    print(f"  共收集错题：{len(wrong_book)} 道")
    for qid, wq in wrong_book.items():
        q = bank.get_question(qid)
        title = q.content[:30] if q else "未知"
        print(f"    - ID:{qid} [{q.question_type.display_name if q else ''}] 错{wq.wrong_count}次：{title}...")

    print("\n--- 薄弱知识点分析 ---")
    weak_kps = analytics.get_weak_knowledge_points(exam_results, "stu_1001")
    if weak_kps:
        for kp in weak_kps:
            print(f"  ⚠️ {kp.knowledge_point}：掌握度{kp.mastery_level}%，正确率{kp.accuracy}%（{kp.wrong_count}次错误）")
    else:
        print("  暂无薄弱知识点，表现不错！")

    print("\n--- 练习历史趋势对比 ---")
    records = analytics.build_practice_records(exam_results, "stu_1001")
    comparison = analytics.compare_practice_history(records)
    print(f"  平均分：{comparison['average_percentage']}%")
    print(f"  学习趋势：{comparison['trend']}")
    if comparison.get("trend_delta"):
        print(f"  趋势变化：{comparison['trend_delta']:+.2f} 百分点")
    print(f"  稳定性：{comparison['stability']['level']}")
    print(f"  最佳成绩：{comparison['best']['percentage']}%")

    print("\n--- 学生综合报告 ---")
    questions_map = {q.id: q for q in bank.questions}
    report = analytics.calculate_student_overall_report(
        exam_results, "stu_1001", questions_map
    )
    print(f"  总答题：{report['summary']['total_questions']}题")
    print(f"  整体正确率：{report['summary']['overall_accuracy']}%")
    print("  学习建议：")
    for s in report["suggestions"]:
        print(f"    💡 {s}")

    return wrong_book, report


def demo_4_export():
    print("\n" + "=" * 70)
    print("【示例4】内容导出：试卷、答题卡、批改报告、错题本（文本/Markdown/HTML）")
    print("=" * 70)

    bank = QuestionBank.from_json("sample_questions.json")
    builder = ExamBuilder(bank)
    grader = Grader()
    exporter = Exporter()

    out_dir = "output_demo"
    os.makedirs(out_dir, exist_ok=True)

    exam = builder.quick_build(
        count=5,
        grade="五年级",
        subject="数学",
        title="五年级数学单元检测卷",
    )

    student_answers = []
    for i, q in enumerate(exam.questions):
        ans = q.answer if i % 2 == 0 else (q.answer if isinstance(q.answer, bool) else "错误答案")
        student_answers.append(StudentAnswer(question_id=q.id, answer=ans))

    result = grader.grade_exam(exam, student_answers, "stu_1001")

    print(f"\n导出目录：{os.path.abspath(out_dir)}")

    formats = ["text", "markdown", "html"]
    ext_map = {"text": "txt", "markdown": "md", "html": "html"}

    for fmt in formats:
        ext = ext_map[fmt]

        student_path = os.path.join(out_dir, f"exam_student.{ext}")
        content = exporter.export_exam_student(exam, format=fmt)
        exporter.save_to_file(content, student_path)
        print(f"  ✓ 学生版试卷 ({fmt.upper()})：{student_path}")

        teacher_path = os.path.join(out_dir, f"exam_teacher.{ext}")
        content = exporter.export_exam_teacher(exam, format=fmt)
        exporter.save_to_file(content, teacher_path)
        print(f"  ✓ 教师版答案 ({fmt.upper()})：{teacher_path}")

        result_path = os.path.join(out_dir, f"grade_result.{ext}")
        content = exporter.export_exam_result(result, exam, format=fmt)
        exporter.save_to_file(content, result_path)
        print(f"  ✓ 批改报告 ({fmt.upper()})：{result_path}")

    analytics = Analytics(bank)
    wrong_book = analytics.collect_wrong_questions([result], "stu_1001")
    wrong_list = list(wrong_book.values())

    for fmt in formats:
        ext = ext_map[fmt]
        wb_path = os.path.join(out_dir, f"wrong_book.{ext}")
        content = exporter.export_wrong_book(wrong_list, format=fmt, student_id="stu_1001")
        exporter.save_to_file(content, wb_path)
        print(f"  ✓ 错题本 ({fmt.upper()})：{wb_path}")

    questions_map = {q.id: q for q in bank.questions}
    report = analytics.calculate_student_overall_report([result], "stu_1001", questions_map)

    for fmt in formats:
        ext = ext_map[fmt]
        rp_path = os.path.join(out_dir, f"study_report.{ext}")
        content = exporter.export_practice_report(report, format=fmt)
        exporter.save_to_file(content, rp_path)
        print(f"  ✓ 学习报告 ({fmt.upper()})：{rp_path}")

    print("\n✓ 所有文件导出完成！可用浏览器打开HTML文件查看精美排版效果。")


def demo_5_question_filtering():
    print("\n" + "=" * 70)
    print("【示例5】题目筛选与题库统计")
    print("=" * 70)

    bank = QuestionBank.from_json("sample_questions.json")

    print(f"\n题库总数：{bank.count} 题")

    print("\n--- 按年级筛选：五年级 ---")
    grade5 = bank.filter(grades=["五年级"])
    print(f"  找到 {len(grade5)} 题")

    print("\n--- 按学科+难度筛选：数学 + 中等以上 ---")
    math_mid_hard = bank.filter(
        subjects=["数学"],
        difficulties=[Difficulty.MEDIUM, Difficulty.HARD],
    )
    print(f"  找到 {len(math_mid_hard)} 题")
    for q in math_mid_hard:
        print(f"    - {q.id}: [{q.difficulty.display_name}] {q.content[:40]}...")

    print("\n--- 按知识点筛选（含质数）---")
    prime = bank.filter(knowledge_points=["质数"])
    print(f"  找到 {len(prime)} 题")

    print("\n--- 多条件组合筛选（五年级数学+选择题+简单）---")
    combo = bank.filter(
        grades=["五年级"],
        subjects=["数学"],
        question_types=[QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE],
        difficulties=[Difficulty.EASY],
    )
    print(f"  找到 {len(combo)} 题")

    print("\n--- 题库统计概览 ---")
    stats = bank.get_statistics()
    for k, v in stats.items():
        if isinstance(v, dict):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

    print("\n--- 自定义筛选器（题目内容包含'圆'字）---")
    circle = bank.filter(custom_filter=lambda q: "圆" in q.content)
    print(f"  找到 {len(circle)} 题")
    for q in circle:
        print(f"    - {q.id}: {q.content[:50]}...")


def main():
    print("🏫 教育练习题生成与批改类库 - 完整演示")
    print("=" * 70)

    try:
        demo_1_basic_workflow()
        demo_2_exam_variants()
        demo_3_analytics_and_wrong_book()
        demo_4_export()
        demo_5_question_filtering()

        print("\n" + "=" * 70)
        print("✅ 所有示例演示完成！")
        print("📚 核心能力总结：")
        print("  1. 题库管理：JSON加载、多维度筛选、统计概览")
        print("  2. 试卷组装：快速组卷/指定题目/难度分层/错题练习")
        print("  3. 智能批改：5种题型自动评分、要点匹配、部分给分")
        print("  4. 数据分析：错题归类、薄弱知识点、历史趋势、综合报告")
        print("  5. 格式导出：试卷/答案/报告/错题本 → 文本/Markdown/HTML")
        print("=" * 70)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 运行出错：{e}")


if __name__ == "__main__":
    main()
