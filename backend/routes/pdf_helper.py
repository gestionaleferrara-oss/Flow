"""Shared PDF base class for all Flow reports."""
from fpdf import FPDF
from datetime import datetime
import re

# Brand colors (RGB)
C_DARK  = (11,  17,  32)
C_NAVY  = (15,  23,  42)
C_BLUE  = (59,  130, 246)
C_EMERALD=(16, 185, 129)
C_VIOLET= (139, 92, 246)
C_AMBER = (245, 158, 11)
C_RED   = (239, 68,  68)
C_SLATE = (100, 116, 139)
C_LIGHT = (245, 247, 250)
C_WHITE = (255, 255, 255)
C_BORDER= (210, 218, 230)
C_ROW_ALT=(242, 246, 250)

PAGE_H   = 297   # A4
MARGIN_B = 22    # footer safe zone
SAFE_Y   = PAGE_H - MARGIN_B   # max Y before footer


def clean_text(text: str) -> str:
    text = str(text)
    for src, dst in [('€','EUR '),('→','->'),('•','-'),('–','-'),('—','-'),
                     ('\u2019',"'"),('\u201c','"'),('\u201d','"')]:
        text = text.replace(src, dst)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*',     r'\1', text)
    text = re.sub(r'#{1,6}\s*',       '',    text)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _bg(color, lightness=235):
    return tuple(min(255, c // 6 + lightness) for c in color)


class FlowPDF(FPDF):
    def __init__(self, report_title="Report", subtitle=""):
        super().__init__()
        self.report_title = clean_text(report_title)
        self.subtitle     = clean_text(subtitle)
        self.set_auto_page_break(auto=True, margin=MARGIN_B)
        self.set_margins(10, 30, 10)

    # ── Header / Footer ────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*C_NAVY);  self.rect(0, 0, 210, 24, 'F')
        self.set_fill_color(*C_BLUE);  self.rect(0, 24, 210, 1.5, 'F')

        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*C_BLUE)
        self.set_xy(10, 5);  self.cell(22, 14, 'FLOW', ln=False)

        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*C_WHITE)
        self.set_xy(33, 5);  self.cell(130, 7, self.report_title, ln=False)

        self.set_font('Helvetica', '', 8)
        self.set_text_color(170, 195, 230)
        self.set_xy(33, 13);  self.cell(130, 6, self.subtitle, ln=False)

        self.set_font('Helvetica', '', 8)
        self.set_text_color(150, 170, 210)
        self.set_xy(150, 8);  self.cell(50, 7, f'Pag. {self.page_no()}', align='R', ln=False)

        self.set_xy(10, 30)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*C_NAVY);  self.rect(0, self.get_y()-1, 210, 18, 'F')
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(140, 165, 205)
        self.cell(0, 10,
            f'Flow Business Analytics  |  Generato il {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  Confidenziale',
            align='C')

    # ── Space helpers ───────────────────────────────────────────────
    def remaining_y(self):
        return SAFE_Y - self.get_y()

    def ensure_space(self, needed_mm):
        """If less than needed_mm remains, start a new page."""
        if self.remaining_y() < needed_mm:
            self.add_page()

    # ── Section title ───────────────────────────────────────────────
    def section_title(self, text, color=None, top_gap=5):
        color = color or C_BLUE
        self.ensure_space(20)
        if top_gap: self.ln(top_gap)

        # Background strip
        y = self.get_y()
        self.set_fill_color(*_bg(color, 238))
        self.rect(10, y, 190, 8, 'F')
        # Left accent
        self.set_fill_color(*color)
        self.rect(10, y, 3, 8, 'F')
        # Text
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*color)
        self.set_xy(16, y)
        self.cell(180, 8, clean_text(text).upper(), ln=False)
        self.set_xy(10, y + 8)
        self.ln(3)

    def note_text(self, text):
        """Small muted italic note (e.g. a table legend)."""
        self.ensure_space(12)
        self.ln(1)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(*C_SLATE)
        self.set_x(10)
        self.multi_cell(190, 3.6, clean_text(text))
        self.ln(1)


    # ── KPI boxes ───────────────────────────────────────────────────
    def kpi_box(self, x, y, w, h, label, value, color=None, sub=None):
        color = color or C_BLUE
        bg    = _bg(color)
        self.set_fill_color(*bg);  self.set_draw_color(*color)
        self.rect(x, y, w, h, 'FD')
        # Accent bar
        self.set_fill_color(*color);  self.rect(x, y, 3, h, 'F')
        # Label
        self.set_font('Helvetica', '', 7); self.set_text_color(*C_SLATE)
        self.set_xy(x+5, y+2);  self.cell(w-7, 5, clean_text(label)[:30], ln=False)
        # Value
        self.set_font('Helvetica', 'B', 10.5); self.set_text_color(*C_NAVY)
        self.set_xy(x+5, y+6.5);  self.cell(w-7, 7, clean_text(str(value)), ln=False)
        # Sub
        if sub:
            self.set_font('Helvetica', '', 6.5); self.set_text_color(*C_SLATE)
            self.set_xy(x+5, y+h-5.5);  self.cell(w-7, 4, clean_text(str(sub)), ln=False)

    def kpi_row(self, kpis):
        """kpis: list of (label, value, color, sub).  Max 4."""
        n     = len(kpis)
        gap   = 3
        box_w = (190 - gap * (n-1)) / n
        y     = self.get_y()
        for i, (label, value, color, sub) in enumerate(kpis):
            self.kpi_box(10 + i*(box_w+gap), y, box_w, 20, label, value, color, sub)
        self.set_xy(10, y + 25)

    # ── Smart table ─────────────────────────────────────────────────
    def smart_table(self, cols, widths, rows, aligns=None, row_h=5.5,
                    col_colors=None, value_formatters=None):
        """Draw table with repeated header on page breaks."""
        aligns = aligns or ['L'] * len(cols)

        def draw_header():
            self.set_font('Helvetica', 'B', 8)
            self.set_fill_color(*C_NAVY); self.set_text_color(*C_WHITE)
            self.set_draw_color(*C_BORDER)
            for col, w, a in zip(cols, widths, aligns):
                self.cell(w, 7, col, border=1, fill=True, align=a)
            self.ln()

        # Check there's room for header + at least 4 rows
        self.ensure_space(7 + row_h * 4)
        draw_header()

        for i, row_vals in enumerate(rows):
            # Page break with repeated header
            if self.get_y() + row_h > SAFE_Y:
                self.add_page()
                draw_header()

            alt = i % 2 == 1
            self.set_font('Helvetica', '', 8)
            self.set_text_color(*C_NAVY)
            self.set_draw_color(*C_BORDER)
            self.set_fill_color(*C_ROW_ALT if alt else C_WHITE)

            for j, (val, w, a) in enumerate(zip(row_vals, widths, aligns)):
                # Highlight specific cells with color if requested
                if col_colors and col_colors.get(j):
                    r,g,b = col_colors[j](str(val))
                    self.set_text_color(r,g,b)
                else:
                    self.set_text_color(*C_NAVY)
                self.cell(w, row_h, str(val), border=1, align=a, fill=alt)
            self.ln()

        self.ln(3)

    # ── Monthly bar chart ───────────────────────────────────────────
    def monthly_chart(self, mensile_sorted, metric_unit='EUR '):
        """Visual horizontal bar chart for monthly data."""
        if not mensile_sorted:
            return
        max_val = max(v for _, v in mensile_sorted) or 1
        bar_max  = 100   # mm
        label_w  = 22
        val_w    = 38
        row_h    = 7

        # Header strip
        y0 = self.get_y()
        self.set_fill_color(*C_NAVY); self.set_text_color(*C_WHITE)
        self.set_font('Helvetica', 'B', 8)
        self.rect(10, y0, 190, 7, 'F')
        self.set_xy(10, y0)
        self.cell(label_w, 7, 'Mese', border=0, fill=False, align='C', ln=False)
        self.cell(bar_max + 6, 7, 'Andamento', border=0, fill=False, align='C', ln=False)
        self.cell(val_w,   7, f'Fatturato ({metric_unit.strip()})', border=0, fill=False, align='R', ln=False)
        self.set_xy(10, y0 + 7)

        for i, (mese, val) in enumerate(mensile_sorted):
            if self.get_y() + row_h > SAFE_Y:
                self.add_page()

            alt = i % 2 == 1
            row_y = self.get_y()
            self.set_fill_color(*C_ROW_ALT if alt else C_WHITE)
            self.rect(10, row_y, 190, row_h, 'F')

            # Thin bottom border
            self.set_draw_color(*C_BORDER)
            self.line(10, row_y + row_h, 200, row_y + row_h)

            # Month label
            self.set_font('Helvetica', '', 7.5); self.set_text_color(*C_SLATE)
            self.set_xy(10, row_y + 1.2)
            self.cell(label_w, row_h-2, mese, ln=False)

            # Bar
            bar_x = 10 + label_w + 3
            bar_y = row_y + 2
            bar_w = (val / max_val) * (bar_max - 6)
            # Background track
            self.set_fill_color(220, 228, 238)
            self.rect(bar_x, bar_y, bar_max - 6, 3, 'F')
            # Value bar
            color_bar = C_BLUE if i < len(mensile_sorted)-1 else C_EMERALD
            self.set_fill_color(*color_bar)
            if bar_w > 0:
                self.rect(bar_x, bar_y, bar_w, 3, 'F')

            # Value
            self.set_font('Helvetica', 'B', 8); self.set_text_color(*C_NAVY)
            self.set_xy(10 + label_w + bar_max + 2, row_y + 1.2)
            self.cell(val_w, row_h-2, f'{val:,.2f}', align='R', ln=False)

            self.set_xy(10, row_y + row_h)

        self.ln(4)

    # ── AI text ─────────────────────────────────────────────────────
    def ai_text_block(self, text):
        lines = clean_text(text).split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(2); continue
            if line.isupper() and len(line) > 3:
                self.ln(2)
                self.set_font('Helvetica', 'B', 9); self.set_text_color(*C_BLUE)
                self.cell(0, 6, line, new_x='LMARGIN', new_y='NEXT')
                self.set_fill_color(*C_BLUE); self.rect(10, self.get_y(), 50, 0.4, 'F')
                self.ln(2)
            elif (len(line) < 70 and line.endswith(':')) or line.startswith('##'):
                clean = line.rstrip(':').lstrip('#').strip()
                self.ln(1)
                self.set_font('Helvetica', 'B', 9); self.set_text_color(*C_NAVY)
                self.cell(0, 5.5, clean + ':', new_x='LMARGIN', new_y='NEXT')
            elif line.startswith('-') or line.startswith('*'):
                self.set_font('Helvetica', '', 8.5); self.set_text_color(55, 65, 85)
                self.set_x(16); self.cell(3, 5, '-', ln=False)
                self.set_x(20); self._write_wrap(line.lstrip('-*').strip(), 170)
            else:
                self.set_font('Helvetica', '', 8.5); self.set_text_color(55, 65, 85)
                self._write_wrap(line, 180)

    def _write_wrap(self, text, max_w):
        words = text.split(); cur = ''
        for w in words:
            test = (cur+' '+w).strip()
            if self.get_string_width(test) <= max_w: cur = test
            else:
                if cur: self.cell(0, 5, cur, new_x='LMARGIN', new_y='NEXT')
                cur = w
        if cur: self.cell(0, 5, cur, new_x='LMARGIN', new_y='NEXT')
