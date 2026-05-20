# evaluation/evaluateur_agent2.py
"""
Evaluateur Agent 2 - Configurateur de Solutions
Métriques RAGAS : faithfulness + context_precision
Vérification Python : plan dans catalogue, prix correct, services couverts
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import ContextPrecision
from ragas.llms import LangchainLLMWrapper

from agents.agent_configurateur import AgentConfigurateur

load_dotenv()

# Matrice des services couverts par chaque plan (du moins cher au plus cher)
SERVICES_PAR_PLAN = {
    "Exchange Online Plan 1":          {"onedrive": False, "sharepoint": False, "mail": True,  "pack_office": False, "intune": False, "defender": False},
    "Microsoft 365 Business Basic":    {"onedrive": True,  "sharepoint": True,  "mail": True,  "pack_office": False, "intune": False, "defender": False},
    "Microsoft 365 Business Standard": {"onedrive": True,  "sharepoint": True,  "mail": True,  "pack_office": True,  "intune": False, "defender": False},
    "Microsoft 365 Business Premium":  {"onedrive": True,  "sharepoint": True,  "mail": True,  "pack_office": True,  "intune": True,  "defender": True},
}


class EvaluateurAgent2:

    def __init__(self):
        self.agent = AgentConfigurateur()

        groq_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        ragas_llm = LangchainLLMWrapper(groq_llm)

        self.metric_context_precision = ContextPrecision(llm=ragas_llm)

    # ═══════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════

    def _catalogue_vers_texte(self) -> str:
        """Retourne les 4 plans Microsoft du catalogue en texte pour RAGAS."""
        lignes = ["Catalogue Microsoft — 4 plans disponibles :"]
        for _, row in self.agent.catalogue_df.iterrows():
            lignes.append(
                f"- {row['nom_produit']} : {row['prix_annuel_tnd']} TND/licence/an | "
                f"OneDrive={row['onedrive']}, SharePoint={row['sharepoint']}, "
                f"Mail={row['mail']}, PackOffice={row['pack_office']}, "
                f"Intune={row['intune']}, Defender={row['defender']}"
            )
        return "\n".join(lignes)

    def _ms_vers_texte(self, ms: dict) -> str:
        """Convertit la configuration Microsoft retournée en texte naturel pour RAGAS."""
        return (
            f"Plan sélectionné : {ms.get('nom_produit', '?')}. "
            f"Nombre de licences : {ms.get('nombre_licences', 0)}. "
            f"Prix unitaire : {ms.get('prix_unitaire_tnd', 0)} TND/licence/an. "
            f"Prix total annuel : {ms.get('prix_total_annuel', 0)} TND. "
            f"Justification : {ms.get('justification', '')}."
        )

    # ═══════════════════════════════════════════════════════════════
    # VÉRIFICATIONS PYTHON
    # ═══════════════════════════════════════════════════════════════

    def _verifier_plan_catalogue(self, ms: dict) -> bool:
        """Le plan sélectionné existe-t-il dans le catalogue des 4 plans ?"""
        return ms.get("nom_produit", "") in self.agent.catalogue_df["nom_produit"].values

    def _verifier_prix(self, ms: dict) -> bool:
        """prix_total_annuel == prix_unitaire × nombre_licences (tolérance 1 TND) ?"""
        pu = float(ms.get("prix_unitaire_tnd", 0))
        nb = int(ms.get("nombre_licences", 0))
        pt = float(ms.get("prix_total_annuel", 0))
        return abs(round(pu * nb, 2) - pt) <= 1.0

    def _verifier_services(self, ms: dict, services_demandes: dict) -> bool:
        """Le plan couvre-t-il tous les services demandés ?"""
        nom = ms.get("nom_produit", "")
        couverture = SERVICES_PAR_PLAN.get(nom, {})
        for service, requis in services_demandes.items():
            if requis and not couverture.get(service, False):
                return False
        return True

    def _verifier_plan_minimum(self, ms: dict, services_demandes: dict) -> bool:
        """Le plan est-il le MINIMUM couvrant les services (pas de surqualité) ?"""
        nom_selectionne = ms.get("nom_produit", "")
        for nom_plan, couverture in SERVICES_PAR_PLAN.items():
            # Si un plan moins cher couvre aussi tous les services → surqualité
            if nom_plan == nom_selectionne:
                break
            couvre_tout = all(
                couverture.get(s, False) for s, v in services_demandes.items() if v
            )
            if couvre_tout:
                return False  # il existait un plan moins cher suffisant
        return True

    # ═══════════════════════════════════════════════════════════════
    # ÉVALUATION PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def evaluer(self, fichier: str = "evaluation/cas_tests/cas_agent2.json") -> dict:
        with open(fichier, 'r', encoding='utf-8') as f:
            cas_tests = json.load(f)

        print(f"\n{'='*60}")
        print("  EVALUATION AGENT 2 — RAGAS + Vérification Python")
        print(f"{'='*60}")
        print(f"  Nombre de cas : {len(cas_tests)}\n")

        samples         = []
        catalogue_texte = self._catalogue_vers_texte()

        # Compteurs vérification Python
        nb_ms_total      = 0
        nb_catalogue_ok  = 0
        nb_prix_ok       = 0
        nb_services_ok   = 0
        nb_minimum_ok    = 0
        nb_plan_exact_ok = 0

        for i, cas in enumerate(cas_tests, 1):
            print(f"  Cas {i}/{len(cas_tests)} [{cas.get('id')}]...", end=" ", flush=True)
            try:
                resultat = self.agent.configurer(cas["input"])
                ms       = resultat.get("microsoft")

                if not ms:
                    expected_ms = cas.get("expected", {}).get("microsoft")
                    if expected_ms is None:
                        print("[OK] Pas de Microsoft (attendu)")
                    else:
                        print("[KO] Microsoft attendu mais absent")
                    continue

                nb_ms_total += 1
                services_demandes = cas["input"]["besoins_microsoft"].get("services", {})

                # Vérifications Python
                v_cat  = self._verifier_plan_catalogue(ms)
                v_prix = self._verifier_prix(ms)
                v_serv = self._verifier_services(ms, services_demandes)
                v_min  = self._verifier_plan_minimum(ms, services_demandes)

                expected_nom = (cas.get("expected", {}).get("microsoft") or {}).get("nom_produit", "?")
                v_exact = ms.get("nom_produit", "") == expected_nom

                if v_cat:  nb_catalogue_ok  += 1
                if v_prix: nb_prix_ok       += 1
                if v_serv: nb_services_ok   += 1
                if v_min:  nb_minimum_ok    += 1
                if v_exact: nb_plan_exact_ok += 1

                print(
                    f"plan={ms.get('nom_produit','?')[:25]} | "
                    f"catalogue={'OK' if v_cat else 'KO'} | "
                    f"prix={'OK' if v_prix else 'KO'} | "
                    f"services={'OK' if v_serv else 'KO'} | "
                    f"minimum={'OK' if v_min else 'KO'} | "
                    f"exact={'OK' if v_exact else f'KO(attendu:{expected_nom})'}"
                )

                # RAGAS sample
                reference = (
                    f"Plan attendu : {expected_nom} "
                    f"pour {ms.get('nombre_licences', '?')} licences. "
                    f"Le plan doit couvrir tous les services demandés "
                    f"en utilisant le plan minimum du catalogue."
                )

                samples.append(SingleTurnSample(
                    user_input=cas["description"],
                    response=self._ms_vers_texte(ms),
                    retrieved_contexts=[catalogue_texte],
                    reference=reference
                ))

            except Exception as e:
                print(f"[ERREUR] {e}")

        # Vérification Python — résumé
        pct = lambda n: round(n / nb_ms_total * 100, 1) if nb_ms_total else 0

        verif_python = {
            "nb_cas_microsoft":    nb_ms_total,
            "plan_du_catalogue":   f"{pct(nb_catalogue_ok)}%",
            "prix_correct":        f"{pct(nb_prix_ok)}%",
            "services_couverts":   f"{pct(nb_services_ok)}%",
            "plan_minimum":        f"{pct(nb_minimum_ok)}%",
            "plan_exact_attendu":  f"{pct(nb_plan_exact_ok)}%",
        }

        # RAGAS
        resultats = {"verification_python": verif_python}

        if samples:
            print("\n  Calcul RAGAS...")
            dataset = EvaluationDataset(samples=samples)
            scores  = evaluate(dataset=dataset, metrics=[self.metric_context_precision])
            df      = scores.to_pandas()

            resultats["context_precision"] = round(float(df["context_precision"].mean()), 4)
        else:
            resultats["context_precision"] = 0.0

        print(f"\n{'='*60}")
        print("  RÉSULTATS")
        print(f"{'='*60}")
        print(f"  context_precision  : {resultats['context_precision']:.4f}  ({resultats['context_precision']*100:.1f}%)")
        print(f"  --- Vérification Python ---")
        print(f"  Plan du catalogue  : {verif_python['plan_du_catalogue']}")
        print(f"  Prix correct       : {verif_python['prix_correct']}")
        print(f"  Services couverts  : {verif_python['services_couverts']}")
        print(f"  Plan minimum       : {verif_python['plan_minimum']}")
        print(f"  Plan exact attendu : {verif_python['plan_exact_attendu']}")

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_agent2.json", 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        print(f"\n  Résultats sauvegardés : evaluation/resultats/resultats_agent2.json")

        return resultats


if __name__ == "__main__":
    EvaluateurAgent2().evaluer()