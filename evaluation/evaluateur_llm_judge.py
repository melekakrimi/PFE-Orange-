# evaluation/evaluateur_llm_judge.py
"""
LLM-as-Judge : évalue la qualité des pitchs commerciaux générés par Agent 3.
Le LLM joue le rôle d'un expert commercial senior qui note chaque pitch sur 3 critères.
"""

import os
import sys
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from agents.agent_configurateur import AgentConfigurateur
from agents.agent_optimiseur import AgentOptimiseur

load_dotenv()

PROMPT_JUGE = """
Tu es un expert commercial senior avec 15 ans d'expérience en vente B2B Telecom.
Tu évalues la qualité d'un pitch commercial généré automatiquement.

═══════════════════════════════════════════════════════
CONTEXTE DU CLIENT
═══════════════════════════════════════════════════════
Entreprise : {client}
Secteur    : {secteur}
Taille     : {taille}
Budget/an  : {budget} TND

═══════════════════════════════════════════════════════
SCÉNARIO RECOMMANDÉ
═══════════════════════════════════════════════════════
Scénario       : {nom_scenario}
Prix annuel    : {prix_annuel} TND
Taux de marge  : {taux_marge}%
Dans le budget : {dans_budget}

═══════════════════════════════════════════════════════
PITCH À ÉVALUER
═══════════════════════════════════════════════════════
{pitch}

═══════════════════════════════════════════════════════
CRITÈRES D'ÉVALUATION (note de 1 à 5)
═══════════════════════════════════════════════════════
1. pertinence_secteur (1-5) :
    Le pitch est-il adapté au secteur du client ?
    Utilise-t-il un vocabulaire et des arguments spécifiques à ce secteur ?
    5 = parfaitement adapté / 1 = générique, pourrait s'appliquer à n'importe qui

2. arguments_chiffres (1-5) :
    Le pitch utilise-t-il les vrais chiffres du scénario (prix, marge, économies) ?
    5 = chiffres concrets et précis / 1 = aucun chiffre, vague

3. ton_professionnel (1-5) :
    Le ton est-il commercial, convaincant et professionnel ?
    5 = excellent niveau commercial / 1 = amateur, maladroit

Réponds UNIQUEMENT avec le JSON suivant. Aucun texte avant ou après.

{{
    "pertinence_secteur": 0,
    "arguments_chiffres": 0,
    "ton_professionnel": 0,
    "score_global": 0.0,
    "commentaire": "Explication courte des points forts et points faibles"
}}
"""


