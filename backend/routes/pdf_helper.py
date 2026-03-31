"""Shared PDF base class for all Flow reports."""
from fpdf import FPDF
from datetime import datetime
import re


# Brand colors (RGB)
C_DARK = (11, 17, 32)       # Near black bg
C_NAVY = (15, 23, 42)       # Dark navy
C_BLUE = (59, 130, 246)     # Primary blue
C_EMERALD = (16, 185, 129)  # Green accent
C_VIOLET = (139, 92, 246)   # Purple accent
C_AMBER = (245, 158, 11)    # Amber
C_RED = (239, 68, 68)       # Red
C_SLATE = (100, 116, 139)   # Muted text
C_LIGHT = (248, 250, 252)   # Light bg
C_WHITE = (255, 255, 255)
C_BORDER = (226, 232, 240)  # Table border
C_ROW_ALT = (241, 245, 249) # Alternate row


def clean_text(text: str) -> str:
    """Remove markdown and encode to ASCII-safe."""
    text = str(text)
    text = text.replace('€', 'EUR ')
    text = text.replace('→', '->')
    text = text.replace('•', '-')
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    return text


class FlowPDF(FPDF):
    def __init__(self, report_title="Report", subtitle="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_title = clean_text(report_title)
        self.subtitle = clean_text(subtitle)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Top accent bar
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, 210, 22, 'F')

        # Accent line
        self.set_fill_color(*C_BLUE)
        self.rect(0, 22, 210, 1.2, 'F')

        # Logo / brand
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(*C_BLUE)
        self.set_xy(10, 5)
        self.cell(25, 12, 'FLOW', ln=False)

        # Report title
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*C_WHITE)
        self.set_xy(35, 5)
        self.cell(130, 6, self.report_title, ln=False)

        # Subtitle / date
        self.set_font('Helvetica', '', 8)
        self.set_text_color(180, 200, 230)
        self.set_xy(35, 12)
        self.cell(130, 5, self.subtitle, ln=False)

        # Page number top-right
        self.set_font('Helvetica', '', 8)
        self.set_text_color(150, 170, 200)
        self.set_xy(155, 8)
        self.cell(45, 6, f'Pag. {self.page_no()}', align='R', ln=False)

        self.set_xy(10, 28)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*C_NAVY)
        self.rect(0, self.get_y() - 2, 210, 20, 'F')
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(140, 160, 200)
        self.cell(0, 10,
                  f'Flow Business Analytics  |  Generato il {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  Confidenziale',
                  align='C')

    # ── Section title ─────────────────────────────────────────────
    def section_title(self, text, color=None):
        color = color or C_BLUE
        self.ln(3)
        self.set_fill_color(*C_LIGHT)
        self.set_text_color(*color)
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 8, f'  {clean_text(text)}', fill=True, new_x='LMARGIN', new_y='NEXT')
        # Bottom accent line
        self.set_fill_color(*color)
        self.rect(10, self.get_y(), 190, 0.5, 'F')
        self.ln(3)

    # ── KPI Box ───────────────────────────────────────────────────
    def kpi_box(self, x, y, w, h, label, value, color=None, sub=None):
        color = color or C_BLUE
        # Background
        self.set_fill_color(
            min(255, color[0] // 5 + 235),
            min(255, color[1] // 5 + 235),
            min(255, color[2] // 5 + 235)
        )
        self.set_draw_color(*color)
        self.rect(x, y, w, h, 'FD')
        # Left accent bar
        self.set_fill_color(*color)
        self.rect(x, y, 2.5, h, 'F')
        # Label
        self.set_font('Helvetica', '', 7.5)
        self.set_text_color(*C_SLATE)
        self.set_xy(x + 4, y + 2)
        self.cell(w - 6, 5, clean_text(label), ln=False)
        # Value
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*C_NAVY)
        self.set_xy(x + 4, y + 6.5)
        self.cell(w - 6, 7, clean_text(str(value)), ln=False)
        # Sub label
        if sub:
            self.set_font('Helvetica', '', 7)
            self.set_text_color(*C_SLATE)
            self.set_xy(x + 4, y + h - 5)
            self.cell(w - 6, 4, clean_text(str(sub)), ln=False)

    def kpi_row_4(self, kpis):
        """Render up to 4 KPI boxes in a row. kpis = list of (label, value, color, sub)"""
        n = len(kpis)
        margin = 10
        spacing = 3
        total_w = 190
        box_w = (total_w - spacing * (n - 1)) / n
        y = self.get_y()
        for i, (label, value, color, sub) in enumerate(kpis):
            x = margin + i * (box_w + spacing)
            self.kpi_box(x, y, box_w, 19, label, value, color, sub)
        self.ln(24)

    # ── Table ─────────────────────────────────────────────────────
    def table_header(self, cols, widths):
        self.set_font('Helvetica', 'B', 8.5)
        self.set_fill_color(*C_NAVY)
        self.set_text_color(*C_WHITE)
        self.set_draw_color(*C_BORDER)
        for col, w in zip(cols, widths):
            self.cell(w, 7, col, border=1, fill=True, align='C')
        self.ln()

    def table_row(self, values, widths, aligns=None, alt=False):
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(*C_NAVY)
        self.set_draw_color(*C_BORDER)
        if alt:
            self.set_fill_color(*C_ROW_ALT)
        else:
            self.set_fill_color(*C_WHITE)
        for i, (val, w) in enumerate(zip(values, widths)):
            a = (aligns[i] if aligns else 'L')
            self.cell(w, 6, str(val)[:35], border=1, align=a, fill=True)
        self.ln()

    # ── Formatted AI text ─────────────────────────────────────────
    def ai_text_block(self, text, max_width=180):
        """Render markdown-cleaned AI text with section detection."""
        lines = clean_text(text).split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(1.5)
                continue
            # Section headers (all caps or ending with :)
            if line.isupper() and len(line) > 3:
                self.ln(2)
                self.set_font('Helvetica', 'B', 9.5)
                self.set_text_color(*C_BLUE)
                self.cell(0, 6, line, new_x='LMARGIN', new_y='NEXT')
                self.set_fill_color(*C_BLUE)
                self.rect(10, self.get_y(), 60, 0.4, 'F')
                self.ln(2)
            elif (len(line) < 60 and line.endswith(':')) or line.startswith('##'):
                clean = line.rstrip(':').lstrip('#').strip()
                self.ln(1)
                self.set_font('Helvetica', 'B', 9)
                self.set_text_color(*C_NAVY)
                self.cell(0, 5.5, clean + ':', new_x='LMARGIN', new_y='NEXT')
            elif line.startswith('-') or line.startswith('*'):
                # Bullet
                self.set_font('Helvetica', '', 8.5)
                self.set_text_color(60, 70, 90)
                self.set_x(14)
                self.cell(3, 5, '-', ln=False)
                self.set_x(18)
                self._write_wrapped(line.lstrip('-*').strip(), max_width - 10)
            else:
                self.set_font('Helvetica', '', 8.5)
                self.set_text_color(60, 70, 90)
                self._write_wrapped(line, max_width)

    def _write_wrapped(self, text, max_width):
        words = text.split()
        current = ''
        for w in words:
            test = (current + ' ' + w).strip()
            if self.get_string_width(test) <= max_width:
                current = test
            else:
                if current:
                    self.cell(0, 5, current, new_x='LMARGIN', new_y='NEXT')
                current = w
        if current:
            self.cell(0, 5, current, new_x='LMARGIN', new_y='NEXT')

    # ── Mini bar chart (ASCII-style horizontal bars) ──────────────
    def mini_bar_chart(self, data, label_col, value_col, color=None, max_rows=12):
        """data: list of dicts. Renders a visual bar representation."""
        color = color or C_BLUE
        if not data:
            return
        max_val = max(abs(d[value_col]) for d in data[:max_rows]) or 1
        bar_max_w = 80

        self.set_font('Helvetica', 'B', 7.5)
        self.set_text_color(*C_SLATE)
        self.cell(70, 5, label_col, ln=False)
        self.cell(0, 5, value_col, new_x='LMARGIN', new_y='NEXT')

        for i, d in enumerate(data[:max_rows]):
            label = str(d[label_col])[:22]
            val = abs(d[value_col])
            bar_w = (val / max_val) * bar_max_w

            alt = i % 2 == 1
            if alt:
                self.set_fill_color(*C_ROW_ALT)
                self.rect(10, self.get_y(), 190, 6, 'F')

            # Label
            self.set_font('Helvetica', '', 7.5)
            self.set_text_color(*C_NAVY)
            self.set_x(10)
            self.cell(65, 6, label, ln=False)

            # Bar
            bar_x = self.get_x()
            bar_y = self.get_y() + 1.5
            if bar_w > 0:
                self.set_fill_color(*color)
                self.rect(bar_x, bar_y, bar_w, 3, 'F')

            # Value
            self.set_x(bar_x + bar_max_w + 3)
            self.set_font('Helvetica', 'B', 7.5)
            self.set_text_color(*C_NAVY)
            self.cell(30, 6, f'EUR {val:,.0f}', align='R', new_x='LMARGIN', new_y='NEXT')
        self.ln(2)
