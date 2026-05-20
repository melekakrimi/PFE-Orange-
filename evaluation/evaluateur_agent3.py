# evaluation/evaluateur_agent3.py
"""
Evaluateur Agent 3 - Optimiseur de Prix et Marges
Metrique RAGAS : faithfulness
    → La configuration respecte-t-elle la contrainte marge >= 14% ?
    → Les calculs prix/coût/marge sont-ils cohérents ?
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
    # Verifie si la configuration respecte la contrainte marge >= 14%
    # ═══════════════════════════════════════════════════════════════

    def evaluer_ragas(self, cas_avec_resultats: list) -> dict:
        """
        faithfulness : la configuration respecte-t-elle marge >= 14% ?

        user_input         = description client + besoins
        response           = configuration + prix + marge calculée
        retrieved_contexts = [règle marge Orange + calculs réels]
        reference          = taux_marge >= 14% et calculs cohérents
        """
        samples = []

        for item in cas_avec_resultats:
            cas      = item["cas"]
            resultat = item["resultat"]

            prix_total  = resultat.get("prix_total_annuel", 0)
            cout_total  = resultat.get("cout_total_annuel", 0)
            marge_brute = resultat.get("marge_brute", 0)
            taux_marge  = resultat.get("taux_marge", 0)
            marge_ok    = resultat.get("contrainte_ok", False)

            response = (
                f"Configuration retenue. "
                f"Prix annuel total : {prix_total} TND. "
                f"Coût annuel total : {cout_total} TND. "
                f"Marge brute : {marge_brute} TND. "
                f"Taux de marge : {taux_marge}%. "
                f"Contrainte marge >= 14% : {'respectée' if marge_ok else 'non respectée'}."
            )

            contexte = (
                f"Règle Orange : taux_marge = marge_brute / prix_vente × 100, minimum 14%. "
                f"Résultats calculs : prix={prix_total} TND, cout={cout_total} TND, "
                f"marge_brute={marge_brute} TND, taux_marge={taux_marge}%."
            )

            reference = (
                f"Le taux de marge doit être >= 14%. "
                f"La formule correcte est : taux_marge = marge_brute / prix_vente × 100."
            )

            samples.append(SingleTurnSample(
                user_input=cas["description"],
                response=response,
                retrieved_contexts=[contexte],
                reference=reference
            ))

        if not samples:
            return {"faithfulness": 0.0}

        print("\n  Calcul RAGAS faithfulness (respect contrainte marge >= 14%)...")
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

                taux_marge = resultat_ag3.get("taux_marge", 0)
                marge_ok   = resultat_ag3.get("contrainte_ok", False)

                statut = "[OK]" if marge_ok else "[KO]"
                print(f"{statut} marge={taux_marge:.1f}%  contrainte={'OK' if marge_ok else 'KO'}")

                cas_avec_resultats.append({"cas": cas, "resultat": resultat_ag3})

            except Exception as e:
                print(f"[ERREUR] {e}")

        ragas = self.evaluer_ragas(cas_avec_resultats)

        resultats = {"ragas": ragas}

        print(f"\n{'='*60}")
        print("  RESULTATS")
        print(f"{'='*60}")
        print(f"  faithfulness : {ragas['faithfulness']:.4f}  ({ragas['faithfulness']*100:.1f}%)")
        print(f"  Interpretation : respect contrainte marge Orange >= 14%")

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_agent3.json", 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        print(f"\n  Resultats sauvegardes : evaluation/resultats/resultats_agent3.json")

        return resultats


if __name__ == "__main__":
    EvaluateurAgent3().evaluer()