# evaluation/run_all.py
"""
Lance toutes les evaluations dans l'ordre :
    1. RAGAS      — Agent 1 (AnswerRelevancy + ContextRecall)
    2. RAGAS      — Agent 2 (Faithfulness + ContextPrecision)
    3. RAGAS      — Agent 3 (Faithfulness)
    4. BERTScore  — Agent 4 (qualite semantique documents)
    5. LLM-Judge  — Agent 3 (qualite pitchs commerciaux)
    6. Humaine    — Agent 3 (notation experte interactive)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluateur_agent1  import EvaluateurAgent1
from evaluation.evaluateur_agent2  import EvaluateurAgent2
from evaluation.evaluateur_agent3  import EvaluateurAgent3
from evaluation.evaluateur_agent4  import EvaluateurAgent4
from evaluation.evaluateur_llm_judge import LLMJuge
from evaluation.evaluateur_human   import EvaluateurFactuel


SEPARATEUR = "\n" + "█"*60 + "\n"


def run_all():
    resultats = {}

    # ── 1. RAGAS Agent 1 ─────────────────────────────────────────
    print(SEPARATEUR)
    print("  [1/6] RAGAS — Agent 1 : Analyste de besoins")
    print(SEPARATEUR)
    try:
        resultats["agent1_ragas"] = EvaluateurAgent1().evaluer()
    except Exception as e:
        print(f"  ERREUR Agent 1 : {e}")
        resultats["agent1_ragas"] = {"erreur": str(e)}

    # ── 2. RAGAS Agent 2 ─────────────────────────────────────────
    print(SEPARATEUR)
    print("  [2/6] RAGAS — Agent 2 : Configurateur de solutions")
    print(SEPARATEUR)
    try:
        resultats["agent2_ragas"] = EvaluateurAgent2().evaluer()
    except Exception as e:
        print(f"  ERREUR Agent 2 : {e}")
        resultats["agent2_ragas"] = {"erreur": str(e)}

    # ── 3. RAGAS Agent 3 ─────────────────────────────────────────
    print(SEPARATEUR)
    print("  [3/6] RAGAS — Agent 3 : Optimiseur de prix")
    print(SEPARATEUR)
    try:
        resultats["agent3_ragas"] = EvaluateurAgent3().evaluer()
    except Exception as e:
        print(f"  ERREUR Agent 3 : {e}")
        resultats["agent3_ragas"] = {"erreur": str(e)}

    # ── 4. BERTScore Agent 4 ─────────────────────────────────────
    print(SEPARATEUR)
    print("  [4/6] BERTScore — Agent 4 : Generateur de documents")
    print(SEPARATEUR)
    try:
        resultats["agent4_bertscore"] = EvaluateurAgent4().evaluer()
    except Exception as e:
        print(f"  ERREUR Agent 4 : {e}")
        resultats["agent4_bertscore"] = {"erreur": str(e)}

    # ── 5. LLM-Judge ─────────────────────────────────────────────
    print(SEPARATEUR)
    print("  [5/6] LLM-as-Judge — Agent 3 : Qualite pitchs")
    print(SEPARATEUR)
    try:
        resultats["llm_judge"] = LLMJuge().evaluer_tous(
            chemin_cas       = "evaluation/cas_tests/cas_agent3.json",
            chemin_resultats = "evaluation/resultats/resultats_llm_judge.json"
        )
    except Exception as e:
        print(f"  ERREUR LLM-Judge : {e}")
        resultats["llm_judge"] = {"erreur": str(e)}

    # ── 6. Evaluation Factuelle ───────────────────────────────────
    print(SEPARATEUR)
    print("  [6/6] EVALUATION FACTUELLE — Agent 1 : Exactitude extraction")
    print(SEPARATEUR)
    try:
        resultats["factuel"] = EvaluateurFactuel().evaluer()
    except Exception as e:
        print(f"  ERREUR Evaluation Factuelle : {e}")
        resultats["factuel"] = {"erreur": str(e)}

    # ── Synthese finale ───────────────────────────────────────────
    print("\n" + "█"*60)
    print("  SYNTHESE COMPLETE — TOUTES EVALUATIONS")
    print("█"*60)

    if "agent1_ragas" in resultats and "erreur" not in resultats["agent1_ragas"]:
        r = resultats["agent1_ragas"]
        print(f"  Agent 1 — AnswerRelevancy : {r.get('answer_relevancy', 0)*100:.1f}%")
        print(f"  Agent 1 — ContextRecall   : {r.get('context_recall', 0)*100:.1f}%")

    if "agent2_ragas" in resultats and "erreur" not in resultats["agent2_ragas"]:
        r = resultats["agent2_ragas"]
        print(f"  Agent 2 — Faithfulness    : {r.get('faithfulness', 0)*100:.1f}%")
        print(f"  Agent 2 — ContextPrecision: {r.get('context_precision', 0)*100:.1f}%")

    if "agent3_ragas" in resultats and "erreur" not in resultats["agent3_ragas"]:
        r = resultats["agent3_ragas"]
        print(f"  Agent 3 — Faithfulness    : {r.get('faithfulness', 0)*100:.1f}%")

    if "agent4_bertscore" in resultats and "erreur" not in resultats["agent4_bertscore"]:
        r = resultats["agent4_bertscore"]
        print(f"  Agent 4 — BERTScore F1    : {r.get('bertscore_f1', 0)*100:.1f}%")

    if "llm_judge" in resultats and "erreur" not in resultats["llm_judge"]:
        r = resultats["llm_judge"].get("moyennes", {})
        print(f"  LLM-Judge — Score global  : {r.get('score_global', 0)}/5")

    if "factuel" in resultats and "erreur" not in resultats["factuel"]:
        r = resultats["factuel"]
        print(f"  Factuel   — Score global  : {r.get('score_global', 0)*100:.1f}%")

    print("█"*60)
    print("\n  Tous les resultats sont dans : evaluation/resultats/")


if __name__ == "__main__":
    run_all()
