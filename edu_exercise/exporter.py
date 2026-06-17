from typing import List, Dict, Optional, Any
from datetime import datetime
from .models import (
    ExamPaper,
    ExamResult,
    QuestionResult,
    WrongQuestion,
    PracticeRecord,
    QuestionType,
    Question,
)


class Exporter:
    def __init__(self, indent: str = "  "):
        self.indent = indent

    def export_exam_student(
        self,
        exam: ExamPaper,
        format: str = "text",
        include_header: bool = True,
    ) -> str:
        if format == "markdown":
            return self._exam_student_markdown(exam, include_header)
        elif format == "html":
            return self._exam_student_html(exam, include_header)
        else:
            return self._exam_student_text(exam, include_header)

    def export_exam_teacher(
        self,
        exam: ExamPaper,
        format: str = "text",
        include_analysis: bool = True,
    ) -> str:
        if format == "markdown":
            return self._exam_teacher_markdown(exam, include_analysis)
        elif format == "html":
            return self._exam_teacher_html(exam, include_analysis)
        else:
            return self._exam_teacher_text(exam, include_analysis)

    def export_exam_result(
        self,
        result: ExamResult,
        exam: Optional[ExamPaper] = None,
        format: str = "text",
        include_question_detail: bool = True,
    ) -> str:
        if format == "markdown":
            return self._result_markdown(result, exam, include_question_detail)
        elif format == "html":
            return self._result_html(result, exam, include_question_detail)
        else:
            return self._result_text(result, exam, include_question_detail)

    def export_wrong_book(
        self,
        wrong_questions: List[WrongQuestion],
        title: str = "错题本",
        format: str = "text",
        student_id: Optional[str] = None,
    ) -> str:
        if format == "markdown":
            return self._wrong_book_markdown(wrong_questions, title, student_id)
        elif format == "html":
            return self._wrong_book_html(wrong_questions, title, student_id)
        else:
            return self._wrong_book_text(wrong_questions, title, student_id)

    def export_practice_report(
        self,
        report: Dict[str, Any],
        format: str = "text",
    ) -> str:
        if format == "markdown":
            return self._report_markdown(report)
        elif format == "html":
            return self._report_html(report)
        else:
            return self._report_text(report)

    def _exam_student_text(self, exam: ExamPaper, include_header: bool) -> str:
        lines = []
        if include_header:
            lines.append("=" * 60)
            lines.append(exam.title)
            lines.append("=" * 60)
            info = []
            if exam.grade:
                info.append(f"年级：{exam.grade}")
            if exam.subject:
                info.append(f"科目：{exam.subject}")
            info.append(f"总分：{exam.total_score}分")
            info.append(f"题数：{len(exam.questions)}题")
            if exam.duration_minutes:
                info.append(f"时长：{exam.duration_minutes}分钟")
            lines.append(" | ".join(info))
            lines.append("")
            lines.append(f"姓名：__________  学号：__________  得分：__________")
            lines.append("")

        q_num = 1
        for q_type in QuestionType:
            qs = exam.get_questions_by_type(q_type)
            if not qs:
                continue
            section_score = sum(q.score for q in qs)
            lines.append(f"【{q_type.display_name}】（共{len(qs)}题，{section_score}分）")
            lines.append("")
            for q in qs:
                lines.append(f"{q_num}. （{q.score}分）{q.content}")
                if q.options:
                    for opt in q.options:
                        lines.append(f"{self.indent}{opt.get('key', '')}. {opt.get('value', '')}")
                if q.question_type == QuestionType.FILL_BLANK:
                    lines.append(f"{self.indent}答案区：{'_' * 40}")
                elif q.question_type == QuestionType.TRUE_FALSE:
                    lines.append(f"{self.indent}（    ）")
                elif q.question_type == QuestionType.SHORT_ANSWER:
                    lines.append(f"{self.indent}答题区：")
                    for _ in range(5):
                        lines.append(f"{self.indent}{'_' * 60}")
                lines.append("")
                q_num += 1

        return "\n".join(lines)

    def _exam_teacher_text(self, exam: ExamPaper, include_analysis: bool) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(exam.title + " （教师答案版）")
        lines.append("=" * 60)
        lines.append(f"总分：{exam.total_score}分  |  题数：{len(exam.questions)}题")
        lines.append("")

        q_num = 1
        for q_type in QuestionType:
            qs = exam.get_questions_by_type(q_type)
            if not qs:
                continue
            section_score = sum(q.score for q in qs)
            lines.append(f"【{q_type.display_name}】（共{len(qs)}题，{section_score}分）")
            lines.append("-" * 50)
            for q in qs:
                lines.append(f"{q_num}. （{q.score}分）{q.content}")
                if q.options:
                    for opt in q.options:
                        mark = " ✓" if str(opt.get("key", "")).lower() in str(q.answer).lower() else ""
                        lines.append(f"{self.indent}{opt.get('key', '')}. {opt.get('value', '')}{mark}")
                lines.append(f"{self.indent}【正确答案】{q.answer}")
                if include_analysis and q.analysis:
                    lines.append(f"{self.indent}【解析】{q.analysis}")
                lines.append("")
                q_num += 1

        return "\n".join(lines)

    def _exam_student_markdown(self, exam: ExamPaper, include_header: bool) -> str:
        lines = []
        if include_header:
            lines.append(f"# {exam.title}")
            lines.append("")
            info_parts = []
            if exam.grade:
                info_parts.append(f"**年级：** {exam.grade}")
            if exam.subject:
                info_parts.append(f"**科目：** {exam.subject}")
            info_parts.append(f"**总分：** {exam.total_score}分")
            info_parts.append(f"**题数：** {len(exam.questions)}题")
            if exam.duration_minutes:
                info_parts.append(f"**时长：** {exam.duration_minutes}分钟")
            lines.append(" | ".join(info_parts))
            lines.append("")
            lines.append("| 姓名 | 学号 | 得分 |")
            lines.append("|------|------|------|")
            lines.append("|      |      |      |")
            lines.append("")

        q_num = 1
        for q_type in QuestionType:
            qs = exam.get_questions_by_type(q_type)
            if not qs:
                continue
            section_score = sum(q.score for q in qs)
            lines.append(f"## {q_type.display_name}（共{len(qs)}题，{section_score}分）")
            lines.append("")
            for q in qs:
                lines.append(f"### {q_num}. （{q.score}分）{q.content}")
                if q.options:
                    lines.append("")
                    for opt in q.options:
                        lines.append(f"- **{opt.get('key', '')}**. {opt.get('value', '')}")
                if q.question_type == QuestionType.FILL_BLANK:
                    lines.append("")
                    lines.append("> 答案区：" + "_" * 20)
                elif q.question_type == QuestionType.TRUE_FALSE:
                    lines.append("")
                    lines.append("> (    )")
                elif q.question_type == QuestionType.SHORT_ANSWER:
                    lines.append("")
                    lines.append("> 答题区：")
                    lines.append(">")
                    blank_line = "> " + "_" * 30
                    lines.append(blank_line)
                    lines.append(blank_line)
                    lines.append(blank_line)
                lines.append("")
                q_num += 1

        return "\n".join(lines)

    def _exam_teacher_markdown(self, exam: ExamPaper, include_analysis: bool) -> str:
        lines = []
        lines.append(f"# {exam.title} （教师答案版）")
        lines.append("")
        lines.append(f"**总分：** {exam.total_score}分 | **题数：** {len(exam.questions)}题")
        lines.append("")

        q_num = 1
        for q_type in QuestionType:
            qs = exam.get_questions_by_type(q_type)
            if not qs:
                continue
            section_score = sum(q.score for q in qs)
            lines.append(f"## {q_type.display_name}（共{len(qs)}题，{section_score}分）")
            lines.append("")
            for q in qs:
                lines.append(f"### {q_num}. （{q.score}分）{q.content}")
                if q.options:
                    lines.append("")
                    for opt in q.options:
                        key = str(opt.get("key", "")).lower()
                        ans = str(q.answer).lower()
                        mark = " ✅" if key in ans else ""
                        lines.append(f"- **{opt.get('key', '')}**. {opt.get('value', '')}{mark}")
                lines.append("")
                lines.append(f"**正确答案：** {q.answer}")
                if include_analysis and q.analysis:
                    lines.append("")
                    lines.append(f"**解析：** {q.analysis}")
                lines.append("")
                lines.append("---")
                lines.append("")
                q_num += 1

        return "\n".join(lines)

    def _exam_student_html(self, exam: ExamPaper, include_header: bool) -> str:
        html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">']
        html.append(f'<title>{exam.title}</title>')
        html.append('<style>')
        html.append('body{font-family:"Microsoft YaHei",sans-serif;padding:40px;max-width:900px;margin:0 auto;}')
        html.append('h1{text-align:center;border-bottom:3px solid #333;padding-bottom:15px;}')
        html.append('.info{display:flex;justify-content:space-between;margin:20px 0;font-size:14px;color:#555;}')
        html.append('.student-row{border:1px solid #999;padding:15px;margin:25px 0;display:flex;gap:30px;}')
        html.append('.student-row div{flex:1;}')
        html.append('h2{background:#f5f5f5;padding:10px 15px;margin-top:30px;border-left:4px solid #2c5282;}')
        html.append('.question{margin:20px 0;padding-left:10px;}')
        html.append('.options{margin:10px 0 10px 30px;}')
        html.append('.option{margin:5px 0;}')
        html.append('.answer-area{border:1px dashed #999;padding:15px;margin:10px 0 10px 30px;min-height:60px;}')
        html.append('</style></head><body>')

        if include_header:
            html.append(f'<h1>{exam.title}</h1>')
            infos = []
            if exam.grade:
                infos.append(f"年级：{exam.grade}")
            if exam.subject:
                infos.append(f"科目：{exam.subject}")
            infos.append(f"总分：{exam.total_score}分")
            infos.append(f"题数：{len(exam.questions)}题")
            if exam.duration_minutes:
                infos.append(f"时长：{exam.duration_minutes}分钟")
            html.append('<div class="info">' + " | ".join(infos) + "</div>")
            html.append('<div class="student-row"><div>姓名：_______________</div><div>学号：_______________</div><div>得分：_______________</div></div>')

        q_num = 1
        for q_type in QuestionType:
            qs = exam.get_questions_by_type(q_type)
            if not qs:
                continue
            section_score = sum(q.score for q in qs)
            html.append(f'<h2>{q_type.display_name}（共{len(qs)}题，{section_score}分）</h2>')
            for q in qs:
                html.append(f'<div class="question"><p><b>{q_num}.</b> （{q.score}分）{q.content}</p>')
                if q.options:
                    html.append('<div class="options">')
                    for opt in q.options:
                        html.append(f'<div class="option">{opt.get("key","")}. {opt.get("value","")}</div>')
                    html.append('</div>')
                if q.question_type in [QuestionType.FILL_BLANK, QuestionType.TRUE_FALSE, QuestionType.SHORT_ANSWER]:
                    hint = "请填空：" if q.question_type == QuestionType.FILL_BLANK else ("请打√或×：" if q.question_type == QuestionType.TRUE_FALSE else "请作答：")
                    html.append(f'<div class="answer-area"><i style="color:#888;">{hint}</i><br/><br/></div>')
                html.append('</div>')
                q_num += 1

        html.append('</body></html>')
        return "\n".join(html)

    def _exam_teacher_html(self, exam: ExamPaper, include_analysis: bool) -> str:
        html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">']
        html.append(f'<title>{exam.title} - 教师版</title>')
        html.append('<style>')
        html.append('body{font-family:"Microsoft YaHei",sans-serif;padding:40px;max-width:900px;margin:0 auto;}')
        html.append('h1{text-align:center;border-bottom:3px solid #c53030;padding-bottom:15px;color:#c53030;}')
        html.append('h2{background:#fff5f5;padding:10px 15px;margin-top:30px;border-left:4px solid #c53030;}')
        html.append('.question{margin:20px 0;padding-left:10px;border-bottom:1px solid #eee;padding-bottom:15px;}')
        html.append('.options{margin:10px 0 10px 30px;}')
        html.append('.option{margin:5px 0;}')
        html.append('.correct{color:#38a169;font-weight:bold;}')
        html.append('.answer-box{background:#f0fff4;border:1px solid #9ae6b4;padding:10px 15px;margin:10px 0;border-radius:4px;}')
        html.append('.analysis-box{background:#ebf8ff;border:1px solid #90cdf4;padding:10px 15px;margin:10px 0;border-radius:4px;}')
        html.append('</style></head><body>')
        html.append(f'<h1>{exam.title} （教师答案版）</h1>')
        html.append(f'<p style="text-align:center;">总分：{exam.total_score}分 | 题数：{len(exam.questions)}题</p>')

        q_num = 1
        for q_type in QuestionType:
            qs = exam.get_questions_by_type(q_type)
            if not qs:
                continue
            section_score = sum(q.score for q in qs)
            html.append(f'<h2>{q_type.display_name}（共{len(qs)}题，{section_score}分）</h2>')
            for q in qs:
                html.append(f'<div class="question"><p><b>{q_num}.</b> （{q.score}分）{q.content}</p>')
                if q.options:
                    html.append('<div class="options">')
                    for opt in q.options:
                        key = str(opt.get("key", "")).lower()
                        ans = str(q.answer).lower()
                        cls = ' class="correct"' if key in ans else ""
                        mark = " ✅" if key in ans else ""
                        html.append(f'<div{cls}>{opt.get("key","")}. {opt.get("value","")}{mark}</div>')
                    html.append('</div>')
                html.append(f'<div class="answer-box"><b>正确答案：</b>{q.answer}</div>')
                if include_analysis and q.analysis:
                    html.append(f'<div class="analysis-box"><b>解析：</b>{q.analysis}</div>')
                html.append('</div>')
                q_num += 1

        html.append('</body></html>')
        return "\n".join(html)

    def _result_text(self, result: ExamResult, exam: Optional[ExamPaper], include_detail: bool) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("练习批改结果报告")
        lines.append("=" * 60)
        lines.append(f"学生ID：{result.student_id}")
        lines.append(f"试卷ID：{result.exam_id}")
        lines.append(f"得分：{result.total_score} / {result.max_score} （{result.percentage}%）")
        lines.append(f"正确：{result.correct_count}题  |  错误：{result.wrong_count}题  |  总计：{len(result.question_results)}题")
        if result.time_spent_seconds:
            lines.append(f"用时：{result.time_spent_seconds // 60}分{result.time_spent_seconds % 60}秒")
        if result.completed_at:
            lines.append(f"完成时间：{result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        level = "优秀"
        if result.percentage < 60:
            level = "不及格"
        elif result.percentage < 70:
            level = "及格"
        elif result.percentage < 80:
            level = "良好"
        lines.append(f"等级评定：{level}")
        lines.append("")

        if include_detail:
            lines.append("-" * 50)
            lines.append("各题详情：")
            lines.append("-" * 50)
            qmap = {q.id: q for q in exam.questions} if exam else {}
            for idx, qr in enumerate(result.question_results, 1):
                q = qmap.get(qr.question_id)
                status = "✓ 正确" if qr.is_correct else "✗ 错误"
                lines.append(f"{idx}. [{status}] 得分{qr.score}/{qr.max_score}分  (ID:{qr.question_id})")
                if q:
                    lines.append(f"{self.indent}题目：{q.content[:80]}{'...' if len(q.content) > 80 else ''}")
                if not qr.is_correct:
                    lines.append(f"{self.indent}你的答案：{qr.student_answer}")
                    lines.append(f"{self.indent}正确答案：{qr.correct_answer}")
                    if qr.feedback:
                        lines.append(f"{self.indent}反馈：{qr.feedback}")
                lines.append("")

        if result.wrong_count > 0:
            lines.append("-" * 50)
            lines.append(f"错题列表（共{result.wrong_count}题）：")
            lines.append("-" * 50)
            for idx, qr in enumerate(result.wrong_questions, 1):
                lines.append(f"{idx}. ID:{qr.question_id}  得分{qr.score}/{qr.max_score}")

        return "\n".join(lines)

    def _result_markdown(self, result: ExamResult, exam: Optional[ExamPaper], include_detail: bool) -> str:
        lines = []
        lines.append("# 练习批改结果报告")
        lines.append("")
        lines.append("| 项目 | 内容 |")
        lines.append("|------|------|")
        lines.append(f"| 学生ID | {result.student_id} |")
        lines.append(f"| 试卷ID | {result.exam_id} |")
        lines.append(f"| **得分** | **{result.total_score} / {result.max_score}**（{result.percentage}%） |")
        lines.append(f"| 正确/错误/总数 | {result.correct_count} / {result.wrong_count} / {len(result.question_results)} |")
        if result.time_spent_seconds:
            m, s = divmod(result.time_spent_seconds, 60)
            lines.append(f"| 用时 | {m}分{s}秒 |")
        if result.completed_at:
            lines.append(f"| 完成时间 | {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')} |")
        level = "优秀" if result.percentage >= 90 else ("良好" if result.percentage >= 80 else ("及格" if result.percentage >= 60 else "不及格"))
        lines.append(f"| **等级** | **{level}** |")
        lines.append("")

        if include_detail:
            lines.append("## 各题详情")
            lines.append("")
            qmap = {q.id: q for q in exam.questions} if exam else {}
            for idx, qr in enumerate(result.question_results, 1):
                q = qmap.get(qr.question_id)
                icon = "✅" if qr.is_correct else "❌"
                lines.append(f"### {idx}. {icon} 得分 {qr.score}/{qr.max_score} 分")
                if q:
                    lines.append(f"**题目：** {q.content}")
                    if q.options:
                        lines.append("")
                        for opt in q.options:
                            lines.append(f"- {opt.get('key','')}. {opt.get('value','')}")
                lines.append("")
                lines.append(f"**你的答案：** {qr.student_answer if qr.student_answer is not None else '(未作答)'}")
                lines.append(f"**正确答案：** {qr.correct_answer}")
                if qr.feedback:
                    lines.append(f"**反馈：** {qr.feedback}")
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def _result_html(self, result: ExamResult, exam: Optional[ExamPaper], include_detail: bool) -> str:
        html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">']
        html.append('<title>批改结果报告</title>')
        html.append('<style>')
        html.append('body{font-family:"Microsoft YaHei",sans-serif;padding:40px;max-width:900px;margin:0 auto;}')
        html.append('h1{text-align:center;color:#2c5282;}')
        html.append('.summary{background:#f7fafc;border:2px solid #4299e1;padding:25px;border-radius:10px;margin:20px 0;}')
        html.append('.summary-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px dashed #cbd5e0;}')
        html.append('.score-big{text-align:center;font-size:48px;font-weight:bold;color:#2c5282;margin:20px 0;}')
        html.append('.level-badge{display:inline-block;padding:6px 20px;border-radius:20px;color:white;font-weight:bold;}')
        html.append('.level-excellent{background:#38a169;}.level-good{background:#4299e1;}.level-pass{background:#ed8936;}.level-fail{background:#e53e3e;}')
        html.append('.q-card{border:1px solid #e2e8f0;padding:20px;margin:15px 0;border-radius:8px;}')
        html.append('.q-correct{border-left:5px solid #38a169;background:#f0fff4;}')
        html.append('.q-wrong{border-left:5px solid #e53e3e;background:#fff5f5;}')
        html.append('.feedback{margin-top:10px;padding:10px;background:#fffaf0;border-radius:4px;color:#744210;}')
        html.append('</style></head><body>')
        html.append('<h1>📋 练习批改结果报告</h1>')

        level = "优秀"
        cls = "level-excellent"
        if result.percentage < 60:
            level, cls = "不及格", "level-fail"
        elif result.percentage < 70:
            level, cls = "及格", "level-pass"
        elif result.percentage < 80:
            level, cls = "良好", "level-good"

        html.append('<div class="summary">')
        html.append(f'<div class="score-big">{result.percentage}%<br/><span style="font-size:20px;color:#718096;">{result.total_score} / {result.max_score} 分</span></div>')
        html.append(f'<div style="text-align:center;"><span class="level-badge {cls}">{level}</span></div>')
        html.append('<div class="summary-row"><span>学生ID</span><b>' + result.student_id + '</b></div>')
        html.append('<div class="summary-row"><span>正确 / 错误 / 总数</span><b>' + f'{result.correct_count} / {result.wrong_count} / {len(result.question_results)}' + '</b></div>')
        if result.time_spent_seconds:
            m, s = divmod(result.time_spent_seconds, 60)
            html.append(f'<div class="summary-row"><span>用时</span><b>{m}分{s}秒</b></div>')
        if result.completed_at:
            html.append(f'<div class="summary-row"><span>完成时间</span><b>{result.completed_at.strftime("%Y-%m-%d %H:%M:%S")}</b></div>')
        html.append('</div>')

        if include_detail:
            html.append('<h2>各题详情</h2>')
            qmap = {q.id: q for q in exam.questions} if exam else {}
            for idx, qr in enumerate(result.question_results, 1):
                q = qmap.get(qr.question_id)
                card_cls = "q-correct" if qr.is_correct else "q-wrong"
                icon = "✅" if qr.is_correct else "❌"
                html.append(f'<div class="q-card {card_cls}">')
                html.append(f'<h3>{idx}. {icon} 得分 <b>{qr.score}/{qr.max_score}</b> 分  <small style="color:#a0aec0;">(ID:{qr.question_id})</small></h3>')
                if q:
                    html.append(f'<p style="font-size:16px;">{q.content}</p>')
                    if q.options:
                        for opt in q.options:
                            html.append(f'<div style="margin:5px 0 5px 20px;">{opt.get("key","")}. {opt.get("value","")}</div>')
                html.append(f'<div style="margin-top:12px;"><span style="color:#718096;">你的答案：</span><b>{qr.student_answer if qr.student_answer is not None else "(未作答)"}</b></div>')
                if not qr.is_correct:
                    html.append(f'<div><span style="color:#718096;">正确答案：</span><b style="color:#38a169;">{qr.correct_answer}</b></div>')
                if qr.feedback:
                    html.append(f'<div class="feedback">💡 {qr.feedback}</div>')
                html.append('</div>')

        html.append('</body></html>')
        return "\n".join(html)

    def _wrong_book_text(self, wrong_questions: List[WrongQuestion], title: str, student_id: Optional[str]) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(title)
        if student_id:
            lines.append(f"（学生：{student_id}）")
        lines.append("=" * 60)
        lines.append(f"错题总数：{len(wrong_questions)}题")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        sorted_wq = sorted(wrong_questions, key=lambda x: x.wrong_count, reverse=True)
        for idx, wq in enumerate(sorted_wq, 1):
            q = wq.question
            lines.append(f"【第{idx}题】ID:{wq.question_id}  错误次数：{wq.wrong_count}次")
            if q:
                lines.append(f"类型：{q.question_type.display_name}  难度：{q.difficulty.display_name}  分值：{q.score}分")
                if q.knowledge_points:
                    lines.append(f"知识点：{'、'.join(q.knowledge_points)}")
                lines.append(f"题目：{q.content}")
                if q.options:
                    for opt in q.options:
                        lines.append(f"{self.indent}{opt.get('key','')}. {opt.get('value','')}")
                lines.append(f"正确答案：{q.answer}")
                if q.analysis:
                    lines.append(f"解析：{q.analysis}")
            if wq.wrong_answers:
                recent = wq.wrong_answers[-3:]
                lines.append(f"最近错误答案：{recent}")
            lines.append("-" * 50)
            lines.append("")

        return "\n".join(lines)

    def _wrong_book_markdown(self, wrong_questions: List[WrongQuestion], title: str, student_id: Optional[str]) -> str:
        lines = []
        lines.append(f"# 📕 {title}")
        lines.append("")
        if student_id:
            lines.append(f"**学生：** {student_id}")
        lines.append(f"**错题总数：** {len(wrong_questions)}题")
        lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        sorted_wq = sorted(wrong_questions, key=lambda x: x.wrong_count, reverse=True)
        for idx, wq in enumerate(sorted_wq, 1):
            q = wq.question
            badge = "🔥" * min(wq.wrong_count, 5)
            lines.append(f"## {idx}. {badge} 错误{wq.wrong_count}次")
            lines.append(f"*ID:{wq.question_id}*")
            lines.append("")
            if q:
                info_parts = [f"**{q.question_type.display_name}**", f"难度：{q.difficulty.display_name}", f"{q.score}分"]
                lines.append(" | ".join(info_parts))
                if q.knowledge_points:
                    lines.append(f"**知识点：** {'、'.join(q.knowledge_points)}")
                lines.append("")
                lines.append(f"**题目：** {q.content}")
                lines.append("")
                if q.options:
                    for opt in q.options:
                        lines.append(f"- {opt.get('key','')}. {opt.get('value','')}")
                    lines.append("")
                lines.append(f"✅ **正确答案：** {q.answer}")
                if q.analysis:
                    lines.append("")
                    lines.append(f"📖 **解析：** {q.analysis}")
            if wq.wrong_answers:
                lines.append("")
                lines.append(f"❌ **最近错误答案：** {', '.join(map(str, wq.wrong_answers[-3:]))}")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _wrong_book_html(self, wrong_questions: List[WrongQuestion], title: str, student_id: Optional[str]) -> str:
        html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">']
        html.append(f'<title>{title}</title>')
        html.append('<style>')
        html.append('body{font-family:"Microsoft YaHei",sans-serif;padding:40px;max-width:900px;margin:0 auto;background:#fffaf0;}')
        html.append('h1{text-align:center;color:#742a2a;border-bottom:3px solid #feb2b2;padding-bottom:15px;}')
        html.append('.wq-card{background:white;border:1px solid #fed7d7;padding:20px;margin:15px 0;border-radius:10px;box-shadow:2px 2px 8px rgba(0,0,0,0.05);}')
        html.append('.fire{color:#e53e3e;font-size:18px;}')
        html.append('.meta{color:#718096;font-size:14px;margin-bottom:10px;}')
        html.append('.answer{background:#f0fff4;border-left:4px solid #38a169;padding:10px 15px;margin:10px 0;border-radius:4px;}')
        html.append('.analysis{background:#ebf8ff;border-left:4px solid #4299e1;padding:10px 15px;margin:10px 0;border-radius:4px;}')
        html.append('</style></head><body>')
        html.append(f'<h1>📕 {title}</h1>')
        if student_id:
            html.append(f'<p style="text-align:center;">学生：{student_id}</p>')
        html.append(f'<p style="text-align:center;color:#718096;">共 {len(wrong_questions)} 道错题 | 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')

        sorted_wq = sorted(wrong_questions, key=lambda x: x.wrong_count, reverse=True)
        for idx, wq in enumerate(sorted_wq, 1):
            q = wq.question
            fires = "🔥" * min(wq.wrong_count, 5)
            html.append(f'<div class="wq-card">')
            html.append(f'<h3 style="margin-top:0;">{idx}. {fires} 错误 <b style="color:#e53e3e;">{wq.wrong_count}</b> 次 <small style="color:#a0aec0;">ID:{wq.question_id}</small></h3>')
            if q:
                meta_parts = [q.question_type.display_name, f"难度：{q.difficulty.display_name}", f"{q.score}分"]
                if q.knowledge_points:
                    meta_parts.append("知识点：" + "、".join(q.knowledge_points))
                html.append(f'<div class="meta">{" | ".join(meta_parts)}</div>')
                html.append(f'<p style="font-size:16px;line-height:1.6;">{q.content}</p>')
                if q.options:
                    for opt in q.options:
                        html.append(f'<div style="margin:5px 0 5px 20px;">{opt.get("key","")}. {opt.get("value","")}</div>')
                html.append(f'<div class="answer"><b>✅ 正确答案：</b>{q.answer}</div>')
                if q.analysis:
                    html.append(f'<div class="analysis"><b>📖 解析：</b>{q.analysis}</div>')
            if wq.wrong_answers:
                html.append(f'<div style="color:#c53030;margin-top:10px;"><b>❌ 最近错误：</b>{"、".join(map(str, wq.wrong_answers[-3:]))}</div>')
            html.append('</div>')

        html.append('</body></html>')
        return "\n".join(html)

    def _report_text(self, report: Dict[str, Any]) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("学习综合分析报告")
        lines.append("=" * 60)
        if "error" in report:
            lines.append(report["error"])
            return "\n".join(lines)

        lines.append(f"学生ID：{report.get('student_id', 'N/A')}")
        lines.append(f"练习次数：{report.get('practice_count', 0)}次")
        lines.append("")

        summary = report.get("summary", {})
        lines.append("【总体表现】")
        lines.append(f"{self.indent}答题总数：{summary.get('total_questions', 0)}题")
        lines.append(f"{self.indent}正确率：{summary.get('overall_accuracy', 0)}%")
        lines.append(f"{self.indent}得分率：{summary.get('overall_score_rate', 0)}%")
        lines.append(f"{self.indent}总得分：{summary.get('total_earned_score', 0)} / {summary.get('total_max_score', 0)}分")
        lines.append("")

        hc = report.get("history_comparison", {})
        if "error" not in hc:
            lines.append("【历史趋势】")
            lines.append(f"{self.indent}平均分：{hc.get('average_percentage', 0)}%")
            lines.append(f"{self.indent}近期平均：{hc.get('recent_average', 0)}%")
            lines.append(f"{self.indent}趋势：{hc.get('trend', 'N/A')}")
            best = hc.get("best", {})
            worst = hc.get("worst", {})
            lines.append(f"{self.indent}最佳：{best.get('percentage', 0)}% ({best.get('date', '')})")
            lines.append(f"{self.indent}最差：{worst.get('percentage', 0)}% ({worst.get('date', '')})")
            stab = hc.get("stability", {})
            lines.append(f"{self.indent}稳定性：{stab.get('level', 'N/A')}")
            lines.append("")

        weak = report.get("weak_knowledge_points", [])
        if weak:
            lines.append("【薄弱知识点】")
            for w in weak:
                lines.append(f"{self.indent}- {w.get('knowledge_point','')}: 掌握度{w.get('mastery_level',0)}%, 正确率{w.get('accuracy',0)}%")
            lines.append("")

        type_analysis = report.get("question_type_analysis", {})
        if type_analysis:
            lines.append("【各题型表现】")
            for t, s in type_analysis.items():
                lines.append(f"{self.indent}- {t}: {s.get('correct',0)}/{s.get('total',0)}题, 正确率{s.get('accuracy',0)}%")
            lines.append("")

        wb = report.get("wrong_book_summary", {})
        if wb:
            lines.append(f"【错题统计】累计{wb.get('total_wrong',0)}道错题")
            freq = wb.get("frequently_wrong", [])
            if freq:
                lines.append(f"{self.indent}高频错题（错≥2次）：")
                for fw in freq[:5]:
                    lines.append(f"{self.indent}{self.indent}- ID:{fw.get('question_id','')} 错{fw.get('wrong_count',0)}次")
            lines.append("")

        suggestions = report.get("suggestions", [])
        if suggestions:
            lines.append("【学习建议】")
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{self.indent}{i}. {s}")

        return "\n".join(lines)

    def _report_markdown(self, report: Dict[str, Any]) -> str:
        lines = []
        lines.append("# 📊 学习综合分析报告")
        lines.append("")
        if "error" in report:
            lines.append(f"> {report['error']}")
            return "\n".join(lines)

        lines.append(f"**学生ID：** {report.get('student_id', 'N/A')}  ")
        lines.append(f"**练习次数：** {report.get('practice_count', 0)} 次")
        lines.append("")

        summary = report.get("summary", {})
        lines.append("## 📈 总体表现")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 答题总数 | {summary.get('total_questions', 0)} 题 |")
        lines.append(f"| 正确 / 错误 | {summary.get('total_correct', 0)} / {summary.get('total_wrong', 0)} |")
        lines.append(f"| **正确率** | **{summary.get('overall_accuracy', 0)}%** |")
        lines.append(f"| **得分率** | **{summary.get('overall_score_rate', 0)}%** |")
        lines.append(f"| 总得分 | {summary.get('total_earned_score', 0)} / {summary.get('total_max_score', 0)} 分 |")
        lines.append("")

        hc = report.get("history_comparison", {})
        if "error" not in hc:
            lines.append("## 📉 历史趋势")
            lines.append("")
            lines.append(f"- **平均分：** {hc.get('average_percentage', 0)}%")
            lines.append(f"- **近期平均（近{len(hc.get('history', [])[-5:])}次）：** {hc.get('recent_average', 0)}%")
            trend_icon = "📈" if "进步" in hc.get('trend','') or "提升" in hc.get('trend','') else ("📉" if "退" in hc.get('trend','') else "➡️")
            lines.append(f"- **趋势：** {trend_icon} {hc.get('trend', 'N/A')}")
            best = hc.get("best", {})
            worst = hc.get("worst", {})
            lines.append(f"- 🏆 **最佳成绩：** {best.get('percentage', 0)}% （{best.get('date', '')}）")
            lines.append(f"- ⚠️ **最差成绩：** {worst.get('percentage', 0)}% （{worst.get('date', '')}）")
            stab = hc.get("stability", {})
            lines.append(f"- 🎯 **稳定性：** {stab.get('level', 'N/A')}")
            lines.append("")

        weak = report.get("weak_knowledge_points", [])
        if weak:
            lines.append("## ⚠️ 薄弱知识点")
            lines.append("")
            lines.append("| 知识点 | 题目数 | 掌握度 | 正确率 |")
            lines.append("|--------|--------|--------|--------|")
            for w in weak:
                lines.append(f"| {w.get('knowledge_point','')} | {w.get('total_questions',0)}题 | **{w.get('mastery_level',0)}%** | {w.get('accuracy',0)}% |")
            lines.append("")

        suggestions = report.get("suggestions", [])
        if suggestions:
            lines.append("## 💡 学习建议")
            lines.append("")
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{i}. {s}")
            lines.append("")

        return "\n".join(lines)

    def _report_html(self, report: Dict[str, Any]) -> str:
        html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">']
        html.append('<title>学习综合分析报告</title>')
        html.append('<style>')
        html.append('body{font-family:"Microsoft YaHei",sans-serif;padding:40px;max-width:960px;margin:0 auto;background:#f7fafc;}')
        html.append('h1{text-align:center;color:#2c5282;margin-bottom:30px;}')
        html.append('.card{background:white;border-radius:12px;padding:25px;margin:20px 0;box-shadow:0 2px 10px rgba(0,0,0,0.08);}')
        html.append('.card h2{margin-top:0;color:#2d3748;border-bottom:2px solid #e2e8f0;padding-bottom:10px;}')
        html.append('.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;}')
        html.append('.stat-item{background:#f7fafc;padding:15px;border-radius:8px;text-align:center;}')
        html.append('.stat-val{font-size:28px;font-weight:bold;color:#2c5282;}')
        html.append('.stat-label{color:#718096;font-size:14px;margin-top:5px;}')
        html.append('table{width:100%;border-collapse:collapse;margin:15px 0;}')
        html.append('th,td{padding:12px;text-align:left;border-bottom:1px solid #e2e8f0;}')
        html.append('th{background:#f7fafc;font-weight:600;}')
        html.append('.suggestion{padding:10px 15px;background:#fefcbf;border-left:4px solid #d69e2e;margin:8px 0;border-radius:4px;}')
        html.append('</style></head><body>')
        html.append('<h1>📊 学习综合分析报告</h1>')

        if "error" in report:
            html.append(f'<div class="card"><p style="color:#e53e3e;font-size:18px;">{report["error"]}</p></div></body></html>')
            return "\n".join(html)

        html.append(f'<div class="card"><p style="text-align:center;color:#4a5568;font-size:16px;">学生：<b>{report.get("student_id","N/A")}</b> | 练习次数：<b>{report.get("practice_count",0)}</b> 次</p></div>')

        summary = report.get("summary", {})
        html.append('<div class="card"><h2>📈 总体表现</h2>')
        html.append('<div class="stat-grid">')
        html.append(f'<div class="stat-item"><div class="stat-val">{summary.get("total_questions",0)}</div><div class="stat-label">答题总数</div></div>')
        html.append(f'<div class="stat-item"><div class="stat-val" style="color:#38a169;">{summary.get("overall_accuracy",0)}%</div><div class="stat-label">正确率</div></div>')
        html.append(f'<div class="stat-item"><div class="stat-val" style="color:#4299e1;">{summary.get("overall_score_rate",0)}%</div><div class="stat-label">得分率</div></div>')
        html.append(f'<div class="stat-item"><div class="stat-val">{summary.get("total_earned_score",0)}/{summary.get("total_max_score",0)}</div><div class="stat-label">总得分/满分</div></div>')
        html.append('</div></div>')

        hc = report.get("history_comparison", {})
        if "error" not in hc:
            html.append('<div class="card"><h2>📉 历史趋势</h2>')
            html.append('<div class="stat-grid">')
            html.append(f'<div class="stat-item"><div class="stat-val">{hc.get("average_percentage",0)}%</div><div class="stat-label">历史平均分</div></div>')
            html.append(f'<div class="stat-item"><div class="stat-val" style="color:#4299e1;">{hc.get("recent_average",0)}%</div><div class="stat-label">近期平均</div></div>')
            trend = hc.get("trend","")
            trend_color = "#38a169" if ("进步" in trend or "提升" in trend) else ("#e53e3e" if "退" in trend else "#a0aec0")
            html.append(f'<div class="stat-item"><div class="stat-val" style="color:{trend_color};font-size:20px;">{trend}</div><div class="stat-label">学习趋势</div></div>')
            best = hc.get("best", {})
            html.append(f'<div class="stat-item"><div class="stat-val" style="color:#d69e2e;">🏆 {best.get("percentage",0)}%</div><div class="stat-label">最佳成绩</div></div>')
            html.append('</div></div>')

        weak = report.get("weak_knowledge_points", [])
        if weak:
            html.append('<div class="card"><h2>⚠️ 薄弱知识点（需重点加强）</h2>')
            html.append('<table><tr><th>知识点</th><th>题目数</th><th>掌握度</th><th>正确率</th></tr>')
            for w in weak:
                ml = w.get("mastery_level", 0)
                color = "#e53e3e" if ml < 40 else ("#ed8936" if ml < 60 else "#d69e2e")
                html.append(f'<tr><td>{w.get("knowledge_point","")}</td><td>{w.get("total_questions",0)}题</td><td style="color:{color};font-weight:bold;">{ml}%</td><td>{w.get("accuracy",0)}%</td></tr>')
            html.append('</table></div>')

        suggestions = report.get("suggestions", [])
        if suggestions:
            html.append('<div class="card"><h2>💡 学习建议</h2>')
            for s in suggestions:
                html.append(f'<div class="suggestion">📌 {s}</div>')
            html.append('</div>')

        html.append('</body></html>')
        return "\n".join(html)

    def save_to_file(self, content: str, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
