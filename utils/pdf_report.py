"""PDF report generation - Shows ALL issues."""

import re
from datetime import datetime

from fpdf import FPDF


def clean_text(text):
    """Remove ALL special characters for PDF."""
    if not text:
        return ""
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"[\u2600-\u26FF]", "", text)
    text = re.sub(r"[#*`\[\]\(\)]", "", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.replace(chr(8226), "-").replace("•", "-").replace("○", "-")
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.strip()


class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(41, 128, 185)
        self.rect(0, 0, 210, 25, "F")
        self.set_font("helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 8)
        self.cell(0, 10, "Code Review Report", new_x="LMARGIN", new_y="NEXT")
        self.ln(15)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(
            0,
            8,
            f'Page {self.page_no()} | Generated {datetime.now().strftime("%Y-%m-%d")}',
            align="C",
        )

    def section(self, title):
        self.ln(5)
        self.set_fill_color(236, 240, 241)
        self.set_font("helvetica", "B", 11)
        self.set_text_color(41, 128, 185)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def score_box(self, score, label):
        if score >= 7:
            r, g, b = 39, 174, 96
        elif score >= 5:
            r, g, b = 241, 196, 15
        else:
            r, g, b = 231, 76, 60
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font("helvetica", "B", 14)
        self.cell(
            0, 12, f"  {label}: {score}/10", fill=True, new_x="LMARGIN", new_y="NEXT"
        )
        self.set_text_color(0, 0, 0)
        self.ln(5)


def generate_review_pdf(data):
    """Generate PDF with ALL issue details."""
    pr_title = clean_text(data.get("pr_title", "Review"))
    pr_url = data.get("pr_url", "")
    overall = data.get("overall_score", 0)
    scores = data.get("scores", [])
    lint_results = data.get("lint_results", [])
    logic_results = data.get("logic_results", [])
    fix_suggestions = data.get("fix_suggestions", [])

    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(10, 30, 10)
    pdf.add_page()

    # Summary
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 6, f"PR: {pr_title}", new_x="LMARGIN", new_y="NEXT")
    if pr_url:
        url_clean = clean_text(pr_url)
        if len(url_clean) > 80:
            url_clean = url_clean[:80] + "..."
        pdf.cell(0, 6, f"URL: {url_clean}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Files: {len(scores)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Overall Score
    pdf.score_box(overall, "Overall Score")

    # Files Summary
    pdf.section("Files Summary")
    for s in scores:
        fname = clean_text(s.get("filename", ""))
        fscore = s.get("score", 7)

        status = "PASS" if fscore >= 7 else ("WARN" if fscore >= 5 else "FAIL")

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(25, 7, f"[{status}]", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(140, 7, fname, new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"{fscore}/10", new_x="LMARGIN", new_y="NEXT")

        # Count issues for this file
        fl = next(
            (r for r in lint_results if r.get("filename") == s.get("filename")), {}
        )
        fl_logic = next(
            (r for r in logic_results if r.get("filename") == s.get("filename")), {}
        )
        fl_fixes = next(
            (r for r in fix_suggestions if r.get("filename") == s.get("filename")), {}
        )

        lint_count = len(fl.get("lint_issues", []))
        fix_count = len(fl_fixes.get("fixes", []))

        if lint_count > 0 or fix_count > 0:
            pdf.set_font("helvetica", "", 8)
            pdf.set_text_color(150, 150, 150)
            details = []
            if lint_count > 0:
                details.append(f"{lint_count} lint")
            if fix_count > 0:
                details.append(f"{fix_count} fixes")
            pdf.cell(0, 5, f'  {", ".join(details)}', new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # Detailed File Analysis
    pdf.ln(5)
    pdf.section("DETAILED ISSUES")

    for s in scores:
        if pdf.get_y() > 200:
            pdf.add_page()

        fname = clean_text(s.get("filename", ""))
        fscore = s.get("score", 7)
        justification = clean_text(s.get("justification", ""))

        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, f"File: {fname}", new_x="LMARGIN", new_y="NEXT")

        status = "PASS" if fscore >= 7 else ("WARN" if fscore >= 5 else "FAIL")
        pdf.set_font("helvetica", "B", 11)
        if fscore >= 7:
            pdf.set_text_color(39, 174, 96)
        elif fscore >= 5:
            pdf.set_text_color(241, 196, 15)
        else:
            pdf.set_text_color(231, 76, 60)
        pdf.cell(0, 8, f"[{status}] Score: {fscore}/10", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        if justification:
            pdf.set_font("helvetica", "I", 9)
            pdf.cell(
                0, 6, f"Rating: {justification[:100]}", new_x="LMARGIN", new_y="NEXT"
            )
        pdf.ln(3)

        # LINT ISSUES
        fl = next(
            (r for r in lint_results if r.get("filename") == s.get("filename")), {}
        )
        lint_issues = fl.get("lint_issues", [])

        if lint_issues:
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(192, 57, 43)
            pdf.cell(
                0,
                7,
                f"LINT ISSUES ({len(lint_issues)}):",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_text_color(0, 0, 0)

            for issue in lint_issues:
                pdf.set_font("helvetica", "", 9)
                sev = issue.get("severity", "INFO")
                line = issue.get("line", "?")
                msg = clean_text(issue.get("message", ""))
                if len(msg) > 80:
                    msg = msg[:80] + "..."
                pdf.cell(
                    0, 5, f"  [{sev}] Line {line}: {msg}", new_x="LMARGIN", new_y="NEXT"
                )

                # Show suggestion if available
                suggestion = issue.get("suggestion", "")
                if suggestion:
                    pdf.set_font("helvetica", "I", 8)
                    pdf.set_text_color(100, 100, 100)
                    sug_clean = clean_text(suggestion)
                    if len(sug_clean) > 70:
                        sug_clean = sug_clean[:70] + "..."
                    pdf.cell(
                        0,
                        4,
                        f"    Suggestion: {sug_clean}",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # SECURITY/SECURITY REVIEW
        fl_logic = next(
            (r for r in logic_results if r.get("filename") == s.get("filename")), {}
        )
        logic_text = fl_logic.get("logic_review", "")

        if logic_text:
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(41, 128, 185)
            pdf.cell(0, 7, "SECURITY & LOGIC REVIEW:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

            pdf.set_font("helvetica", "", 9)
            # Split long text into multiple lines
            logic_clean = clean_text(logic_text)
            if len(logic_clean) > 400:
                logic_clean = logic_clean[:400] + "..."

            # Print line by line
            words = logic_clean.split()
            line = ""
            for word in words:
                if len(line + word) < 85:
                    line += word + " "
                else:
                    pdf.cell(0, 5, line.strip(), new_x="LMARGIN", new_y="NEXT")
                    line = word + " "
            if line:
                pdf.cell(0, 5, line.strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # SUGGESTED FIXES
        fl_fixes = next(
            (r for r in fix_suggestions if r.get("filename") == s.get("filename")), {}
        )
        fixes = fl_fixes.get("fixes", [])

        if fixes:
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(243, 121, 32)
            pdf.cell(
                0, 7, f"SUGGESTED FIXES ({len(fixes)}):", new_x="LMARGIN", new_y="NEXT"
            )
            pdf.set_text_color(0, 0, 0)

            for fix in fixes:
                pdf.set_font("helvetica", "B", 9)
                title = clean_text(fix.get("issue_title", "Fix"))
                if len(title) > 70:
                    title = title[:70] + "..."
                sev = fix.get("severity", "N/A")
                pdf.cell(0, 5, f"  - {title} ({sev})", new_x="LMARGIN", new_y="NEXT")

                # Show original and fixed code
                orig = fix.get("original_code", "")
                fixed = fix.get("fixed_code", "")
                if orig:
                    pdf.set_font("courier", "", 8)
                    pdf.set_text_color(231, 76, 60)
                    orig_clean = clean_text(orig)
                    if len(orig_clean) > 60:
                        orig_clean = orig_clean[:60] + "..."
                    pdf.cell(
                        0, 4, f"    Before: {orig_clean}", new_x="LMARGIN", new_y="NEXT"
                    )
                if fixed:
                    pdf.set_font("courier", "", 8)
                    pdf.set_text_color(39, 174, 96)
                    fixed_clean = clean_text(fixed)
                    if len(fixed_clean) > 60:
                        fixed_clean = fixed_clean[:60] + "..."
                    pdf.cell(
                        0,
                        4,
                        f"    After:  {fixed_clean}",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    pdf.set_text_color(0, 0, 0)

                # Show explanation
                expl = fix.get("explanation", "")
                if expl:
                    pdf.set_font("helvetica", "I", 8)
                    pdf.set_text_color(100, 100, 100)
                    expl_clean = clean_text(expl)
                    if len(expl_clean) > 70:
                        expl_clean = expl_clean[:70] + "..."
                    pdf.cell(
                        0, 4, f"    Why: {expl_clean}", new_x="LMARGIN", new_y="NEXT"
                    )
                    pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Divider
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    # Footer
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, "Generated by AI Code Review Agent", align="C")

    out = pdf.output()
    return bytes(out) if isinstance(out, bytearray) else out
