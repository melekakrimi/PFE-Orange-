# generators/generateur_pdf.py
"""
Générateur PDF — 1 page A4 charte Orange Business
Proposition commerciale prête à signer.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

ORANGE = colors.HexColor("#FF7900")
GRIS   = colors.HexColor("#F5F5F5")
GRIS_M = colors.HexColor("#E0E0E0")
DARK   = colors.HexColor("#333333")


def generer_pdf(data: dict, textes: dict, chemin: str):
    doc = SimpleDocTemplate(chemin, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm,  bottomMargin=1.5*cm)

    s_h1  = ParagraphStyle("h1",  fontSize=12, fontName="Helvetica-Bold", textColor=ORANGE, spaceBefore=8, spaceAfter=3)
    s_txt = ParagraphStyle("txt", fontSize=9,  fontName="Helvetica",      textColor=colors.black, spaceAfter=3, leading=13)
    s_it  = ParagraphStyle("it",  fontSize=9,  fontName="Helvetica-Oblique", textColor=DARK, spaceAfter=3, leading=13)
    s_c   = ParagraphStyle("c",   fontSize=8,  fontName="Helvetica",      textColor=DARK, alignment=TA_CENTER)

    def hr(): return HRFlowable(width="100%", thickness=1.2, color=ORANGE, spaceAfter=4, spaceBefore=2)
    def sp(): return Spacer(1, 0.25*cm)

    story = []

    # ── En-tête ───────────────────────────────────────────────────
    story += [
        Paragraph('<font color="#FF7900" size="20"><b>Orange Business</b></font> '
                    '<font color="#333333" size="10">· Tunisie  |  Proposition Commerciale Confidentielle</font>',
                    ParagraphStyle("hdr", fontSize=10, fontName="Helvetica", spaceAfter=2)),
        Paragraph(f'Client : <b>{data["client"]}</b>   |   '
                    f'Date : {data["date"]}   |   Validité : {data["validite"]}',
                    ParagraphStyle("meta", fontSize=9, fontName="Helvetica", textColor=DARK, spaceAfter=4)),
        hr(),
    ]

    # ── Profil client (1 ligne compacte) ──────────────────────────
    story.append(Paragraph("PROFIL CLIENT", s_h1))
    story.append(_table(
        [["Entreprise", data["client"], "Secteur", data["secteur"],
            "Taille", data["taille"], "Sites", str(data["sites"]),
            "Budget/an", f"{data['budget']:,.0f} TND" if data["budget"] else "—"]],
        [2.5*cm,3*cm,1.8*cm,2.5*cm,1.5*cm,2.5*cm,1.3*cm,1*cm,2*cm,2.4*cm],
        profil=True))
    story.append(sp())

    # ── Comparatif 3 scénarios ────────────────────────────────────
    story.append(Paragraph("COMPARATIF DES 3 SCÉNARIOS TARIFAIRES", s_h1))
    sc = data["scenarios"]
    story.append(_table(
        [["Critère", "Compétitif", "Équilibré", "Premium"]] + [
            ["Prix annuel (TND)"]      + [f"{x.get('prix_vente_total',0):,.0f}"   for x in sc],
            ["Coût de revient (TND)"]  + [f"{x.get('cout_revient_total',0):,.0f}" for x in sc],
            ["Marge brute (TND)"]      + [f"{x.get('marge_brute',0):,.0f}"        for x in sc],
            ["Taux de marge (%)"]      + [f"{x.get('taux_marge',0):.1f}%"         for x in sc],
            ["Dans le budget"]         + ["OUI" if x.get("dans_budget") else "NON" for x in sc],
            ["Marge ≥ 14%"]            + ["OK"  if x.get("contrainte_marge_ok") else "KO" for x in sc],
        ], [6*cm, 3.83*cm, 3.83*cm, 3.83*cm]))
    story.append(sp())

    # ── Recommandation ────────────────────────────────────────────
    story.append(Paragraph("RECOMMANDATION ORANGE BUSINESS", s_h1))
    rec = data["rec"]
    story.append(_table(
        [[f"Scénario {rec.get('nom_scenario','').upper()}",
            f"Prix annuel : {rec.get('prix_vente_total',0):,.0f} TND",
            f"Marge : {rec.get('taux_marge',0):.1f}%",
            "✓ Dans le budget" if rec.get("dans_budget") else "Hors budget"]],
        [4.37*cm]*4, highlight=True))
    story.append(sp())

    # Synthèse LLM
    synthese = textes.get("synthese") or data.get("pitch", "")
    if synthese:
        story.append(Paragraph(synthese, s_it))
        story.append(sp())

    # Arguments
    args = data.get("arguments", [])
    if args:
        story.append(Paragraph("Arguments de négociation :", ParagraphStyle("ah", fontSize=9, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=2)))
        for i, arg in enumerate(args, 1):
            story.append(Paragraph(f"<b>{i}.</b>  {arg}", s_txt))
    story.append(sp())

    # ── Conditions + Signature ────────────────────────────────────
    story.append(hr())
    story.append(_table(
        [["Durée : 12 ou 24 mois", "Facturation mensuelle", "Support 24h/24", f"Validité : {data['validite']}"]],
        [4.37*cm]*4, footer=True))
    story.append(sp())

    story.append(Paragraph("BON POUR ACCORD", s_h1))
    story.append(_table(
        [["Pour Orange Business Tunisie", "Pour le Client"],
            ["Nom : _________________________", "Nom : _________________________"],
            ["Date : ________________________", "Date : ________________________"],
            ["Signature & Cachet :\n\n\n",     "Signature & Cachet :\n\n\n"]],
        [8.75*cm, 8.75*cm], sig=True))

    story += [sp(), hr(),
                Paragraph("Orange Business Tunisie  |  Proposition confidentielle — usage exclusif du destinataire", s_c)]

    doc.build(story)


def _table(rows, col_widths, highlight=False, profil=False, footer=False, sig=False):
    t = Table(rows, colWidths=col_widths)
    style = [
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("GRID",          (0,0),(-1,-1), 0.3, GRIS_M),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
    ]
    if highlight:
        style += [("BACKGROUND",(0,0),(-1,-1),ORANGE),
                    ("TEXTCOLOR",(0,0),(-1,-1),colors.white),
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold")]
    elif profil:
        style += [("FONTNAME",(0,0),(-2,0),"Helvetica-Bold"),
                    ("TEXTCOLOR",(0,0),(0,0),"#FF7900"),
                    ("ROWBACKGROUNDS",(0,0),(-1,-1),[GRIS])]
    elif footer:
        style += [("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                    ("TEXTCOLOR",(0,0),(-1,-1),DARK),
                    ("BACKGROUND",(0,0),(-1,-1),GRIS)]
    elif sig:
        style += [("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                    ("TEXTCOLOR",(0,0),(-1,0),ORANGE),
                    ("VALIGN",(0,0),(-1,-1),"TOP"),
                    ("ALIGN",(0,0),(-1,-1),"LEFT")]
    else:
        style += [("BACKGROUND",(0,0),(-1,0),ORANGE),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                    ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
                    ("ALIGN",(0,1),(0,-1),"LEFT"),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,GRIS])]
    t.setStyle(TableStyle(style))
    return t