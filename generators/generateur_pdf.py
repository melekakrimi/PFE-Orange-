# generators/generateur_pdf.py
"""
Générateur PDF — Contrat commercial Orange Business, prêt à signer.
Format A4 formel, minimal, orienté signature client.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

ORANGE   = colors.HexColor("#FF7900")
SAUMON   = colors.HexColor("#FFCCAA")
SAUMON_L = colors.HexColor("#FFF5EC")
DARK     = colors.HexColor("#1A1A1A")
GRIS_M   = colors.HexColor("#E0E0E0")


def generer_pdf(data: dict, textes: dict, chemin: str):
    doc = SimpleDocTemplate(chemin, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm,  bottomMargin=2*cm)

    s_titre = ParagraphStyle("titre", fontSize=18, fontName="Helvetica-Bold",textColor=ORANGE, spaceAfter=2)
    s_sous  = ParagraphStyle("sous",  fontSize=10, fontName="Helvetica",textColor=DARK, spaceAfter=6)
    s_h1    = ParagraphStyle("h1",    fontSize=11, fontName="Helvetica-Bold",textColor=ORANGE, spaceBefore=10, spaceAfter=4)
    s_body  = ParagraphStyle("body",  fontSize=9,  fontName="Helvetica",textColor=DARK, spaceAfter=3, leading=14,alignment=TA_JUSTIFY)
    s_legal = ParagraphStyle("legal", fontSize=8,  fontName="Helvetica",textColor=DARK, spaceAfter=2, leading=12, alignment=TA_JUSTIFY)
    s_c     = ParagraphStyle("c",     fontSize=8,  fontName="Helvetica",textColor=DARK, alignment=TA_CENTER)

    def hr(): return HRFlowable(width="100%", thickness=1, color=ORANGE,spaceAfter=6, spaceBefore=4)
    def sp(h=0.3): return Spacer(1, h*cm)

    story = []

    # ── En-tête ───────────────────────────────────────────────────
    story.append(Paragraph("Orange Business", s_titre))
    story.append(Paragraph("Tunisie  |  Contrat de Prestation de Services", s_sous))
    story.append(hr())

    # Référence contrat
    story.append(_table(
        [["Référence", f"OBT-{data['date'].replace(' ', '').upper()}",
            "Date", data["date"],
            "Validité", data["validite"]]],
        [2.5*cm, 3.5*cm, 1.5*cm, 3*cm, 2*cm, 2*cm], footer=True
    ))
    story.append(sp())

    # ── Article 1 — Parties ───────────────────────────────────────
    story.append(Paragraph("ARTICLE 1 — PARTIES CONTRACTANTES", s_h1))
    story.append(_table(
        [["Prestataire", "Client"],
            ["Orange Business Tunisie\nSociété anonyme — Tunis, Tunisie\nICE : OBT-2024",
            f"{data['client']}\nSecteur : {data['secteur']}  |  Taille : {data['taille']}"]],
        [8.75*cm, 8.75*cm], sig=True
    ))
    story.append(sp())

    # ── Article 2 — Objet ─────────────────────────────────────────
    story.append(Paragraph("ARTICLE 2 — OBJET DU CONTRAT", s_h1))
    story.append(Paragraph(
        f"Le présent contrat a pour objet la fourniture par Orange Business Tunisie "
        f"des services de communication et cloud suivants à {data['client']} : "
        f"<b>{data['solutions']}</b>.",
        s_body
    ))
    story.append(sp(0.2))

    # ── Article 3 — Prestations ───────────────────────────────────
    story.append(Paragraph("ARTICLE 3 — DÉTAIL DES PRESTATIONS", s_h1))

    fibre = data.get("fibre")
    ms    = data.get("microsoft")

    rows = [["Prestation", "Spécification", "Durée", "Prix annuel (TND)"]]
    if fibre:
        rows.append([
            fibre.get("nom_offre", "Fibre FTTO"),
            f"{fibre.get('debit_mbps', '')} Mbps symétrique",
            f"{fibre.get('engagement_mois', '')} mois",
            f"{fibre.get('prix_annuel', 0):,.0f}",
        ])
    if ms:
        rows.append([
            ms.get("nom_produit", "Microsoft 365"),
            f"{ms.get('nombre_licences', '')} licences",
            "12 mois",
            f"{ms.get('prix_annuel', 0):,.0f}",
        ])

    story.append(_table(rows, [6*cm, 4*cm, 2.5*cm, 3*cm]))
    story.append(sp())

    # ── Article 4 — Prix ──────────────────────────────────────────
    story.append(Paragraph("ARTICLE 4 — CONDITIONS FINANCIÈRES", s_h1))
    prix_annuel  = data.get("prix_total_annuel", 0)
    prix_mensuel = round(prix_annuel / 12, 0)
    story.append(_table(
        [["Prix total annuel (TND HT)", "Équivalent mensuel (TND HT)", "Modalité"],
            [f"{prix_annuel:,.0f}", f"{prix_mensuel:,.0f}", "Facturation mensuelle"]],
        [5.83*cm, 5.83*cm, 5.83*cm]
    ))
    story.append(sp(0.2))
    story.append(Paragraph(
        "Les prix sont exprimés hors taxes. La TVA applicable sera ajoutée selon "
        "la réglementation en vigueur. Le paiement est dû dans un délai de 30 jours "
        "à compter de la date de facturation.",
        s_legal
    ))
    story.append(sp())

    # ── Article 5 — Durée ─────────────────────────────────────────
    story.append(Paragraph("ARTICLE 5 — DURÉE ET RÉSILIATION", s_h1))
    fibre_eng = fibre.get("engagement_mois", 12) if fibre else 12
    story.append(Paragraph(
        f"Le contrat est conclu pour une durée initiale de <b>{fibre_eng} mois</b> "
        f"à compter de la date de mise en service. À l'échéance, il sera reconduit "
        f"tacitement par période de 12 mois sauf résiliation notifiée par lettre "
        f"recommandée avec un préavis de 3 mois.",
        s_legal
    ))
    story.append(sp())

    # ── Article 6 — Engagement de service ────────────────────────
    story.append(Paragraph("ARTICLE 6 — ENGAGEMENTS DE SERVICE", s_h1))
    story.append(_table(
        [["Déploiement", "Support", "Disponibilité", "SLA"],
            ["Équipes Orange Business", "24h/24 — 7j/7", "99,5% garantie", "4h intervention"]],
        [4.37*cm] * 4, footer=True
    ))
    story.append(sp())

    # ── Signatures ────────────────────────────────────────────────
    story.append(hr())
    story.append(Paragraph("BON POUR ACCORD", s_h1))
    story.append(Paragraph(
        "Les parties soussignées reconnaissent avoir pris connaissance des conditions "
        "du présent contrat et s'engagent à les respecter.",
        s_legal
    ))
    story.append(sp(0.3))
    story.append(_table(
        [["Pour Orange Business Tunisie", "Pour le Client"],
            ["Nom : _________________________", "Nom : _________________________"],
            ["Fonction : ____________________", "Fonction : ____________________"],
            ["Date : ________________________", "Date : ________________________"],
            ["Signature & Cachet :\n\n\n\n",   "Signature & Cachet :\n\n\n\n"]],
        [8.75*cm, 8.75*cm], sig=True
    ))

    # ── Pied de page ──────────────────────────────────────────────
    story += [sp(), hr(),
                Paragraph(
                    "Orange Business Tunisie  |  Document contractuel confidentiel — "
                    "usage exclusif du destinataire",
                    s_c
                )]

    doc.build(story)


# ── Helper tableau ────────────────────────────────────────────────────────────

def _table(rows, col_widths, footer=False, sig=False):
    t = Table(rows, colWidths=col_widths)
    if sig:
        style = [
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, GRIS_M),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  ORANGE),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ]
    elif footer:
        style = [
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.3, GRIS_M),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
            ("TEXTCOLOR",     (0, 0), (-1, -1), DARK),
            ("BACKGROUND",    (0, 0), (-1, -1), SAUMON_L),
        ]
    else:
        style = [
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.3, GRIS_M),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND",    (0, 0), (-1, 0),  ORANGE),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, SAUMON]),
        ]
    t.setStyle(TableStyle(style))
    return t
