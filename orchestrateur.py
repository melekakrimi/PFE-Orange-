# orchestrateur.py
"""
Orchestrateur du système multi-agents Orange Business

Pipeline complet : Agent 1 → Agent 2 → Agent 3 → Agent 4 → Base de données

Usage :
    python orchestrateur.py
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.agent_analyste      import AgentAnalyste
from agents.agent_configurateur import AgentConfigurateur
from agents.agent_optimiseur    import AgentOptimiseur
from agents.agent_documents     import AgentDocuments
from database.db_manager        import (sauvegarder_client,
                                        sauvegarder_proposition,
                                        sauvegarder_documents,
                                        sauvegarder_log)


def lancer(description_client: str, dossier_sortie: str = "output") -> dict:
    """
    Lance le pipeline complet pour une description client.

    Paramètres
    ----------
    description_client : rapport rédigé par le commercial
    dossier_sortie     : dossier où sauvegarder le PPTX

    Retourne
    --------
    dict avec tous les résultats + chemin du fichier généré
    """

    print("\n" + "█" * 70)
    print("  ORANGE BUSINESS — SYSTÈME MULTI-AGENTS")
    print("█" * 70)

    # ── Agent 1 : Analyse des besoins ─────────────────────────────
    print("\n[1/4] Agent Analyste...")
    agent1  = AgentAnalyste()
    analyse = agent1.analyser(description_client)

    if "erreur" in analyse:
        print(f" Erreur Agent 1 : {analyse['erreur']}")
        return {"erreur": analyse["erreur"]}

    # ── Agent 2 : Configuration Fibre + Microsoft ─────────────────
    print("\n[2/4] Agent Configurateur...")
    agent2        = AgentConfigurateur()
    configuration = agent2.configurer(analyse)

    # ── Agent 3 : Calcul marges + pitch commercial ─────────────────
    print("\n[3/4] Agent Optimiseur...")
    agent3   = AgentOptimiseur()
    resultat = agent3.optimiser(analyse, configuration)

    # ── Agent 4 : Génération PPTX ─────────────────────────────────
    print("\n[4/4] Agent Documents...")
    agent4   = AgentDocuments()
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    dossier  = os.path.join(dossier_sortie, ts)
    chemins  = agent4.generer(analyse, configuration, resultat, dossier)

    # ── Sauvegarde en base de données ─────────────────────────────
    print("\n Sauvegarde en base de données...")
    try:
        client_id      = sauvegarder_client(analyse)
        proposition_id = sauvegarder_proposition(
            client_id, analyse, resultat, description_client
        )
        sauvegarder_documents(proposition_id, chemins)
        sauvegarder_log(proposition_id, "orchestrateur", "succes")
        print(f" Proposition #{proposition_id} sauvegardée")
    except Exception as e:
        print(f" Avertissement DB : {e} (résultats disponibles quand même)")
        proposition_id = None

    # ── Résumé final ───────────────────────────────────────────────
    print("\n" + "█" * 70)
    print("  RÉSULTATS FINAUX")
    print("█" * 70)
    print(f"  Client      : {analyse.get('nom_entreprise', '')}")
    print(f"  Secteur     : {analyse.get('secteur', '')}")
    if resultat.get("fibre"):
        f = resultat["fibre"]
        print(f"  Fibre       : {f.get('debit_mbps','')} Mbps — "
                f"{f.get('prix_annuel', 0):,.0f} TND/an")
    if resultat.get("microsoft"):
        m = resultat["microsoft"]
        print(f"  Microsoft   : {m.get('nom_produit','')} x{m.get('nombre_licences','')} — "
                f"{m.get('prix_annuel', 0):,.0f} TND/an")
    print(f"  Prix total  : {resultat.get('prix_total_annuel', 0):,.2f} TND/an")
    print(f"  Marge       : {resultat.get('taux_marge', 0):.1f}%")
    print(f"  Présentation: {chemins.get('pptx', '')}")
    print("█" * 70)

    return {
        "analyse":        analyse,
        "configuration":  configuration,
        "resultat":       resultat,
        "documents":      chemins,
        "proposition_id": proposition_id,
    }


# ============================================
# TEST
# ============================================
if __name__ == "__main__":

    description = """
    Client BIAT, secteur bancaire, 15 employes au siege de Tunis.
    Ils veulent la fibre 200 Mbps, le boitier Orange est a 80 metres.
    Aussi 15 licences Microsoft avec le mail, OneDrive et SharePoint
    pour les collaborateurs. Budget annuel 50000 TND. Urgence haute.
    """

    resultats = lancer(description)