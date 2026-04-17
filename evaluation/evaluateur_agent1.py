# evaluation/evaluateur_agent1.py
"""
Evaluateur Agent 1 - Analyste de Besoins
Metriques RAGAS : answer_relevancy + context_recall
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import AnswerRelevancy, ContextRecall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from agents.agent_analyste import AgentAnalyste

load_dotenv()


class EvaluateurAgent1:

    def __init__(self):
        self.agent = AgentAnalyste()

        groq_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        ragas_llm = LangchainLLMWrapper(groq_llm)

        hf_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        ragas_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)

        self.metric_relevancy = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
        self.metric_recall    = ContextRecall(llm=ragas_llm)

    def _json_vers_texte(self, data: dict) -> str:
        """Convertit le JSON extrait en texte naturel pour les embeddings RAGAS."""
        parties = []
        if data.get("nom_entreprise"):
            parties.append(f"Entreprise : {data['nom_entreprise']}")
        if data.get("secteur"):
            parties.append(f"Secteur : {data['secteur']}")
        if data.get("taille_entreprise"):
            parties.append(f"Taille : {data['taille_entreprise']}")
        if data.get("budget_mensuel"):
            parties.append(f"Budget mensuel : {data['budget_mensuel']} TND")

        fibre = data.get("besoins_fibre", {})
        if fibre.get("demande_fibre"):
            parties.append(
                f"Fibre demandee : {fibre.get('debit_souhaite_mbps')} Mbps, "
                f"{fibre.get('nombre_sites', 1)} site(s)"
            )
        else:
            parties.append("Pas de demande Fibre")

        ms = data.get("besoins_microsoft", {})
        if ms.get("demande_microsoft"):
            parties.append(
                f"Microsoft 365 demande : {ms.get('nombre_licences')} licences"
            )
        else:
            parties.append("Pas de demande Microsoft")

        return ". ".join(parties)

    def evaluer(self, fichier: str = "evaluation/cas_tests/cas_agent1.json") -> dict:
        with open(fichier, 'r', encoding='utf-8') as f:
            cas_tests = json.load(f)
    
        print(f"\n{'='*60}")
        print("  EVALUATION AGENT 1 — RAGAS")
        print(f"{'='*60}")
        print(f"  Nombre de cas : {len(cas_tests)}\n")

        samples = []
        for i, cas in enumerate(cas_tests, 1):
            print(f"  Cas {i}/{len(cas_tests)}...", end=" ", flush=True)
            try:
                resultat       = self.agent.analyser(cas["input"])
                response_texte = self._json_vers_texte(resultat)
                reference_texte = self._json_vers_texte(cas["expected"])

                samples.append(SingleTurnSample(
                    user_input=cas["input"],
                    response=response_texte,
                    retrieved_contexts=[cas["input"]],
                    reference=reference_texte
                ))
                print("[OK]")
            except Exception as e:
                print(f"[ERREUR] {e}")

        if not samples:
            print("Aucun cas valide.")
            return {}

        print("\n  Calcul RAGAS...")
        dataset = EvaluationDataset(samples=samples)
        scores  = evaluate(dataset=dataset, metrics=[self.metric_relevancy, self.metric_recall])
        df      = scores.to_pandas()

        resultats = {
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4),
            "context_recall":   round(float(df["context_recall"].mean()),   4)
        }

        print(f"\n  answer_relevancy : {resultats['answer_relevancy']:.4f}  ({resultats['answer_relevancy']*100:.1f}%)")
        print(f"  context_recall   : {resultats['context_recall']:.4f}  ({resultats['context_recall']*100:.1f}%)")

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_agent1.json", 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        print("\n  Resultats sauvegardes : evaluation/resultats/resultats_agent1.json")

        return resultats


if __name__ == "__main__":
    EvaluateurAgent1().evaluer()
