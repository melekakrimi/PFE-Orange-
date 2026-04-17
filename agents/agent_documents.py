# agents/agent_documents.py
"""
Agent 4 : Générateur de Documents Commerciaux

Technique : Instruction Following
- Le LLM reçoit le profil du client et les solutions choisies
- Il génère les textes narratifs personnalisés pour chaque slide
- Le générateur PPTX utilise ces textes + les données réelles (prix, plan, débit)
    pour produire une présentation au format Orange Business

Résultat : 1 fichier PPTX (charte Orange officielle)
"""

import os
import sys
import json
import re
from datetime import date
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.prompt_documents import TEMPLATE_DOCUMENTS
from generators.generateur_pptx import generer_pptx

load_dotenv()

# Noms des mois en français
MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]


class AgentDocuments:
    """
    Agent 4 : Génère la présentation commerciale PPTX au format Orange Business.

    Reçoit :
        analyse_agent1       → profil client (nom, secteur, taille, urgence)
        configuration_agent2 → solution exacte (Fibre + Microsoft)
        resultat_agent3      → prix, marge, pitch commercial

    Produit :
        Un fichier PPTX 9 slides, charte Orange #FF7900
    """

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.4,
        )
        self.prompt = PromptTemplate(
            input_variables=["client", "secteur", "taille", "solutions", "prix_annuel"],
            template=TEMPLATE_DOCUMENTS,
        )
        self.chain = self.prompt | self.llm

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def generer(self, analyse: dict, configuration: dict,
                resultat: dict, dossier_sortie: str = "output") -> dict:
        """
        Paramètres
        ----------
        analyse       : sortie Agent 1
        configuration : sortie Agent 2  (fibre, microsoft)
        resultat      : sortie Agent 3  (prix, marge, pitch, arguments)
        dossier_sortie: dossier de sauvegarde

        Retourne
        --------
        {"pptx": chemin_fichier}
        """
        print("\n" + "=" * 70)
        print(" Agent 4 — Génération de la présentation commerciale")
        print("=" * 70)

        os.makedirs(dossier_sortie, exist_ok=True)

        # 1. Construire le dictionnaire de données
        data = self._construire_data(analyse, configuration, resultat)

        # 2. Générer les textes via LLM
        textes = self._generer_textes(data)

        # 3. Générer le PPTX
        client_slug = re.sub(r"[^\w]", "_", data["client"])
        from datetime import datetime
        ts = datetime.now().strftime("%H%M%S")
        chemin_pptx = os.path.join(dossier_sortie, f"proposition_{client_slug}_{ts}.pptx")

        generer_pptx(data, textes, chemin_pptx)

        print(f"\n Présentation générée : {chemin_pptx}")
        return {"pptx": chemin_pptx}

    # ═══════════════════════════════════════════════════════════════
    # CONSTRUCTION DES DONNÉES
    # ═══════════════════════════════════════════════════════════════

    def _construire_data(self, analyse: dict, configuration: dict, resultat: dict) -> dict:
        """Consolide toutes les données pour le générateur PPTX."""
        a_fibre     = configuration.get("fibre") is not None
        a_microsoft = configuration.get("microsoft") is not None

        # Titre de l'offre selon les solutions
        if a_fibre and a_microsoft:
            titre_offre = "Connectivité & Cloud"
            sous_titre  = f"Fibre FTTO + Microsoft 365 pour {analyse.get('nom_entreprise', '')}"
        elif a_fibre:
            titre_offre = "Fibre Optique FTTO"
            sous_titre  = f"Connectivité haut débit pour {analyse.get('nom_entreprise', '')}"
        else:
            ms_nom      = (resultat.get("microsoft") or {}).get("nom_produit", "Microsoft 365")
            titre_offre = ms_nom
            sous_titre  = f"Solutions collaboratives pour {analyse.get('nom_entreprise', '')}"

        # Solutions texte pour le prompt LLM
        solutions_liste = []
        if a_fibre:
            debit = (resultat.get("fibre") or {}).get("debit_mbps", "")
            solutions_liste.append(f"Fibre {debit} Mbps")
        if a_microsoft:
            ms_nom = (resultat.get("microsoft") or {}).get("nom_produit", "Microsoft 365")
            nb_lic = (resultat.get("microsoft") or {}).get("nombre_licences", "")
            solutions_liste.append(f"{ms_nom} ({nb_lic} licences)")

        # Date en français
        today   = date.today()
        date_fr = f"{today.day} {MOIS_FR[today.month - 1]} {today.year}"

        return {
            # Infos client
            "client":   analyse.get("nom_entreprise", ""),
            "secteur":  analyse.get("secteur", ""),
            "taille":   analyse.get("taille_entreprise", ""),
            "urgence":  analyse.get("urgence", ""),
            "date":     date_fr,

            # Offre
            "titre_offre": titre_offre,
            "sous_titre":  sous_titre,
            "solutions":   " + ".join(solutions_liste),
            "a_fibre":     a_fibre,
            "a_microsoft": a_microsoft,

            # Détails Fibre (depuis Agent 3)
            "fibre":       resultat.get("fibre"),
            "fibre_debit": (resultat.get("fibre") or {}).get("debit_mbps", ""),

            # Détails Microsoft (depuis Agent 3)
            "microsoft":       resultat.get("microsoft"),
            "microsoft_plan":  (resultat.get("microsoft") or {}).get("nom_produit", ""),

            # Pricing
            "prix_total_annuel": resultat.get("prix_total_annuel", 0),
            "marge_brute":       resultat.get("marge_brute", 0),
            "taux_marge":        resultat.get("taux_marge", 0),

            # Pitch (depuis Agent 3)
            "pitch":     resultat.get("pitch_commercial", ""),
            "arguments": resultat.get("arguments_negociation", []),
        }

    # ═══════════════════════════════════════════════════════════════
    # GÉNÉRATION DES TEXTES VIA LLM
    # ═══════════════════════════════════════════════════════════════

    def _generer_textes(self, data: dict) -> dict:
        """Appelle le LLM pour générer les textes narratifs des slides."""
        print("  Génération des textes via LLM...")
        try:
            reponse = self.chain.invoke({
                "client":     data["client"],
                "secteur":    data["secteur"],
                "taille":     data["taille"],
                "solutions":  data["solutions"],
                "prix_annuel": f"{data['prix_total_annuel']:,.0f}",
            })
            textes = self._parser_json(reponse.content)
            print("  Textes générés avec succès")
            return textes
        except Exception as e:
            print(f"  Erreur LLM textes : {e} — utilisation du fallback")
            return self._fallback_textes(data)

    def _fallback_textes(self, data: dict) -> dict:
        """Textes par défaut si le LLM échoue."""
        client  = data["client"]
        secteur = data["secteur"]
        return {
            "pourquoi":         f"Orange Business propose à {client} une solution adaptée "
                                f"aux besoins du secteur {secteur}.",
            "benefice_1":       "Améliorez la productivité de vos équipes.",
            "benefice_2":       "Bénéficiez d'une connectivité fiable et sécurisée.",
            "benefice_3":       "Réduisez vos coûts IT avec une solution intégrée.",
            "cas_usage":        f"Une entreprise du secteur {secteur} a adopté cette "
                                "solution et a constaté +25% de productivité.",
            "securite":         "Orange Business garantit la sécurité de vos données "
                                "avec des protocoles certifiés.",
            "accompagnement_1": "Déploiement assuré par les équipes Orange Business.",
            "accompagnement_2": "Formation et prise en main de vos collaborateurs.",
            "accompagnement_3": "Support dédié et réactif pour votre activité.",
            "conclusion":       f"Nous restons à votre disposition pour finaliser "
                                f"cette offre avec {client}.",
        }

    def _parser_json(self, texte: str) -> dict:
        texte = texte.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", texte)
        if match:
            texte = match.group(1).strip()
        else:
            match = re.search(r"(\{[\s\S]*\})", texte)
            if match:
                texte = match.group(1).strip()
        return json.loads(texte)


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    from agents.agent_analyste      import AgentAnalyste
    from agents.agent_configurateur import AgentConfigurateur
    from agents.agent_optimiseur    import AgentOptimiseur

    print(" Test Agent 4 — Pipeline complet")
    print("=" * 70)

    a1 = AgentAnalyste()
    a2 = AgentConfigurateur()
    a3 = AgentOptimiseur()
    a4 = AgentDocuments()

    desc = """
    BIAT, secteur bancaire, 15 employes au siege.
    On veut la fibre 200 Mbps, boitier Orange a 80 metres.
    Et 15 licences Microsoft avec le mail, OneDrive et SharePoint
    pour les collaborateurs. Budget 50000 TND/an.
    """

    analyse = a1.analyser(desc)
    config  = a2.configurer(analyse)
    resultat = a3.optimiser(analyse, config)
    chemins = a4.generer(analyse, config, resultat, dossier_sortie="output")

    print("\n Fichiers générés :")
    for fmt, chemin in chemins.items():
        print(f"  [{fmt.upper()}] {chemin}")
    print("\n Test Agent 4 terminé !")
