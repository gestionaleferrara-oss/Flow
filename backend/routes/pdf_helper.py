"""Base grafica condivisa da tutti i PDF Flow.

Impaginazione editoriale su fondo chiaro, font IBM Plex Sans (unicode: € e accenti ok),
tabelle senza griglia, KPI a schede, titoli di sezione con filetto.
L'API pubblica (FlowPDF, clean_text, colori) resta identica per tutti i chiamanti.
"""
import os
import re
from datetime import datetime

from fpdf import FPDF

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
FONT = "plex"

# Palette (RGB)
C_DARK   = (10,  15,  28)
C_NAVY   = (18,  26,  43)
C_BLUE   = (37,  99,  235)
C_EMERALD= (5,   150, 105)
C_VIOLET = (124, 58,  237)
C_AMBER  = (202, 138, 4)
C_RED    = (220, 38,  38)
C_SLATE  = (110, 122, 142)
C_MUTED  = (148, 158, 175)
C_LIGHT  = (246, 248, 251)
C_WHITE  = (255, 255, 255)
C_BORDER = (223, 229, 238)
C_HAIR   = (234, 238, 245)
C_ROW_ALT= (248, 250, 252)

PAGE_W   = 210
PAGE_H   = 297
ML       = 14          # margine sinistro
MR       = 14          # margine destro
CONTENT_W = PAGE_W - ML - MR
HEADER_H = 26
MARGIN_B = 20
SAFE_Y   = PAGE_H - MARGIN_B


def clean_text(text: str) -> str:
    """Normalizza il markdown e i caratteri tipografici (il font e' unicode)."""
    text = str(text)
    for src, dst in [('→', '→'), ('•', '-'), ('\u2019', "'"),
                     ('\u201c', '"'), ('\u201d', '"'), ('\u00a0', ' ')]:
        text = text.replace(src, dst)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]', '', text)
    return text.strip()


def it_num(v, dec=2) -> str:
    """Numero in formato italiano: 1.234,56"""
    txt = f"{(v or 0):,.{dec}f}"
    return txt.replace(",", "@").replace(".", ",").replace("@", ".")


def eur(v, dec=2) -> str:
    return f"\u20ac {it_num(v, dec)}"


def _tint(color, amount=0.92):
    """Versione molto chiara del colore, per gli sfondi."""
    return tuple(int(c + (255 - c) * amount) for c in color)


