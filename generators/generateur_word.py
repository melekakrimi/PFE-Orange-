# generators/generateur_word.py
"""
Générateur Word — 1 page document technique modifiable Orange Business
"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ORANGE = RGBColor(0xFF, 0x79, 0x00)
DARK   = RGBColor(0x33, 0x33, 0x33)
BLANC  = RGBColor(0xFF, 0xFF, 0xFF)


def generer_word(data: dict, textes: dict, chemin: str):
    doc = Document()

    for sec in doc.sections:
        sec.top_margin = sec.bottom_margin = Cm(1.8)
        sec.left_margin = sec.right_margin = Cm(2)

    # ── En-tête ───────────────────────────────────────────────────
    p = doc.add_paragraph()
    _run(p, "Orange Business", size=18, bold=True, color=ORANGE)
    _run(p, f"  ·  Tunisie  |  Proposition Commerciale Confidentielle", size=10, color=DARK)

    p2 = doc.add_paragraph()
    _run(p2, f"Client : ", size=9, bold=True, color=DARK)
    _run(p2, f"{data['client']}   |   Date : {data['date']}   |   Validité : {data['validite']}", size=9, color=DARK)
    _hr(doc)

    # ── Profil client ─────────────────────────────────────────────
    _h1(doc, "PROFIL CLIENT")
    t = doc.add_table(rows=2, cols=5)
    t.style = "Table Grid"
    hdrs = ["Entreprise", "Secteur", "Taille", "Budget/an", "Urgence"]
    vals = [data["client"], data["secteur"], data["taille"],
            f"{data['budget']:,.0f} TND" if data["budget"] else "—", data["urgence"].capitalize()]
    for j, (h, v) in enumerate(zip(hdrs, vals)):
        _cell(t, 0, j, h, bold=True, bg="FF7900", color=BLANC)
        _cell(t, 1, j, v)
    doc.add_paragraph()

    # ── Comparatif scénarios ──────────────────────────────────────
    _h1(doc, "COMPARATIF DES 3 SCÉNARIOS TARIFAIRES")
    sc = data["scenarios"]
    headers = ["Critère", "Compétitif", "Équilibré", "Premium"]
    rows = [
        ["Prix annuel (TND)"]      + [f"{x.get('prix_vente_total',0):,.0f}"   for x in sc],
        ["Coût de revient (TND)"]  + [f"{x.get('cout_revient_total',0):,.0f}" for x in sc],
        ["Marge brute (TND)"]      + [f"{x.get('marge_brute',0):,.0f}"        for x in sc],
        ["Taux de marge (%)"]      + [f"{x.get('taux_marge',0):.1f}%"         for x in sc],
        ["Dans le budget"]         + ["OUI" if x.get("dans_budget") else "NON" for x in sc],
        ["Marge ≥ 14%"]            + ["OK"  if x.get("contrainte_marge_ok") else "KO" for x in sc],
    ]
    _tableau(doc, headers, rows)
    doc.add_paragraph()

    # ── Recommandation ────────────────────────────────────────────
    _h1(doc, "RECOMMANDATION ORANGE BUSINESS")
    rec = data["rec"]
    p3 = doc.add_paragraph()
    _run(p3, f"Scénario {rec.get('nom_scenario','').upper()}", size=13, bold=True, color=ORANGE)
    _run(p3, f"   |   Prix : {rec.get('prix_vente_total',0):,.0f} TND/an"
                f"   |   Marge : {rec.get('taux_marge',0):.1f}%"
                f"   |   {'✓ Dans le budget' if rec.get('dans_budget') else 'Hors budget'}",
            size=11, color=DARK)

    synthese = textes.get("synthese") or data.get("pitch", "")
    if synthese:
        p4 = doc.add_paragraph()
        _run(p4, synthese, size=10, italic=True, color=DARK)

    args = data.get("arguments", [])
    if args:
        p5 = doc.add_paragraph()
        _run(p5, "Arguments de négociation : ", size=10, bold=True, color=DARK)
        for i, arg in enumerate(args, 1):
            pa = doc.add_paragraph(style="List Number")
            _run(pa, arg, size=10)
    doc.add_paragraph()

    # ── Conditions + Signature ────────────────────────────────────
    _hr(doc)
    p6 = doc.add_paragraph()
    _run(p6, "Conditions : ", size=9, bold=True, color=DARK)
    _run(p6, f"Durée 12/24 mois  |  Facturation mensuelle  |  Support 24h/24  |  Validité : {data['validite']}", size=9, color=DARK)

    _h1(doc, "BON POUR ACCORD")
    ts = doc.add_table(rows=4, cols=2)
    ts.style = "Table Grid"
    sig_rows = [
        ("Pour Orange Business Tunisie", "Pour le Client"),
        ("Nom : _________________________", "Nom : _________________________"),
        ("Date : ________________________", "Date : ________________________"),
        ("Signature & Cachet :\n\n\n",    "Signature & Cachet :\n\n\n"),
    ]
    for i, (l, r) in enumerate(sig_rows):
        _cell(ts, i, 0, l, bold=(i==0), color=ORANGE if i==0 else None)
        _cell(ts, i, 1, r, bold=(i==0), color=ORANGE if i==0 else None)

    _hr(doc)
    p7 = doc.add_paragraph()
    p7.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p7, "Orange Business Tunisie  |  Document confidentiel", size=8, italic=True, color=DARK)

    doc.save(chemin)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(para, texte, size=11, bold=False, italic=False, color=None):
    r = para.add_run(texte)
    r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
    if color: r.font.color.rgb = color

def _h1(doc, texte):
    p = doc.add_paragraph()
    _run(p, texte, size=12, bold=True, color=ORANGE)

def _hr(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single"); bot.set(qn("w:sz"), "6")
    bot.set(qn("w:space"), "1");   bot.set(qn("w:color"), "FF7900")
    pBdr.append(bot); pPr.append(pBdr)

def _tableau(doc, headers, rows):
    nb_c = len(headers)
    t = doc.add_table(rows=1+len(rows), cols=nb_c)
    t.style = "Table Grid"
    for j, h in enumerate(headers):
        _cell(t, 0, j, h, bold=True, bg="FF7900", color=BLANC)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            _cell(t, i+1, j, val, bg="F5F5F5" if i%2==0 else "FFFFFF")

def _cell(table, row, col, texte, bold=False, italic=False, color=None, bg=None):
    cell = table.cell(row, col)
    p    = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r    = p.add_run(str(texte))
    r.font.size = Pt(9); r.font.bold = bold; r.font.italic = italic
    if color: r.font.color.rgb = color if isinstance(color, RGBColor) else RGBColor.from_string(color) if len(str(color))==6 else color
    if bg:
        tc = cell._tc; tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), str(bg).replace("#",""))
        tcPr.append(shd)