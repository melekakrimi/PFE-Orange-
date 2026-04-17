# evaluation/evaluateur_agent2.py
"""
Evaluateur Agent 2 - Configurateur de Solutions
Metriques RAGAS : faithfulness + context_precision (Microsoft uniquement)
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness, ContextPrecision
from ragas.llms import LangchainLLMWrapper

from agents.agent_configurateur import AgentConfigurateur

load_dotenv()


class EvaluateurAgent2:

    def __init__(self):
        self.agent = AgentConfigurateur()

        groq_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        ragas_llm = LangchainLLMWrapper(groq_llm)

        self.metric_faithfulness      = Faithfulness(llm=ragas_llm)
        self.metric_context_precision = ContextPrecision(llm=ragas_llm)

    def _configs_ms_vers_texte(self, configs: dict) -> str:
        """Convertit les 3 configurations Microsoft en texte naturel pour RAGAS."""
        parties = []
        mapping = {
            "configuration_economique": "Economique",
            "configuration_standard":   "Standard",
            "configuration_premium":    "Premium"
        }
        for cle, label in mapping.items():
            if cle not in configs:
                continue
            c = configs[cle]
            parties.append(
                f"Option {label} : {c.get('nom_produit', '?')} "
                f"au prix de {c.get('prix_unitaire_tnd', 0)} TND par licence par an."
            )
        rec = configs.get("recommandation", "")
        if rec:
            parties.append(f"Recommandation : {rec}.")
        return " ".join(parties)

    def _catalogue_vers_texte(self) -> str:
        """Retourne les produits Microsoft 365 du catalogue en texte pour RAGAS."""
        df = self.agent.catalogue_microsoft[
            self.agent.catalogue_microsoft['famille'] == 'Microsoft 365'
        ].head(30)
        if len(df) < 5:
            df = self.agent.catalogue_microsoft.head(30)
        return df[['nom_service', 'product_id', 'prix_vente_tnd']].to_string(index=False)

    def evaluer(self, fichier: str = "evaluation/cas_tests/cas_agent2.json") -> dict:
        with open(fichier, 'r', encoding='utf-8') as f:
            cas_tests = json.load(f)

        print(f"\n{'='*60}")
        print("  EVALUATION AGENT 2 — RAGAS")
        print(f"{'='*60}")
        print(f"  Nombre de cas : {len(cas_tests)}\n")

        samples         = []
        catalogue_texte = self._catalogue_vers_texte()

        for i, cas in enumerate(cas_tests, 1):
            print(f"  Cas {i}/{len(cas_tests)}...", end=" ", flush=True)
            try:
                resultat  = self.agent.configurer(cas["input"])
                ms_result = resultat.get("microsoft", {})

                # On evalue uniquement les cas avec Microsoft
                if not ms_result or "configuration_economique" not in ms_result:
                    print("[SKIP] Pas de Microsoft")
                    continue

                response_texte  = self._configs_ms_vers_texte(ms_result)
                expected_ms     = cas.get("expected", {}).get("microsoft", {})
                reference       = (
                    f"3 configurations Microsoft distinctes pour "
                    f"{expected_ms.get('nb_licences', '?')} licences. "
                    f"Recommandation attendue : {expected_ms.get('recommandation', '?')}."
                )

                samples.append(SingleTurnSample(
                    user_input=cas["description"],
                    response=response_texte,
                    retrieved_contexts=[catalogue_texte],
                    reference=reference
                ))
                print("[OK]")
            except Exception as e:
                print(f"[ERREUR] {e}")

        if not samples:
            print("Aucun cas Microsoft valide.")
            return {}

        print("\n  Calcul RAGAS...")
        dataset = EvaluationDataset(samples=samples)
        scores  = evaluate(dataset=dataset, metrics=[self.metric_faithfulness, self.metric_context_precision])
        df      = scores.to_pandas()

        resultats = {
            "faithfulness":      round(float(df["faithfulness"].mean()),      4),
            "context_precision": round(float(df["context_precision"].mean()), 4)
        }

        print(f"\n  faithfulness       : {resultats['faithfulness']:.4f}  ({resultats['faithfulness']*100:.1f}%)")
        print(f"  context_precision  : {resultats['context_precision']:.4f}  ({resultats['context_precision']*100:.1f}%)")

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_agent2.json", 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        print("\n  Resultats sauvegardes : evaluation/resultats/resultats_agent2.json")

        return resultats


if __name__ == "__main__":
    EvaluateurAgent2().evaluer()