class LLMJuge:

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        self.prompt = PromptTemplate(
            input_variables=["client", "secteur", "taille", "budget",
                                "nom_scenario", "prix_annuel", "taux_marge",
                                "dans_budget", "pitch"],
            template=PROMPT_JUGE
        )
        self.chain = self.prompt | self.llm
        self.agent_config = AgentConfigurateur()
        self.agent_optim  = AgentOptimiseur()

    def evaluer_cas(self, cas: dict) -> dict:
        """Évalue un cas de test complet."""
        analyse = cas["input_agent1"]
        nom     = analyse.get("nom_entreprise", "")
        print(f"\n  Cas {cas['id']} : {nom}")

        # Générer les scénarios
        try:
            configs   = self.agent_config.configurer(analyse)
            resultat  = self.agent_optim.optimiser(analyse, configs)
            scenarios = resultat["scenarios"]
            rec_niveau = resultat["recommandation"]
            rec = next(s for s in scenarios if s["niveau"] == rec_niveau)
        except Exception as e:
            print(f"    Erreur agents : {e}")
            return {"id": cas["id"], "erreur": str(e)}

        pitch = rec.get("pitch_commercial", "")
        if not pitch:
            print(f"    Pitch vide — cas ignoré")
            return {"id": cas["id"], "erreur": "pitch vide"}

        # Appel LLM juge
        try:
            reponse = self.chain.invoke({
                "client":       nom,
                "secteur":      analyse.get("secteur", ""),
                "taille":       analyse.get("taille_entreprise", ""),
                "budget":       f"{analyse.get('budget_annuel', 0):,}",
                "nom_scenario": rec.get("nom_scenario", ""),
                "prix_annuel":  f"{rec.get('prix_vente_total', 0):,.0f}",
                "taux_marge":   f"{rec.get('taux_marge', 0):.1f}",
                "dans_budget":  "Oui" if rec.get("dans_budget") else "Non",
                "pitch":        pitch,
            })
            brut = reponse.content.strip()
            m = re.search(r"\{.*\}", brut, re.DOTALL)
            note = json.loads(m.group()) if m else {}

            # Calculer score global = moyenne des 3 critères
            scores = [
                note.get("pertinence_secteur", 0),
                note.get("arguments_chiffres", 0),
                note.get("ton_professionnel", 0)
            ]
            note["score_global"] = round(sum(scores) / len(scores), 2)

            print(f"    Score global : {note['score_global']}/5")
            print(f"    Pertinence secteur  : {note.get('pertinence_secteur')}/5")
            print(f"    Arguments chiffres  : {note.get('arguments_chiffres')}/5")
            print(f"    Ton professionnel   : {note.get('ton_professionnel')}/5")
            print(f"    Commentaire : {note.get('commentaire', '')}")

            return {
                "id":                 cas["id"],
                "client":             nom,
                "secteur":            analyse.get("secteur", ""),
                "scenario":           rec.get("nom_scenario", ""),
                "pitch":              pitch,
                "pertinence_secteur": note.get("pertinence_secteur", 0),
                "arguments_chiffres": note.get("arguments_chiffres", 0),
                "ton_professionnel":  note.get("ton_professionnel", 0),
                "score_global":       note["score_global"],
                "commentaire":        note.get("commentaire", ""),
            }

        except Exception as e:
            print(f"    Erreur juge : {e}")
            return {"id": cas["id"], "erreur": str(e)}

    def evaluer_tous(self, chemin_cas: str, chemin_resultats: str):
        """Évalue tous les cas de test et sauvegarde les résultats."""
        with open(chemin_cas, encoding="utf-8") as f:
            cas_tests = json.load(f)

        print("\n" + "="*60)
        print("  LLM-AS-JUDGE — Évaluation qualité pitchs Agent 3")
        print("="*60)

        resultats = []
        for cas in cas_tests:
            r = self.evaluer_cas(cas)
            resultats.append(r)

        # Scores valides uniquement
        valides = [r for r in resultats if "score_global" in r]

        if valides:
            moy_global     = round(sum(r["score_global"]     for r in valides) / len(valides), 2)
            moy_pertinence = round(sum(r["pertinence_secteur"] for r in valides) / len(valides), 2)
            moy_chiffres   = round(sum(r["arguments_chiffres"] for r in valides) / len(valides), 2)
            moy_ton        = round(sum(r["ton_professionnel"]  for r in valides) / len(valides), 2)

            print("\n" + "="*60)
            print("  RÉSULTATS FINAUX")
            print("="*60)
            print(f"  Cas évalués         : {len(valides)}/{len(cas_tests)}")
            print(f"  Score global moyen  : {moy_global}/5")
            print(f"  Pertinence secteur  : {moy_pertinence}/5")
            print(f"  Arguments chiffrés  : {moy_chiffres}/5")
            print(f"  Ton professionnel   : {moy_ton}/5")
            print("="*60)

            rapport = {
                "methode":             "LLM-as-Judge",
                "modele_juge":         "llama-3.3-70b-versatile",
                "nb_cas":              len(cas_tests),
                "nb_valides":          len(valides),
                "moyennes": {
                    "score_global":       moy_global,
                    "pertinence_secteur": moy_pertinence,
                    "arguments_chiffres": moy_chiffres,
                    "ton_professionnel":  moy_ton,
                },
                "details": resultats
            }
        else:
            rapport = {"erreur": "Aucun cas valide", "details": resultats}

        os.makedirs(os.path.dirname(chemin_resultats), exist_ok=True)
        with open(chemin_resultats, "w", encoding="utf-8") as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False)

        print(f"\n  Résultats sauvegardés : {chemin_resultats}")
        return rapport


if __name__ == "__main__":
    juge = LLMJuge()
    juge.evaluer_tous(
        chemin_cas       = "evaluation/cas_tests/cas_agent3.json",
        chemin_resultats = "evaluation/resultats/resultats_llm_judge.json"
    )
