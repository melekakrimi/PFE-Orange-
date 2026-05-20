# evaluation/evaluateur_human.py
"""
Evaluation Factuelle — Agent 1 (Analyste de besoins)
Metrique custom : verifie champ par champ si l'agent extrait
correctement les informations du client.

Champs verifies :
    - nom_entreprise      : nom correct ?
    - secteur             : secteur correct ?
    - taille_entreprise   : taille correcte ?
    - demande_fibre       : besoin fibre detecte ?
    - debit_souhaite_mbps : debit correct ? (si fibre)
    - demande_microsoft   : besoin Microsoft detecte ?
    - nombre_licences     : nombre de licences correct ? (si Microsoft)

Score = champs_corrects / champs_verifies
"""

import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_analyste import AgentAnalyste


class EvaluateurFactuel:

    def __init__(self):
        self.agent = AgentAnalyste()

    def _verifier_cas(self, resultat: dict, expected: dict) -> dict:
        checks = {}

        checks["nom_entreprise"] = (
            resultat.get("nom_entreprise", "").strip().lower() ==
            expected.get("nom_entreprise", "").strip().lower()
        )

        checks["secteur"] = (
            resultat.get("secteur", "").strip().lower() ==
            expected.get("secteur", "").strip().lower()
        )

        checks["taille_entreprise"] = (
            resultat.get("taille_entreprise", "").strip().upper() ==
            expected.get("taille_entreprise", "").strip().upper()
        )

        fibre_res = resultat.get("besoins_fibre", {})
        fibre_exp = expected.get("besoins_fibre", {})

        checks["demande_fibre"] = (
            fibre_res.get("demande_fibre") == fibre_exp.get("demande_fibre")
        )

        if fibre_exp.get("demande_fibre"):
            checks["debit_souhaite_mbps"] = (
                fibre_res.get("debit_souhaite_mbps") ==
                fibre_exp.get("debit_souhaite_mbps")
            )

        ms_res = resultat.get("besoins_microsoft", {})
        ms_exp = expected.get("besoins_microsoft", {})

        checks["demande_microsoft"] = (
            ms_res.get("demande_microsoft") == ms_exp.get("demande_microsoft")
        )

        if ms_exp.get("demande_microsoft"):
            checks["nombre_licences"] = (
                ms_res.get("nombre_licences") == ms_exp.get("nombre_licences")
            )

        return checks

    def evaluer(self, fichier: str = "evaluation/cas_tests/cas_agent1.json") -> dict:
        with open(fichier, encoding="utf-8") as f:
            cas_tests = json.load(f)

        print(f"\n{'='*60}")
        print("  EVALUATION FACTUELLE — Agent 1 (Analyste)")
        print(f"{'='*60}")
        print(f"  Nombre de cas : {len(cas_tests)}\n")

        details = []

        for i, cas in enumerate(cas_tests, 1):
            print(f"  Cas {i}/{len(cas_tests)} — {cas['expected']['nom_entreprise']}...", end=" ", flush=True)

            try:
                resultat = self.agent.analyser(cas["input"])
                checks   = self._verifier_cas(resultat, cas["expected"])

                corrects = sum(1 for v in checks.values() if v)
                total    = len(checks)
                score    = round(corrects / total, 4)

                print(f"[{corrects}/{total}] {score*100:.0f}%")

                for champ, ok in checks.items():
                    statut = "OK" if ok else "ERREUR"
                    print(f"    {statut:6} — {champ}")

                details.append({
                    "id":       cas["id"],
                    "client":   cas["expected"]["nom_entreprise"],
                    "checks":   {k: bool(v) for k, v in checks.items()},
                    "corrects": corrects,
                    "total":    total,
                    "score":    score,
                })

            except Exception as e:
                print(f"[ERREUR] {e}")
                details.append({"id": cas["id"], "erreur": str(e)})

        valides = [d for d in details if "score" in d]

        if valides:
            score_moyen = round(sum(d["score"] for d in valides) / len(valides), 4)

            tous_champs = set()
            for d in valides:
                tous_champs.update(d["checks"].keys())

            scores_champs = {}
            for champ in sorted(tous_champs):
                valeurs = [d["checks"][champ] for d in valides if champ in d["checks"]]
                if valeurs:
                    scores_champs[champ] = round(sum(valeurs) / len(valeurs), 4)

            print(f"\n{'='*60}")
            print("  RESULTATS FINAUX — EVALUATION FACTUELLE")
            print(f"{'='*60}")
            print(f"  Cas evalues       : {len(valides)}/{len(cas_tests)}")
            print(f"  Score global      : {score_moyen*100:.1f}%")
            print(f"\n  Detail par champ :")
            for champ, sc in scores_champs.items():
                barre = "█" * int(sc * 20)
                print(f"    {champ:<25} {sc*100:5.1f}%  {barre}")
            print(f"{'='*60}")

            rapport = {
                "methode":       "Evaluation factuelle",
                "agent_evalue":  "Agent 1 — Analyste de besoins",
                "nb_cas":        len(cas_tests),
                "nb_valides":    len(valides),
                "score_global":  score_moyen,
                "scores_champs": scores_champs,
                "details":       details,
            }
        else:
            rapport = {"erreur": "Aucun cas valide", "details": details}

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_factuel.json", "w", encoding="utf-8") as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False)

        print(f"\n  Resultats sauvegardes : evaluation/resultats/resultats_factuel.json")
        return rapport


if __name__ == "__main__":
    EvaluateurFactuel().evaluer()
