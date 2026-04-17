# evaluation/evaluateur_agent3.py
"""
Evaluateur Agent 3 - Optimiseur de Prix et Marges
Metrique RAGAS : faithfulness
    → Le scenario recommande respecte-t-il le budget client ?
    → Les claims de budget dans la reponse sont-elles supportees par les chiffres ?
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness
from ragas.llms import LangchainLLMWrapper

from agents.agent_configurateur import AgentConfigurateur
from agents.agent_optimiseur import AgentOptimiseur

load_dotenv()


class EvaluateurAgent3:

    def __init__(self):
        self.agent_config     = AgentConfigurateur()
        self.agent_optimiseur = AgentOptimiseur()

        groq_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        self.metric_faithfulness = Faithfulness(llm=LangchainLLMWrapper(groq_llm))

    # ═══════════════════════════════════════════════════════════════
    # RAGAS — faithfulness
    # Verifie si le scenario recommande respecte le budget client
    # ═══════════════════════════════════════════════════════════════

    def evaluer_ragas(self, cas_avec_resultats: list) -> dict:
        """
        faithfulness : le scenario recommande respecte-t-il le budget client ?

        user_input         = description client avec budget annuel
        response           = scenario recommande + prix + verdict budget
        retrieved_contexts = [budget client + prix des 3 scenarios]
        reference          = le scenario recommande doit etre dans le budget
        """
        samples = []

        for item in cas_avec_resultats:
            cas       = item["cas"]
            resultat  = item["resultat"]
            scenarios = resultat.get("scenarios", [])
            rec       = resultat.get("recommandation", "economique")
            budget    = float(cas["input_agent1"].get("budget_annuel", 0) or 0)

            scenario_rec = next((s for s in scenarios if s["niveau"] == rec), None)
            if not scenario_rec:
                continue

            prix_rec    = scenario_rec.get("prix_vente_total", 0)
            dans_budget = prix_rec <= budget if budget > 0 else True
            taux_marge  = scenario_rec.get("taux_marge", 0)

            # Response : ce que Agent 3 affirme sur le budget
            response = (
                f"Le scenario {scenario_rec.get('nom_scenario', rec)} est recommande. "
                f"Prix annuel total : {prix_rec} TND. "
                f"Budget client declare : {budget} TND. "
                f"Dans le budget : {'Oui' if dans_budget else 'Non'}. "
                f"Taux de marge Orange : {taux_marge}%."
            )

            # Contexte : les chiffres reels des 3 scenarios
            contexte = (
                f"Budget annuel client : {budget} TND. "
                + " | ".join([
                    f"Scenario {s['nom_scenario']} : prix={s['prix_vente_total']} TND, "
                    f"marge={s['taux_marge']}%, dans_budget={s['dans_budget']}"
                    for s in scenarios
                ])
            )

            # Reference : ce qu'on attend
            reference = (
                f"Le scenario recommande doit avoir un prix inferieur ou egal "
                f"au budget de {budget} TND et un taux de marge >= 14%."
            )

            samples.append(SingleTurnSample(
                user_input=cas["description"],
                response=response,
                retrieved_contexts=[contexte],
                reference=reference
            ))

        if not samples:
            return {"faithfulness": 0.0}

        print("\n  Calcul RAGAS faithfulness (respect budget client)...")
        dataset = EvaluationDataset(samples=samples)
        scores  = evaluate(dataset=dataset, metrics=[self.metric_faithfulness])
        df      = scores.to_pandas()

        return {
            "faithfulness": round(float(df["faithfulness"].mean()), 4)
        }

    # ═══════════════════════════════════════════════════════════════
    # EVALUATION COMPLETE
    # ═══════════════════════════════════════════════════════════════

    def evaluer(self, fichier: str = "evaluation/cas_tests/cas_agent3.json") -> dict:
        with open(fichier, 'r', encoding='utf-8') as f:
            cas_tests = json.load(f)

        print(f"\n{'='*60}")
        print("  EVALUATION AGENT 3 — RAGAS faithfulness")
        print(f"{'='*60}")
        print(f"  Nombre de cas : {len(cas_tests)}\n")

        cas_avec_resultats = []

        for i, cas in enumerate(cas_tests, 1):
            print(f"  Cas {i}/{len(cas_tests)}...", end=" ", flush=True)
            try:
                agent1_data  = cas["input_agent1"]
                configs_ag2  = self.agent_config.configurer(agent1_data)
                resultat_ag3 = self.agent_optimiseur.optimiser(agent1_data, configs_ag2)

                scenarios    = resultat_ag3.get("scenarios", [])
                rec          = resultat_ag3.get("recommandation", "")
                budget       = float(agent1_data.get("budget_annuel", 0) or 0)
                scenario_rec = next((s for s in scenarios if s["niveau"] == rec), None)

                dans_budget = scenario_rec["prix_vente_total"] <= budget if (scenario_rec and budget > 0) else None
                marge_ok    = scenario_rec["contrainte_marge_ok"] if scenario_rec else False

                statut = "[OK]" if dans_budget and marge_ok else "[~]"
                print(f"{statut} budget={'OK' if dans_budget else 'KO'}  marge={'OK' if marge_ok else 'KO'}")

                cas_avec_resultats.append({"cas": cas, "resultat": resultat_ag3})

            except Exception as e:
                print(f"[ERREUR] {e}")

        # RAGAS
        ragas = self.evaluer_ragas(cas_avec_resultats)

        resultats = {"ragas": ragas}

        print(f"\n{'='*60}")
        print("  RESULTATS")
        print(f"{'='*60}")
        print(f"  faithfulness : {ragas['faithfulness']:.4f}  ({ragas['faithfulness']*100:.1f}%)")
        print(f"  Interpretation : respect des contraintes budget client")

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_agent3.json", 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        print(f"\n  Resultats sauvegardes : evaluation/resultats/resultats_agent3.json")

        return resultats


if __name__ == "__main__":
    EvaluateurAgent3().evaluer()