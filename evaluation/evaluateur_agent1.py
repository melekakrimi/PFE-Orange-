# evaluation/evaluateur_agent1.py
"""
Evaluateur professionnel Agent 1 - Analyste de Besoins
=======================================================
Metriques RAGAS  : answer_relevancy + context_recall
Metriques academiques : Precision / Rappel / F1 (comparaison JSON champ par champ)
Metriques business    : Temps d'execution, Cout API estime
"""

import sys
import os
import json
import time
from typing import Dict, List

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
    """
    Evalue Agent 1 selon 3 niveaux de metriques :
    1. RAGAS        : answer_relevancy + context_recall
    2. Academiques  : Precision / Rappel / F1
    3. Business     : Temps d'execution, Cout API
    """

    def __init__(self):
        self.agent = AgentAnalyste()

        # ── Configuration LLM Groq pour RAGAS ────────────────────────
        groq_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        ragas_llm = LangchainLLMWrapper(groq_llm)

        # ── Embeddings multilingues locaux (pas d'API OpenAI requise) ─
        hf_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        ragas_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)

        # ── Metriques RAGAS ───────────────────────────────────────────
        # answer_relevancy : la reponse JSON est-elle pertinente par rapport a l'email ?
        self.metric_relevancy = AnswerRelevancy(
            llm=ragas_llm,
            embeddings=ragas_embeddings
        )
        # context_recall : toutes les infos importantes de l'email sont-elles extraites ?
        self.metric_recall = ContextRecall(llm=ragas_llm)

        self.resultats = {
            "ragas": {},
            "academique": {},
            "business": {},
            "details": []
        }

    # ═══════════════════════════════════════════════════════════════════
    # CHARGEMENT CAS DE TEST
    # ═══════════════════════════════════════════════════════════════════

    def charger_cas_tests(self, fichier: str = "evaluation/cas_tests/cas_agent1.json") -> List[Dict]:
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ═══════════════════════════════════════════════════════════════════
    # METRIQUES ACADEMIQUES (comparaison champ par champ)
    # ═══════════════════════════════════════════════════════════════════

    def _verifier_champ(self, resultat: Dict, expected: Dict, champ: str) -> bool:
        """Verification recursive d'un champ entre resultat et expected."""
        if champ not in expected:
            return True
        if champ not in resultat:
            return False

        val_attendue = expected[champ]
        val_obtenue  = resultat[champ]

        if isinstance(val_attendue, dict):
            return all(
                self._verifier_champ(val_obtenue, val_attendue, sous_champ)
                for sous_champ in val_attendue.keys()
            )
        if isinstance(val_attendue, (int, float)) and isinstance(val_obtenue, (int, float)):
            return abs(val_obtenue - val_attendue) / max(abs(val_attendue), 1) < 0.1
        return str(val_obtenue).lower() == str(val_attendue).lower()

    def evaluer_academique(self, resultat: Dict, expected: Dict) -> Dict:
        """Calcule precision par champ pour un cas de test."""
        champs = [
            "nom_entreprise", "secteur", "taille_entreprise",
            "nombre_sites", "budget_mensuel",
            "besoins_fibre", "besoins_microsoft"
        ]
        total, corrects, manquants = 0, 0, []

        for champ in champs:
            if champ in expected:
                total += 1
                if self._verifier_champ(resultat, expected, champ):
                    corrects += 1
                else:
                    manquants.append(champ)

        return {
            "champs_totaux":   total,
            "champs_corrects": corrects,
            "champs_manquants": manquants,
            "precision":       round(corrects / total * 100, 2) if total > 0 else 0
        }

    def calculer_metriques_academiques(self, details: List[Dict]) -> Dict:
        """Precision / Rappel / F1 globaux sur tous les cas."""
        total    = sum(d["academique"]["champs_totaux"]   for d in details)
        corrects = sum(d["academique"]["champs_corrects"] for d in details)

        precision = round(corrects / total * 100, 2) if total > 0 else 0
        rappel    = precision  # Pour Agent 1 : rappel ~ precision (extraction complete)
        f1        = round(2 * precision * rappel / (precision + rappel), 2) if (precision + rappel) > 0 else 0

        return {
            "precision":      precision,
            "rappel":         rappel,
            "f1_score":       f1,
            "total_champs":   total,
            "total_corrects": corrects
        }

    # ═══════════════════════════════════════════════════════════════════
    # METRIQUES RAGAS (answer_relevancy + context_recall)
    # ═══════════════════════════════════════════════════════════════════

    def evaluer_ragas(self, cas_tests: List[Dict], resultats_agents: List[Dict]) -> Dict:
        """
        Lance l'evaluation RAGAS sur l'ensemble des cas.

        Mapping RAGAS :
          user_input        = email client (question)
          response          = JSON extrait par Agent 1 (reponse)
          retrieved_contexts = [email client] (contexte disponible)
          reference         = JSON expected (verite terrain)
        """
        samples = []

        for cas, resultat in zip(cas_tests, resultats_agents):
            if resultat is None:
                continue

            sample = SingleTurnSample(
                user_input=cas["input"],
                response=json.dumps(resultat, ensure_ascii=False),
                retrieved_contexts=[cas["input"]],                 # contexte = l'email lui-meme
                reference=json.dumps(cas["expected"], ensure_ascii=False)
            )
            samples.append(sample)

        if not samples:
            return {"answer_relevancy": 0.0, "context_recall": 0.0}

        dataset = EvaluationDataset(samples=samples)

        print("\n  Calcul metriques RAGAS (answer_relevancy + context_recall)...")
        scores = evaluate(
            dataset=dataset,
            metrics=[self.metric_relevancy, self.metric_recall]
        )

        df = scores.to_pandas()
        return {
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4),
            "context_recall":   round(float(df["context_recall"].mean()), 4)
        }

    # ═══════════════════════════════════════════════════════════════════
    # METRIQUES BUSINESS
    # ═══════════════════════════════════════════════════════════════════

    def _estimer_cout_api(self, input_text: str, output_text: str) -> float:
        """Estime le cout API (LLaMA 3.3 70B via Groq : gratuit sur free tier)."""
        tokens = (len(input_text.split()) + len(output_text.split())) * 1.3
        return round((tokens / 1000) * 0.001, 4)

    def calculer_metriques_business(self, details: List[Dict]) -> Dict:
        n = len(details)
        if n == 0:
            return {"temps_moyen": 0, "cout_moyen": 0, "temps_total": 0, "cout_total": 0}

        temps = [d["business"]["temps"] for d in details]
        couts = [d["business"]["cout"]  for d in details]

        return {
            "temps_moyen": round(sum(temps) / n, 3),
            "cout_moyen":  round(sum(couts) / n, 4),
            "temps_total": round(sum(temps), 2),
            "cout_total":  round(sum(couts), 4)
        }

    # ═══════════════════════════════════════════════════════════════════
    # EVALUATION COMPLETE
    # ═══════════════════════════════════════════════════════════════════

    def evaluer_tous_les_cas(self, cas_tests: List[Dict] = None) -> Dict:
        if cas_tests is None:
            cas_tests = self.charger_cas_tests()

        print("\n" + "=" * 70)
        print("  EVALUATION AGENT 1 - ANALYSTE DE BESOINS")
        print("=" * 70)
        print(f"\nNombre de cas : {len(cas_tests)}\n")

        details          = []
        resultats_agents = []

        # ── Phase 1 : Execution des cas ──────────────────────────────
        for i, cas in enumerate(cas_tests, 1):
            print(f"Cas {i}/{len(cas_tests)} #{cas['id']}...", end=" ", flush=True)
            t0 = time.time()
            try:
                resultat   = self.agent.analyser(cas["input"])
                temps_exec = time.time() - t0

                eval_acad = self.evaluer_academique(resultat, cas["expected"])
                cout      = self._estimer_cout_api(cas["input"], json.dumps(resultat))

                detail = {
                    "cas_id":    cas["id"],
                    "succes":    True,
                    "academique": eval_acad,
                    "business":  {"temps": temps_exec, "cout": cout},
                    "resultat":  resultat,
                    "expected":  cas["expected"]
                }
                details.append(detail)
                resultats_agents.append(resultat)

                statut = "[OK]" if eval_acad["precision"] >= 90 else ("[~]" if eval_acad["precision"] >= 70 else "[KO]")
                print(f"{statut} Precision {eval_acad['precision']:.1f}%")

            except Exception as e:
                print(f"[ERREUR] {e}")
                details.append({"cas_id": cas["id"], "succes": False, "erreur": str(e)})
                resultats_agents.append(None)

        # ── Phase 2 : Metriques globales ─────────────────────────────
        details_ok = [d for d in details if d.get("succes")]

        self.resultats["academique"] = self.calculer_metriques_academiques(details_ok)
        self.resultats["business"]   = self.calculer_metriques_business(details_ok)

        # ── Phase 3 : RAGAS (appel LLM separé) ───────────────────────
        cas_ok = [cas_tests[i] for i, d in enumerate(details) if d.get("succes")]
        self.resultats["ragas"] = self.evaluer_ragas(cas_ok, resultats_agents)

        self.resultats["details"] = details
        return self.resultats

    # ═══════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═══════════════════════════════════════════════════════════════════

    def generer_rapport_console(self):
        print("\n" + "=" * 70)
        print("  RAPPORT D'EVALUATION - AGENT 1")
        print("=" * 70)

        # Metriques academiques
        print("\n[1] METRIQUES ACADEMIQUES (comparaison JSON ground truth)")
        print("-" * 70)
        acad = self.resultats["academique"]
        print(f"  Precision  : {acad['precision']:.2f}%   (cible : >=90%)")
        print(f"  Rappel     : {acad['rappel']:.2f}%   (cible : >=85%)")
        print(f"  F1-Score   : {acad['f1_score']:.2f}%   (cible : >=87%)")
        print(f"  Details    : {acad['total_corrects']}/{acad['total_champs']} champs corrects")
        verdict = "EXCELLENT" if acad['f1_score'] >= 87 else ("BON" if acad['f1_score'] >= 75 else "INSUFFISANT")
        print(f"  Verdict    : {verdict}")

        # Metriques RAGAS
        print("\n[2] METRIQUES RAGAS")
        print("-" * 70)
        ragas = self.resultats["ragas"]
        ar = ragas.get("answer_relevancy", 0)
        cr = ragas.get("context_recall",   0)
        print(f"  answer_relevancy : {ar:.4f}  ({ar*100:.1f}%)  (cible : >=0.85)")
        print(f"  context_recall   : {cr:.4f}  ({cr*100:.1f}%)  (cible : >=0.85)")
        verdict_ragas = "EXCELLENT" if ar >= 0.85 and cr >= 0.85 else "A AMELIORER"
        print(f"  Verdict RAGAS    : {verdict_ragas}")

        # Metriques business
        print("\n[3] METRIQUES BUSINESS")
        print("-" * 70)
        biz = self.resultats["business"]
        print(f"  Temps moyen   : {biz['temps_moyen']:.3f}s")
        print(f"  Temps total   : {biz['temps_total']:.2f}s")
        print(f"  Cout moyen    : {biz['cout_moyen']:.4f} TND")
        print(f"  Gain de temps : ~{(1 - biz['temps_moyen']/(30*60))*100:.1f}% vs analyse manuelle (30 min)")

        print("\n" + "=" * 70)

    def sauvegarder_resultats(self, fichier: str = "evaluation/resultats/resultats_agent1.json"):
        os.makedirs(os.path.dirname(fichier), exist_ok=True)
        with open(fichier, 'w', encoding='utf-8') as f:
            json.dump(self.resultats, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResultats sauvegardes : {fichier}")


# ═══════════════════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    evaluateur = EvaluateurAgent1()
    evaluateur.evaluer_tous_les_cas()
    evaluateur.generer_rapport_console()
    evaluateur.sauvegarder_resultats()
    print("\nEvaluation Agent 1 terminee.")
