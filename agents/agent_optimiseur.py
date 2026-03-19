# agents/agent_optimiseur.py
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
    Agent 3 : Synthétise les configurations Fibre + Microsoft de l'Agent 2,
    calcule les totaux par scénario, choisit la recommandation selon le budget
    et génère un pitch commercial personnalisé via LLM.

    BASE DE CALCUL :
    ================
    - Fibre    : prix_mensuel_total (mensuel, tel que retourné par l'Agent 2)
    - Microsoft: prix_total_mensuel (mensuel, tel que retourné par l'Agent 2)
    - Total mensuel = Fibre mensuel + Microsoft mensuel
    - Comparaison avec budget_mensuel de l'Agent 1
    """

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1   # FIX 3 : strict pour les calculs financiers
        )

        self.prompt = PromptTemplate(
            input_variables=[
                "description_client",
                "budget_mensuel",
                "scenario_recommande",
                "a_fibre",
                "a_microsoft",
                "dans_budget"
            ],
            template=TEMPLATE_OPTIMISEUR
        )

        self.chain = self.prompt | self.llm

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def optimiser(self, analyse_agent1: dict, configurations_agent2: dict) -> dict:
        """
        Méthode principale.

        Args:
            analyse_agent1        : dict retourné par AgentAnalyste.analyser()
            configurations_agent2 : dict retourné par AgentConfigurateur.configurer()

        Returns:
            dict avec les 3 scénarios + recommandation + pitch commercial
        """
        print("\n" + "=" * 70)
        print(" Synthèse et recommandation des offres Orange")
        print("=" * 70)

        fibre_data  = configurations_agent2.get("fibre", {})
        ms_data     = configurations_agent2.get("microsoft", {})
        budget      = float(analyse_agent1.get("budget_mensuel", 0) or 0)

        a_fibre     = isinstance(fibre_data.get("configurations"), list)
        a_microsoft = "configuration_economique" in ms_data

        # Construire les 3 scénarios
        fibre_configs = {}
        if a_fibre:
            for c in fibre_data["configurations"]:
                fibre_configs[c["niveau"]] = c

        ms_keys = {
            "economique": "configuration_economique",
            "standard":   "configuration_standard",
            "premium":    "configuration_premium"
        }

        scenarios = []
        for niveau in ["economique", "standard", "premium"]:
            scenario = self._construire_scenario(
                niveau       = niveau,
                fibre_config = fibre_configs.get(niveau) if a_fibre else None,
                ms_config    = ms_data.get(ms_keys[niveau]) if a_microsoft else None,
                budget       = budget
            )
            scenarios.append(scenario)

        # Choisir la recommandation
        recommandation = self._choisir_recommandation(scenarios, budget)

        # Générer le pitch pour le scénario recommandé
        scenario_rec = next(s for s in scenarios if s["niveau"] == recommandation)
        pitch_data   = self._generer_pitch(
            analyse_agent1, scenario_rec, a_fibre, a_microsoft
        )

        # Injecter le pitch dans le scénario recommandé
        scenario_rec["pitch_commercial"]      = pitch_data.get("pitch_commercial", "")
        scenario_rec["arguments_negociation"] = pitch_data.get("arguments_negociation", [])

        print(f" Recommandation : niveau '{recommandation}'")

        return {
            "scenarios":      scenarios,
            "recommandation": recommandation,
            "raison":         pitch_data.get("raison_recommandation", ""),
        }

    # ═══════════════════════════════════════════════════════════════
    # CONSTRUCTION D'UN SCÉNARIO
    # ═══════════════════════════════════════════════════════════════

    def _construire_scenario(
        self,
        niveau: str,
        fibre_config,
        ms_config,
        budget: float
    ) -> dict:
        """Calcule les totaux pour un scénario donné."""

        # ── Fibre ──────────────────────────────────────────────────
        fibre_mensuel = 0.0
        fibre_detail  = None
        if fibre_config:
            fibre_mensuel = float(fibre_config.get("prix_mensuel_total", 0))
            fibre_detail  = {
                "nom_offre":         str(fibre_config.get("nom_offre", "")),
                "debit_mbps":        int(fibre_config.get("debit_mbps", 0)),
                "prix_mensuel":      round(fibre_mensuel, 2),
                "cout_installation": float(fibre_config.get("cout_installation", 0)),
                "engagement_mois":   int(fibre_config.get("engagement_mois", 12)),
            }

        # ── Microsoft ──────────────────────────────────────────────
        # FIX 2 : utilise prix_total_mensuel (pas prix_total_annuel)
        ms_mensuel = 0.0
        ms_annuel  = 0.0
        ms_detail  = None
        if ms_config:
            ms_mensuel = float(ms_config.get("prix_total_mensuel", 0))
            ms_annuel  = round(ms_mensuel * 12, 2)
            ms_detail  = {
                "nom_produit":       str(ms_config.get("nom_produit", "")),
                "product_id":        str(ms_config.get("product_id", "")),
                "nombre_licences":   int(ms_config.get("nombre_licences", 0)),
                "prix_unitaire_tnd": float(ms_config.get("prix_unitaire_tnd", 0)),
                "prix_mensuel":      round(ms_mensuel, 2),
                "prix_annuel":       ms_annuel,
            }

        total_mensuel = round(fibre_mensuel + ms_mensuel, 2)
        total_annuel  = round(total_mensuel * 12, 2)
        dans_budget   = budget > 0 and total_mensuel <= budget

        return {
            "niveau":                niveau,
            "fibre":                 fibre_detail,
            "microsoft":             ms_detail,
            "total_mensuel":         total_mensuel,
            "total_annuel":          total_annuel,
            "dans_budget":           dans_budget,
            "pitch_commercial":      "",
            "arguments_negociation": [],
        }

    # ═══════════════════════════════════════════════════════════════
    # RECOMMANDATION
    # ═══════════════════════════════════════════════════════════════

    def _choisir_recommandation(self, scenarios: list, budget: float) -> str:
        """
        Logique de recommandation :
        - Standard si dans le budget
        - Économique si le standard dépasse le budget
        - Premium si le budget permet un large confort
        """
        if budget <= 0:
            return "standard"

        totaux      = {s["niveau"]: s["total_mensuel"] for s in scenarios}
        dans_budget = {s["niveau"]: s["dans_budget"]   for s in scenarios}

        if dans_budget.get("premium"):
            if (totaux["premium"] - totaux["standard"]) < budget * 0.25:
                return "premium"

        if dans_budget.get("standard"):
            return "standard"

        if dans_budget.get("economique"):
            return "economique"

        return "economique"

    # ═══════════════════════════════════════════════════════════════
    # PITCH COMMERCIAL VIA LLM
    # ═══════════════════════════════════════════════════════════════

    def _generer_pitch(
        self,
        analyse_agent1: dict,
        scenario: dict,
        a_fibre: bool,
        a_microsoft: bool
    ) -> dict:
        """Appelle le LLM pour générer le pitch commercial."""
        print("  🎯 Génération du pitch commercial...")

        inputs = {
            "description_client":  self._construire_description(analyse_agent1),
            "budget_mensuel":      analyse_agent1.get("budget_mensuel", "Non spécifié"),
            "scenario_recommande": json.dumps(scenario, indent=2, ensure_ascii=False),
            "a_fibre":             "Oui" if a_fibre else "Non",
            "a_microsoft":         "Oui" if a_microsoft else "Non",
            "dans_budget":         "Oui" if scenario["dans_budget"] else "Non (à discuter)"
        }

        try:
            resultat = self.chain.invoke(inputs)
            return self._parser_json(resultat.content)
        except Exception as e:
            print(f"  ⚠️  Erreur pitch LLM : {e}")
            return {
                "pitch_commercial":      "Offre personnalisée Orange Business.",
                "arguments_negociation": [],
                "raison_recommandation": "Meilleur rapport qualité/prix pour ce profil."
            }

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════════

    def _construire_description(self, analyste: dict) -> str:
        """Construit un résumé du profil client pour le prompt"""
        lignes = [
            f"Entreprise  : {analyste.get('nom_entreprise', 'Non spécifié')}",
            f"Secteur     : {analyste.get('secteur', 'Non spécifié')}",
            f"Taille      : {analyste.get('taille_entreprise', 'Non spécifié')}",
            f"Nombre sites: {analyste.get('nombre_sites', 1)}",
            f"Urgence     : {analyste.get('urgence', 'moyen')}",
        ]
        return "\n".join(lignes)

    def _parser_json(self, texte: str) -> dict:
        """Extrait le JSON depuis la réponse du LLM"""
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
# TESTS
# ============================================
if __name__ == "__main__":

    # FIX 1 : NumpyEncoder supprimé — n'existe pas dans agent_configurateur
    from agents.agent_analyste      import AgentAnalyste
    from agents.agent_configurateur import AgentConfigurateur

    print("🧪 Tests de l'Agent 3 - Optimiseur de Prix")
    print("=" * 70)

    agent_analyste      = AgentAnalyste()
    agent_configurateur = AgentConfigurateur()
    agent_optimiseur    = AgentOptimiseur()

    # ── Test 1 : Startup Fibre + Microsoft ──────────────────────────
    print("\n📋 TEST 1 : Startup (Fibre 200 Mbps + Microsoft 25 licences)")
    print("-" * 70)

    desc1 = """
    DevSoft, entreprise tech (PME, 25 employés).
    On déménage : fibre 200 Mbps minimum et 25 licences Microsoft 365
    avec Teams et Word. Budget : 2000 TND/mois. Urgence élevée.
    """
    analyse1 = agent_analyste.analyser(desc1)
    configs1 = agent_configurateur.configurer(analyse1)
    result1  = agent_optimiseur.optimiser(analyse1, configs1)

    print("\n📄 RÉSULTATS :")
    # FIX 1 : cls=NumpyEncoder supprimé
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # ── Test 2 : Cabinet Microsoft uniquement ───────────────────────
    print("\n\n📋 TEST 2 : Cabinet comptable (Microsoft uniquement)")
    print("-" * 70)

    desc2 = """
    Cabinet Tunis Audit, 12 comptables.
    Besoin de Microsoft 365 avec Excel, Word et OneDrive.
    Budget : 500 TND/mois.
    """
    analyse2 = agent_analyste.analyser(desc2)
    configs2 = agent_configurateur.configurer(analyse2)
    result2  = agent_optimiseur.optimiser(analyse2, configs2)

    print("\n📄 RÉSULTATS :")
    # FIX 1 : cls=NumpyEncoder supprimé
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    print("\n\n" + "=" * 70)
    print("✅ Tests Agent 3 terminés !")