class FlowPDF(FPDF):
    def __init__(self, report_title="Report", subtitle=""):
        super().__init__()
        self.report_title = clean_text(report_title)
        self.subtitle = clean_text(subtitle)
        self.accent = C_BLUE
        self.set_auto_page_break(auto=True, margin=MARGIN_B)
        self.set_margins(ML, HEADER_H + 8, MR)
        self.add_font(FONT, '', os.path.join(FONT_DIR, 'Plex-Regular.ttf'))
        self.add_font(FONT, 'B', os.path.join(FONT_DIR, 'Plex-Bold.ttf'))
        self.add_font(FONT, 'I', os.path.join(FONT_DIR, 'Plex-Italic.ttf'))
        self.add_font(FONT + 'med', '', os.path.join(FONT_DIR, 'Plex-Medium.ttf'))
        self.set_font(FONT, '', 9)
        self.set_text_color(*C_NAVY)

    # ── Header / Footer ────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*C_WHITE)
        self.rect(0, 0, PAGE_W, HEADER_H, 'F')

        # Titolo + sottotitolo
        self.set_font(FONT, 'B', 11.5)
        self.set_text_color(*C_DARK)
        self.set_xy(ML, 7.2)
        self.cell(150, 6, self.report_title[:74], ln=False)
        if self.subtitle:
            self.set_font(FONT, '', 7.8)
            self.set_text_color(*C_SLATE)
            self.set_xy(ML, 13.6)
            self.cell(150, 5, self.subtitle[:120], ln=False)

        # Numero pagina
        self.set_font(FONT, '', 7.6)
        self.set_text_color(*C_MUTED)
        self.set_xy(PAGE_W - MR - 30, 9)
        self.cell(30, 6, f'{self.page_no():02d}', align='R', ln=False)

        # Filetto con segmento accento
        self.set_fill_color(*C_HAIR)
        self.rect(ML, HEADER_H - 3.5, CONTENT_W, 0.35, 'F')
        self.set_fill_color(*self.accent)
        self.rect(ML, HEADER_H - 3.5, 26, 0.9, 'F')

        self.set_xy(ML, HEADER_H + 8)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*C_HAIR)
        self.rect(ML, self.get_y(), CONTENT_W, 0.35, 'F')
        self.set_font(FONT, '', 7)
        self.set_text_color(*C_MUTED)
        self.set_xy(ML, self.get_y() + 1.5)
        self.cell(CONTENT_W / 2, 5, 'Flow Business Analytics', ln=False)
        self.cell(CONTENT_W / 2, 5,
                  f'Generato il {datetime.now().strftime("%d/%m/%Y %H:%M")}  ·  Documento riservato',
                  align='R', ln=False)

    # ── Spazi ──────────────────────────────────────────────────────
    def remaining_y(self):
        return SAFE_Y - self.get_y()

    def ensure_space(self, needed_mm):
        if self.remaining_y() < needed_mm:
            self.add_page()

    # ── Titolo di sezione ──────────────────────────────────────────
    def section_title(self, text, color=None, top_gap=6):
        color = color or self.accent
        self.ensure_space(34)
        if top_gap:
            self.ln(top_gap)
        y = self.get_y()
        label = clean_text(text).upper()
        self.set_font(FONT, 'B', 8.6)
        self.set_text_color(*C_DARK)
        self.set_xy(ML, y)
        self.cell(0, 5, label, ln=False)
        w = self.get_string_width(label)
        # Filetto a destra del titolo
        self.set_fill_color(*C_HAIR)
        self.rect(ML + w + 4, y + 2.4, max(CONTENT_W - w - 4, 0), 0.3, 'F')
        # Puntino accento
        self.set_fill_color(*color)
        self.rect(ML + w + 4, y + 2.05, 6, 0.9, 'F')
        self.set_xy(ML, y + 8)

    def note_text(self, text):
        self.ensure_space(12)
        self.ln(1.5)
        self.set_font(FONT, 'I', 7)
        self.set_text_color(*C_MUTED)
        self.set_x(ML)
        self.multi_cell(CONTENT_W, 3.6, clean_text(text))
        self.ln(1)

    def lead_text(self, text):
        """Paragrafo introduttivo piu' grande."""
        self.ensure_space(16)
        self.set_font(FONT, '', 9.4)
        self.set_text_color(60, 72, 92)
        self.set_x(ML)
        self.multi_cell(CONTENT_W, 5.2, clean_text(text))
        self.ln(2)

    # ── KPI ────────────────────────────────────────────────────────
    def kpi_box(self, x, y, w, h, label, value, color=None, sub=None):
        color = color or self.accent
        self.set_fill_color(*C_WHITE)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.25)
        self.rect(x, y, w, h, 'FD')
        self.set_fill_color(*color)
        self.rect(x, y, w, 1.1, 'F')

        self.set_font(FONT, '', 6.6)
        self.set_text_color(*C_MUTED)
        self.set_xy(x + 4, y + 3.4)
        self.cell(w - 6, 4, clean_text(label).upper()[:34], ln=False)

        val = clean_text(str(value))
        size = 13 if len(val) <= 12 else (11 if len(val) <= 17 else 9.2)
        self.set_font(FONT, 'B', size)
        self.set_text_color(*C_DARK)
        self.set_xy(x + 4, y + 8.2)
        self.cell(w - 6, 7, val, ln=False)

        if sub:
            self.set_font(FONT, '', 6.4)
            self.set_text_color(*C_SLATE)
            self.set_xy(x + 4, y + h - 6)
            self.cell(w - 6, 4, clean_text(str(sub))[:40], ln=False)

    def kpi_row(self, kpis):
        """kpis: lista di (label, value, color, sub). Max 4."""
        kpis = list(kpis)[:4]
        n = max(len(kpis), 1)
        gap = 3.5
        box_w = (CONTENT_W - gap * (n - 1)) / n
        self.ensure_space(30)
        y = self.get_y()
        for i, (label, value, color, sub) in enumerate(kpis):
            self.kpi_box(ML + i * (box_w + gap), y, box_w, 22, label, value, color, sub)
        self.set_xy(ML, y + 27)

    # ── Tabella ────────────────────────────────────────────────────
    def smart_table(self, cols, widths, rows, aligns=None, row_h=6.2,
                    col_colors=None, value_formatters=None):
        aligns = aligns or ['L'] * len(cols)
        scale = CONTENT_W / max(sum(widths), 1)
        widths = [w * scale for w in widths]

        def draw_header():
            y = self.get_y()
            self.set_font(FONT, 'B', 7)
            self.set_text_color(*C_SLATE)
            self.set_x(ML)
            for col, w, a in zip(cols, widths, aligns):
                self.cell(w, 6, clean_text(col).upper(), border=0, align=a)
            self.ln(6)
            self.set_fill_color(*C_NAVY)
            self.rect(ML, y + 6, CONTENT_W, 0.45, 'F')
            self.ln(1.6)

        self.ensure_space(8 + row_h * 3)
        draw_header()

        for i, row_vals in enumerate(rows):
            if self.get_y() + row_h > SAFE_Y:
                self.add_page()
                draw_header()
            y = self.get_y()
            if i % 2 == 1:
                self.set_fill_color(*C_ROW_ALT)
                self.rect(ML, y - 0.6, CONTENT_W, row_h, 'F')

            self.set_font(FONT, '', 7.8)
            self.set_x(ML)
            for j, (val, w, a) in enumerate(zip(row_vals, widths, aligns)):
                txt = clean_text('' if val is None else str(val))
                size = 7.8
                if col_colors and col_colors.get(j):
                    self.set_text_color(*col_colors[j](txt))
                    style = 'B'
                elif j == 0:
                    self.set_text_color(*C_DARK)
                    style = ''
                else:
                    self.set_text_color(45, 56, 74)
                    style = ''
                self.set_font(FONT, style, size)
                # riduce il corpo prima di troncare, cosi' i numeri restano leggibili
                while txt and self.get_string_width(txt) > w - 2 and size > 5.6:
                    size -= 0.35
                    self.set_font(FONT, style, size)
                while txt and self.get_string_width(txt) > w - 2:
                    txt = txt[:-2] + '.'
                self.cell(w, row_h - 1.2, txt, border=0, align=a)
            self.ln(row_h - 1.2)
            self.set_fill_color(*C_HAIR)
            self.rect(ML, self.get_y() - 0.4, CONTENT_W, 0.2, 'F')
            self.ln(0.8)

        self.ln(2)

    # ── Grafici ────────────────────────────────────────────────────
    def column_chart(self, pairs, color=None, height=42, unit=''):
        """Istogramma verticale: pairs = [(etichetta, valore), ...] max 14 colonne."""
        pairs = [(str(k), float(v or 0)) for k, v in pairs][:14]
        if not pairs:
            return
        color = color or self.accent
        self.ensure_space(height + 18)
        top = self.get_y()
        base = top + height
        max_val = max(v for _, v in pairs) or 1

        self.set_fill_color(*C_HAIR)
        for frac in (0, 0.5, 1):
            self.rect(ML, base - height * frac, CONTENT_W, 0.2, 'F')
        self.set_font(FONT, '', 6)
        self.set_text_color(*C_MUTED)
        for frac in (0.5, 1):
            self.set_xy(ML, base - height * frac - 3.4)
            self.cell(CONTENT_W, 3, f'{it_num(max_val * frac)}{unit}', align='R', ln=False)

        slot = CONTENT_W / len(pairs)
        bar_w = min(slot * 0.52, 13)
        for i, (label, val) in enumerate(pairs):
            x = ML + slot * i + (slot - bar_w) / 2
            h = max((val / max_val) * height, 0.4)
            self.set_fill_color(*color)
            self.rect(x, base - h, bar_w, h, 'F')
            self.set_font(FONT, 'B', 6.2)
            self.set_text_color(*C_DARK)
            self.set_xy(x - 4, base - h - 4.2)
            self.cell(bar_w + 8, 3.4, it_num(val), align='C', ln=False)
            self.set_font(FONT, '', 6.2)
            self.set_text_color(*C_SLATE)
            self.set_xy(x - 4, base + 1.4)
            self.cell(bar_w + 8, 3.4, clean_text(label)[:10], align='C', ln=False)

        self.set_xy(ML, base + 8)

    def line_chart(self, labels, serie_a, serie_b=None, legend_a='Periodo', legend_b='Anno prec.',
                   color_a=None, color_b=None, height=44, unit='', mostra_valori=True):
        """Grafico a linee con area: serie_a in evidenza, serie_b (opzionale) tratteggiata."""
        labels = [clean_text(str(l)) for l in labels]
        if not labels:
            return
        color_a = color_a or self.accent
        color_b = color_b or C_MUTED
        serie_a = [float(v or 0) for v in serie_a]
        serie_b = [float(v or 0) for v in (serie_b or [])]
        self.ensure_space(height + 26)

        y0 = self.get_y()
        # legenda
        self.set_font(FONT, '', 6.6)
        entries = [(legend_a, color_a)] + ([(legend_b, color_b)] if serie_b else [])
        for i, (lab, col) in enumerate(entries):
            x = ML + i * 42
            self.set_fill_color(*col)
            self.rect(x, y0 + 1.2, 6, 1.4, 'F')
            self.set_text_color(*C_SLATE)
            self.set_xy(x + 7.4, y0 - 0.4)
            self.cell(36, 4, clean_text(lab)[:24], ln=False)

        pad_l = 20
        top = y0 + 7
        base = top + height
        plot_x = ML + pad_l
        plot_w = CONTENT_W - pad_l - 4
        max_val = max(serie_a + serie_b + [1])

        # griglia + etichette asse
        self.set_font(FONT, '', 6)
        for frac in (0, 0.5, 1):
            gy = base - height * frac
            self.set_fill_color(*C_HAIR)
            self.rect(plot_x, gy, plot_w, 0.2, 'F')
            self.set_text_color(*C_MUTED)
            self.set_xy(ML, gy - 1.8)
            self.cell(pad_l - 2, 3.6, f'{it_num(max_val * frac)}', align='R', ln=False)

        n = len(labels)
        step = plot_w / max(n - 1, 1) if n > 1 else 0
        xs = [plot_x + (plot_w / 2 if n == 1 else step * i) for i in range(n)]

        def py(v):
            return base - (v / max_val) * height

        # area sotto la serie principale
        if n > 1:
            pts = [(xs[i], py(serie_a[i])) for i in range(n)]
            self.set_fill_color(*_tint(color_a, 0.86))
            self.polygon([(xs[0], base)] + pts + [(xs[-1], base)], style='F')

        # serie di confronto
        if serie_b:
            self.set_draw_color(*color_b)
            self.set_line_width(0.5)
            self.set_dash_pattern(dash=1.2, gap=1.2)
            for i in range(n - 1):
                self.line(xs[i], py(serie_b[i]), xs[i + 1], py(serie_b[i + 1]))
            self.set_dash_pattern()
            self.set_fill_color(*color_b)
            for i in range(n):
                self.ellipse(xs[i] - 0.8, py(serie_b[i]) - 0.8, 1.6, 1.6, 'F')

        # serie principale
        self.set_draw_color(*color_a)
        self.set_line_width(0.8)
        for i in range(n - 1):
            self.line(xs[i], py(serie_a[i]), xs[i + 1], py(serie_a[i + 1]))
        for i in range(n):
            self.set_fill_color(*C_WHITE)
            self.ellipse(xs[i] - 1.4, py(serie_a[i]) - 1.4, 2.8, 2.8, 'F')
            self.set_fill_color(*color_a)
            self.ellipse(xs[i] - 0.9, py(serie_a[i]) - 0.9, 1.8, 1.8, 'F')

        # valori ed etichette
        if mostra_valori:
            idx_max = max(range(n), key=lambda i: serie_a[i])
            evidenza = {0, n - 1, idx_max} if n > 6 else set(range(n))
            self.set_font(FONT, 'B', 6.2)
            self.set_text_color(*C_DARK)
            for i in sorted(evidenza):
                lx = min(max(xs[i] - 11, ML), PAGE_W - MR - 22)
                self.set_xy(lx, py(serie_a[i]) - 5.4)
                self.cell(22, 3.4, f'{it_num(serie_a[i])}{unit}', align='C', ln=False)

        self.set_font(FONT, '', 6.2)
        self.set_text_color(*C_SLATE)
        for i in range(n):
            self.set_xy(xs[i] - 11, base + 1.8)
            self.cell(22, 3.4, labels[i][:10], align='C', ln=False)

        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.set_xy(ML, base + 8)

    def compare_chart(self, labels, serie_a, serie_b, legend_a='Periodo', legend_b='Anno prec.',
                      color_a=None, color_b=None, height=42, unit=''):
        """Confronto anno su anno: reso come grafico a linee."""
        self.line_chart(labels, serie_a, serie_b, legend_a, legend_b,
                        color_a, color_b, height=height, unit=unit)

    def _compare_columns(self, labels, serie_a, serie_b, legend_a='Periodo', legend_b='Anno prec.',
                         color_a=None, color_b=None, height=42, unit=''):
        """Colonne appaiate per il confronto anno su anno."""
        labels = [str(l) for l in labels][:12]
        if not labels:
            return
        color_a = color_a or self.accent
        color_b = color_b or C_MUTED
        self.ensure_space(height + 24)

        y = self.get_y()
        self.set_font(FONT, '', 6.6)
        for i, (lab, col) in enumerate(((legend_a, color_a), (legend_b, color_b))):
            x = ML + i * 36
            self.set_fill_color(*col)
            self.rect(x, y + 1, 2.4, 2.4, 'F')
            self.set_text_color(*C_SLATE)
            self.set_xy(x + 3.6, y - 0.4)
            self.cell(32, 4, clean_text(lab)[:22], ln=False)
        top = y + 6
        base = top + height
        max_val = max([float(v or 0) for v in list(serie_a) + list(serie_b)] + [1])

        self.set_fill_color(*C_HAIR)
        for frac in (0, 0.5, 1):
            self.rect(ML, base - height * frac, CONTENT_W, 0.2, 'F')
        self.set_font(FONT, '', 6)
        self.set_text_color(*C_MUTED)
        self.set_xy(ML, base - height - 3.4)
        self.cell(CONTENT_W, 3, f'{it_num(max_val)}{unit}', align='R', ln=False)

        slot = CONTENT_W / len(labels)
        bar_w = min(slot * 0.3, 8)
        for i, label in enumerate(labels):
            cx = ML + slot * i + slot / 2
            for k, (vals, col) in enumerate(((serie_b, color_b), (serie_a, color_a))):
                v = float(vals[i] or 0) if i < len(vals) else 0
                h = max((v / max_val) * height, 0.3)
                x = cx - bar_w - 0.6 + k * (bar_w + 1.2)
                self.set_fill_color(*col)
                self.rect(x, base - h, bar_w, h, 'F')
            self.set_font(FONT, '', 6.2)
            self.set_text_color(*C_SLATE)
            self.set_xy(cx - slot / 2, base + 1.4)
            self.cell(slot, 3.4, clean_text(label)[:10], align='C', ln=False)

        self.set_xy(ML, base + 8)

    def bar_ranking(self, items, color=None, label_w=62, unit='', dec=0):
        """Classifica a barre orizzontali: items = [(etichetta, valore), ...]"""
        items = [(clean_text(str(k)), float(v or 0)) for k, v in items][:14]
        if not items:
            return
        color = color or self.accent
        max_val = max(v for _, v in items) or 1
        val_w = 28
        track_w = CONTENT_W - label_w - val_w - 4
        row_h = 6.6
        self.ensure_space(row_h * min(len(items), 4) + 6)

        for label, val in items:
            if self.get_y() + row_h > SAFE_Y:
                self.add_page()
            y = self.get_y()
            self.set_font(FONT, '', 7.2)
            self.set_text_color(*C_DARK)
            txt = label
            while txt and self.get_string_width(txt) > label_w - 2:
                txt = txt[:-2]
            self.set_xy(ML, y + 0.6)
            self.cell(label_w, row_h - 1.6, txt, ln=False)

            bx = ML + label_w
            self.set_fill_color(*C_HAIR)
            self.rect(bx, y + 2.1, track_w, 2.6, 'F')
            self.set_fill_color(*color)
            self.rect(bx, y + 2.1, max((val / max_val) * track_w, 0.3), 2.6, 'F')

            self.set_font(FONT, 'B', 7.2)
            self.set_text_color(*C_NAVY)
            self.set_xy(PAGE_W - MR - val_w, y + 0.6)
            self.cell(val_w, row_h - 1.6, f'{it_num(val, dec)}{unit}', align='R', ln=False)
            self.set_xy(ML, y + row_h)
        self.ln(3)

    def share_bar(self, items, height=6.5):
        """Barra 100% impilata: items = [(etichetta, valore, colore)]"""
        items = [(clean_text(str(k)), float(v or 0), c) for k, v, c in items if (v or 0) > 0]
        tot = sum(v for _, v, _ in items)
        if not tot:
            return
        self.ensure_space(height + 16)
        y = self.get_y()
        x = ML
        for label, val, col in items:
            w = CONTENT_W * val / tot
            self.set_fill_color(*col)
            self.rect(x, y, w, height, 'F')
            if w > 16:
                self.set_font(FONT, 'B', 6.4)
                self.set_text_color(*C_WHITE)
                self.set_xy(x, y + height / 2 - 1.8)
                self.cell(w, 3.6, f'{val / tot * 100:.0f}%', align='C', ln=False)
            x += w
        self.set_xy(ML, y + height + 2)
        self.set_font(FONT, '', 6.4)
        per_riga = 4
        for i, (label, val, col) in enumerate(items[:8]):
            if i and i % per_riga == 0:
                self.set_xy(ML, self.get_y() + 4)
            bx = ML + (i % per_riga) * (CONTENT_W / per_riga)
            yy = self.get_y()
            self.set_fill_color(*col)
            self.rect(bx, yy + 1, 2.2, 2.2, 'F')
            self.set_text_color(*C_SLATE)
            self.set_xy(bx + 3.4, yy - 0.2)
            self.cell(CONTENT_W / per_riga - 5, 4, label[:26], ln=False)
        self.set_xy(ML, self.get_y() + 8)

    def chart_caption(self, text):
        self.set_font(FONT, '', 6.6)
        self.set_text_color(*C_MUTED)
        self.set_x(ML)
        self.multi_cell(CONTENT_W, 3.4, clean_text(text), align='L')
        self.ln(1.5)


    # ── Grafico mensile ────────────────────────────────────────────
    def monthly_chart(self, mensile_sorted, metric_unit='\u20ac'):
        if not mensile_sorted:
            return
        max_val = max(v for _, v in mensile_sorted) or 1
        label_w = 20
        val_w = 30
        track_w = CONTENT_W - label_w - val_w - 8
        row_h = 7.4

        self.ensure_space(row_h * 3 + 8)
        y0 = self.get_y()
        self.set_font(FONT, 'B', 7)
        self.set_text_color(*C_SLATE)
        self.set_xy(ML, y0)
        self.cell(label_w, 5, 'MESE', ln=False)
        self.cell(track_w + 8, 5, 'ANDAMENTO', ln=False)
        self.cell(val_w, 5, clean_text(metric_unit).strip().upper() or 'VALORE', align='R', ln=False)
        self.set_fill_color(*C_NAVY)
        self.rect(ML, y0 + 5, CONTENT_W, 0.45, 'F')
        self.set_xy(ML, y0 + 7.5)

        for i, (mese, val) in enumerate(mensile_sorted):
            if self.get_y() + row_h > SAFE_Y:
                self.add_page()
            row_y = self.get_y()

            self.set_font(FONT, '', 7.6)
            self.set_text_color(*C_SLATE)
            self.set_xy(ML, row_y + 1)
            self.cell(label_w, row_h - 2, clean_text(str(mese)), ln=False)

            bar_x = ML + label_w
            bar_y = row_y + 2.4
            self.set_fill_color(*C_HAIR)
            self.rect(bar_x, bar_y, track_w, 2.6, 'F')
            bar_w = (val / max_val) * track_w
            ultimo = i == len(mensile_sorted) - 1
            self.set_fill_color(*(C_EMERALD if ultimo else self.accent))
            if bar_w > 0.2:
                self.rect(bar_x, bar_y, bar_w, 2.6, 'F')

            self.set_font(FONT, 'B', 7.8)
            self.set_text_color(*C_DARK)
            self.set_xy(PAGE_W - MR - val_w, row_y + 1)
            self.cell(val_w, row_h - 2, f'{val:,.0f}'.replace(',', '.'), align='R', ln=False)

            self.set_xy(ML, row_y + row_h)

        self.ln(3)

    # ── Testo AI / narrativa ───────────────────────────────────────
    def ai_text_block(self, text):
        for raw in clean_text(text).split('\n'):
            line = raw.strip()
            if not line or set(line) <= {'-', '=', '_', '|'}:
                self.ln(1.8)
                continue
            if line.startswith('|'):   # tabella markdown: ignorata (usare smart_table)
                continue
            self.ensure_space(10)
            if line[0] in '-*' or re.match(r'^\d+[.)]\s', line):
                testo = re.sub(r'^(\d+[.)]|[-*])\s*', '', line)
                self.set_font(FONT, '', 8.4)
                self.set_text_color(*self.accent)
                self.set_xy(ML + 1.5, self.get_y())
                self.cell(3.5, 4.8, '·', ln=False)
                self.set_text_color(52, 64, 84)
                self.set_x(ML + 5.5)
                self._write_wrap(testo, CONTENT_W - 6)
            elif line.isupper() and len(line) > 3:
                self.ln(2.5)
                self.set_font(FONT, 'B', 8.4)
                self.set_text_color(*self.accent)
                self.set_x(ML)
                self.cell(0, 5, line, new_x='LMARGIN', new_y='NEXT')
                self.ln(1)
            elif len(line) < 80 and line.endswith(':'):
                self.ln(1.5)
                self.set_font(FONT, 'B', 8.6)
                self.set_text_color(*C_DARK)
                self.set_x(ML)
                self.cell(0, 5, line.rstrip(':'), new_x='LMARGIN', new_y='NEXT')
                self.ln(0.8)
            else:
                self.set_font(FONT, '', 8.4)
                self.set_text_color(52, 64, 84)
                self.set_x(ML)
                self._write_wrap(line, CONTENT_W)
        self.ln(1)

    def _write_wrap(self, text, max_w):
        x0 = self.get_x()
        cur = ''
        for w in text.split():
            test = (cur + ' ' + w).strip()
            if self.get_string_width(test) <= max_w:
                cur = test
            else:
                if cur:
                    self.cell(max_w, 4.8, cur, new_x='LMARGIN', new_y='NEXT')
                    self.set_x(x0)
                cur = w
        if cur:
            self.cell(max_w, 4.8, cur, new_x='LMARGIN', new_y='NEXT')
            self.set_x(ML)
