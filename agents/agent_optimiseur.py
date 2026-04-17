# agents/agent_optimiseur.py
"""
Agent 3 : Optimiseur de Prix et Marges

Technique : Constrained Prompting
- Reçoit la configuration unique d'Agent 2 (Fibre + Microsoft)
- Calcule les coûts, prix de vente et marges de façon déterministe
- Vérifie la contrainte Orange (marge >= 14%)
- Génère un pitch commercial personnalisé via LLM
"""

import os
import sys
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.prompt_optimiseur import TEMPLATE_OPTIMISEUR

load_dotenv()


class AgentOptimiseur:
    """
    Agent 3 : Calcule la rentabilité de la configuration et génère le pitch.

    CALCUL MARGE :
        Fibre     : marge_pct = marge_tnd / revenu_total_engagement × 100
        Microsoft : marge fixe 14% (prix_vente = cout × 1.14)
        Total     : taux_marge = marge_brute / prix_vente_total × 100

    CONTRAINTE Orange : taux_marge >= 14%
    """

    MARGE_MIN_PCT = 14.0
    MARGE_MS_PCT  = 14.0

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )

        self.prompt = PromptTemplate(
            input_variables=[
                "description_client",
                "configuration_json",
                "cout_total",
                "prix_total",
                "marge_brute",
                "taux_marge",
                "marge_ok",
            ],
            template=TEMPLATE_OPTIMISEUR
        )

        self.chain = self.prompt | self.llm

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def optimiser(self, analyse_agent1: dict, configuration_agent2: dict) -> dict:
        """
        Args:
            analyse_agent1       : dict retourné par AgentAnalyste.analyser()
            configuration_agent2 : dict retourné par AgentConfigurateur.configurer()
        Returns:
            dict avec coûts/marges calculés + pitch commercial
        """
        print("\n" + "=" * 70)
        print(" Calcul de la rentabilité et génération du pitch")
        print("=" * 70)

        fibre_data = configuration_agent2.get("fibre")
        ms_data    = configuration_agent2.get("microsoft")

        # ── Calcul des coûts et prix (déterministe) ────────────────
        fibre_cout_annuel, fibre_prix_annuel, fibre_detail = self._calculer_fibre(fibre_data)
        ms_cout_annuel,    ms_prix_annuel,    ms_detail    = self._calculer_microsoft(ms_data)

        cout_total  = round(fibre_cout_annuel + ms_cout_annuel, 2)
        prix_total  = round(fibre_prix_annuel + ms_prix_annuel, 2)
        marge_brute = round(prix_total - cout_total, 2)
        taux_marge  = round(marge_brute / prix_total * 100, 1) if prix_total > 0 else 0.0
        marge_ok    = taux_marge >= self.MARGE_MIN_PCT

        print(f"  Cout total annuel  : {cout_total} TND")
        print(f"  Prix total annuel  : {prix_total} TND")
        print(f"  Marge brute        : {marge_brute} TND")
        print(f"  Taux de marge      : {taux_marge}%  "
                f"({'OK' if marge_ok else 'ATTENTION < 14%'})")

        # ── Pitch commercial via LLM ───────────────────────────────
        pitch = self._generer_pitch(
            analyse_agent1, fibre_detail, ms_detail,
            cout_total, prix_total, marge_brute, taux_marge, marge_ok
        )

        return {
            "fibre":             fibre_detail,
            "microsoft":         ms_detail,
            "cout_total_annuel": cout_total,
            "prix_total_annuel": prix_total,
            "marge_brute":       marge_brute,
            "taux_marge":        taux_marge,
            "contrainte_ok":     marge_ok,
            "pitch_commercial":       pitch.get("pitch_commercial", ""),
            "arguments_negociation":  pitch.get("arguments_negociation", []),
            "raison_recommandation":  pitch.get("raison_recommandation", ""),
        }

    # ═══════════════════════════════════════════════════════════════
    # CALCULS DÉTERMINISTES
    # ═══════════════════════════════════════════════════════════════

    def _calculer_fibre(self, fibre_data: dict):
        """Extrait les coûts et prix annuels de la config Fibre d'Agent 2."""
        if not fibre_data:
            return 0.0, 0.0, None

        engagement_mois     = max(int(fibre_data.get("engagement_mois", 24)), 1)
        cout_initial        = float(fibre_data.get("cout_initial_total", 0))
        cout_mensuel        = float(fibre_data.get("cout_mensuel_total", 0))
        prix_mensuel        = float(fibre_data.get("prix_mensuel_total", 0))

        # cout_initial est one-time → on l'amortit sur la durée d'engagement
        cout_initial_annuel = round(cout_initial * 12 / engagement_mois, 2)
        fibre_cout_annuel   = round(cout_initial_annuel + cout_mensuel * 12, 2)
        fibre_prix_annuel   = round(prix_mensuel * 12, 2)

        detail = {
            "nom_offre":          fibre_data.get("nom_offre", ""),
            "debit_mbps":         fibre_data.get("debit_mbps", 0),
            "engagement_mois":    engagement_mois,
            "distance_metres":    fibre_data.get("distance_metres", 0),
            "cout_initial_total": cout_initial,
            "cout_mensuel_total": cout_mensuel,
            "prix_mensuel_total": prix_mensuel,
            "prix_annuel":        fibre_prix_annuel,
            "marge_pct_fibre":    fibre_data.get("marge_pct", 0),
        }
        return fibre_cout_annuel, fibre_prix_annuel, detail

    def _calculer_microsoft(self, ms_data: dict):
        """Extrait les coûts et prix annuels de la config Microsoft d'Agent 2."""
        if not ms_data:
            return 0.0, 0.0, None

        ms_prix_annuel = float(ms_data.get("prix_total_annuel", 0))
        ms_cout_annuel = round(ms_prix_annuel / (1 + self.MARGE_MS_PCT / 100), 2)

        detail = {
            "nom_produit":       ms_data.get("nom_produit", ""),
            "product_id":        ms_data.get("product_id", ""),
            "nombre_licences":   ms_data.get("nombre_licences", 0),
            "prix_unitaire_tnd": ms_data.get("prix_unitaire_tnd", 0),
            "prix_annuel":       ms_prix_annuel,
            "cout_annuel":       ms_cout_annuel,
        }
        return ms_cout_annuel, ms_prix_annuel, detail

    # ═══════════════════════════════════════════════════════════════
    # PITCH COMMERCIAL VIA LLM
    # ═══════════════════════════════════════════════════════════════

    def _generer_pitch(
        self,
        analyse_agent1: dict,
        fibre_detail,
        ms_detail,
        cout_total: float,
        prix_total: float,
        marge_brute: float,
        taux_marge: float,
        marge_ok: bool,
    ) -> dict:
        print("  Generation du pitch commercial...")

        config_resume = {}
        if fibre_detail:
            config_resume["fibre"] = {
                "offre":      fibre_detail["nom_offre"],
                "debit":      f"{fibre_detail['debit_mbps']} Mbps",
                "engagement": f"{fibre_detail['engagement_mois']} mois",
                "prix_annuel": fibre_detail["prix_annuel"],
            }
        if ms_detail:
            config_resume["microsoft"] = {
                "plan":              ms_detail["nom_produit"],
                "licences":          ms_detail["nombre_licences"],
                "prix_total_annuel": ms_detail["prix_annuel"],
            }

        inputs = {
            "description_client":  self._construire_description(analyse_agent1),
            "configuration_json":  json.dumps(config_resume, indent=2, ensure_ascii=False),
            "cout_total":          cout_total,
            "prix_total":          prix_total,
            "marge_brute":         marge_brute,
            "taux_marge":          taux_marge,
            "marge_ok":            "Oui" if marge_ok else "Non (attention requise)",
        }

        try:
            resultat = self.chain.invoke(inputs)
            return self._parser_json(resultat.content)
        except Exception as e:
            print(f"  Erreur pitch LLM : {e}")
            return {
                "pitch_commercial":      "Solution Orange Business personnalisée pour votre activité.",
                "arguments_negociation": [],
                "raison_recommandation": "Solution adaptée exactement à vos besoins.",
            }

    # ═══════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════════

    def _construire_description(self, analyste: dict) -> str:
        return "\n".join([
            f"Entreprise : {analyste.get('nom_entreprise', 'Non specifie')}",
            f"Secteur    : {analyste.get('secteur', 'Non specifie')}",
            f"Taille     : {analyste.get('taille_entreprise', 'Non specifie')}",
            f"Urgence    : {analyste.get('urgence', 'moyen')}",
        ])

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

    print(" Test Agent 3 - Optimiseur")
    print("=" * 70)

    a1 = AgentAnalyste()
    a2 = AgentConfigurateur()
    a3 = AgentOptimiseur()

    desc = """
    DevSoft, entreprise tech, PME, 20 employes.
    On demenage dans de nouveaux bureaux. On a besoin de la fibre 200 Mbps,
    boitier Orange a 80 metres. Et 20 licences Microsoft avec Teams, OneDrive
    et le Pack Office pour les developpeurs. Budget 26000 TND/an.
    """

    analyse = a1.analyser(desc)
    config  = a2.configurer(analyse)
    result  = a3.optimiser(analyse, config)

    print("\n RESULTATS :")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n Test Agent 3 termine !")