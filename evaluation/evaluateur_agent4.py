# evaluation/evaluateur_agent4.py
"""
Evaluateur Agent 4 - Generateur de Documents Commerciaux
Metriques :
  1. LLM-as-Judge   : qualite commerciale des textes (pertinence, coherence, ton)
  2. BERTScore      : qualite semantique des textes generes vs reference
"""

import sys
import os
import json
import re
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from bert_score import score as bert_score_fn

from agents.agent_configurateur import AgentConfigurateur
from agents.agent_optimiseur    import AgentOptimiseur
from agents.agent_documents     import AgentDocuments

load_dotenv()

DOSSIER_TEST = "evaluation/output_test"

PROMPT_JUGE = """
Tu es un expert commercial senior chez Orange Business Tunisie.
Tu evalues la qualite des textes generes pour une presentation commerciale B2B.

═══════════════════════════════════════════════════════
CONTEXTE CLIENT
═══════════════════════════════════════════════════════
Client   : {client}
Secteur  : {secteur}
Taille   : {taille}
Solutions: {solutions}
Prix total annuel : {prix_annuel} TND

═══════════════════════════════════════════════════════
TEXTES GENERES
═══════════════════════════════════════════════════════
Pourquoi cette offre : {pourquoi}
Benefice 1 : {benefice_1}
Benefice 2 : {benefice_2}
Benefice 3 : {benefice_3}
Cas d'usage : {cas_usage}
Conclusion : {conclusion}

═══════════════════════════════════════════════════════
CRITERES D'EVALUATION (note de 1 a 5)
═══════════════════════════════════════════════════════
1. pertinence_client (1-5) :
   Les textes sont-ils adaptes au secteur et a la taille de ce client ?
   5 = parfaitement adapte au secteur / 1 = generique, s'applique a n'importe qui

2. coherence_donnees (1-5) :
   Les textes sont-ils coherents avec les vraies donnees (prix, solutions) ?
   5 = chiffres et solutions bien integres / 1 = texte sans reference aux donnees reelles

3. qualite_commerciale (1-5) :
   Le ton est-il professionnel, convaincant et adapte a une presentation B2B ?
   5 = excellent niveau commercial / 1 = amateur ou trop technique

Reponds UNIQUEMENT avec le JSON suivant. Aucun texte avant ou apres.

{{
    "pertinence_client": 0,
    "coherence_donnees": 0,
    "qualite_commerciale": 0,
    "score_global": 0.0,
    "commentaire": "Explication courte des points forts et points faibles"
}}
"""


class EvaluateurAgent4:

    def __init__(self):
        self.agent_config = AgentConfigurateur()
        self.agent_optim  = AgentOptimiseur()
        self.agent_docs   = AgentDocuments()

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        self.prompt = PromptTemplate(
            input_variables=["client", "secteur", "taille", "solutions",
                             "prix_annuel", "pourquoi", "benefice_1",
                             "benefice_2", "benefice_3", "cas_usage", "conclusion"],
            template=PROMPT_JUGE,
        )
        self.chain = self.prompt | self.llm

    # ═══════════════════════════════════════════════════════════════
    # 1. LLM-AS-JUDGE
    # ═══════════════════════════════════════════════════════════════

    def _evaluer_llm_judge(self, cas_avec_resultats: list) -> dict:
        notes = []

        for item in cas_avec_resultats:
            data   = item["data"]
            textes = item["textes"]
            nom    = data.get("client", "")

            try:
                reponse = self.chain.invoke({
                    "client":     nom,
                    "secteur":    data.get("secteur", ""),
                    "taille":     data.get("taille", ""),
                    "solutions":  data.get("solutions", ""),
                    "prix_annuel": f"{data.get('prix_total_annuel', 0):,.0f}",
                    "pourquoi":   textes.get("pourquoi", ""),
                    "benefice_1": textes.get("benefice_1", ""),
                    "benefice_2": textes.get("benefice_2", ""),
                    "benefice_3": textes.get("benefice_3", ""),
                    "cas_usage":  textes.get("cas_usage", ""),
                    "conclusion": textes.get("conclusion", ""),
                })

                brut = reponse.content.strip()
                m    = re.search(r"\{.*\}", brut, re.DOTALL)
                note = json.loads(m.group()) if m else {}

                scores = [
                    note.get("pertinence_client", 0),
                    note.get("coherence_donnees", 0),
                    note.get("qualite_commerciale", 0),
                ]
                note["score_global"] = round(sum(scores) / len(scores), 2)

                print(f"    {nom} -> score={note['score_global']}/5 | "
                      f"pertinence={note.get('pertinence_client')}/5 | "
                      f"coherence={note.get('coherence_donnees')}/5 | "
                      f"ton={note.get('qualite_commerciale')}/5")
                print(f"    Commentaire : {note.get('commentaire', '')}")

                notes.append(note)

            except Exception as e:
                print(f"    Erreur juge [{nom}] : {e}")

        if not notes:
            return {"score_global": 0.0, "pertinence_client": 0.0,
                    "coherence_donnees": 0.0, "qualite_commerciale": 0.0}

        return {
            "score_global":        round(sum(n["score_global"]            for n in notes) / len(notes), 2),
            "pertinence_client":   round(sum(n.get("pertinence_client",  0) for n in notes) / len(notes), 2),
            "coherence_donnees":   round(sum(n.get("coherence_donnees",  0) for n in notes) / len(notes), 2),
            "qualite_commerciale": round(sum(n.get("qualite_commerciale",0) for n in notes) / len(notes), 2),
        }

    # ═══════════════════════════════════════════════════════════════
    # 2. BERTSCORE
    # ═══════════════════════════════════════════════════════════════

    def _evaluer_bertscore(self, cas_avec_resultats: list) -> dict:
        candidats  = []
        references = []

        for item in cas_avec_resultats:
            textes = item["textes"]
            ref    = item["cas"].get("reference_bertscore", "")
            cand   = " ".join(filter(None, [
                textes.get("pourquoi", ""),
                textes.get("benefice_1", ""),
                textes.get("conclusion", ""),
            ]))
            if cand.strip() and ref.strip():
                candidats.append(cand)
                references.append(ref)

        if not candidats:
            return {"bertscore_f1": 0.0, "bertscore_precision": 0.0, "bertscore_recall": 0.0}

        print("\n  Calcul BERTScore...")
        P, R, F1 = bert_score_fn(candidats, references, lang="fr", verbose=False)
        return {
            "bertscore_precision": round(float(P.mean()), 4),
            "bertscore_recall":    round(float(R.mean()), 4),
            "bertscore_f1":        round(float(F1.mean()), 4),
        }

    # ═══════════════════════════════════════════════════════════════
    # ÉVALUATION PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def evaluer(self, fichier: str = "evaluation/cas_tests/cas_agent4.json") -> dict:
        with open(fichier, 'r', encoding='utf-8') as f:
            cas_tests = json.load(f)

        print(f"\n{'='*60}")
        print("  EVALUATION AGENT 4 — LLM-Judge + BERTScore")
        print(f"{'='*60}")
        print(f"  Nombre de cas : {len(cas_tests)}\n")

        os.makedirs(DOSSIER_TEST, exist_ok=True)
        cas_avec_resultats = []

        for i, cas in enumerate(cas_tests, 1):
            print(f"  Cas {i}/{len(cas_tests)} [{cas.get('id')}] {cas['input_agent1'].get('nom_entreprise','')}")
            try:
                analyse  = cas["input_agent1"]
                config   = self.agent_config.configurer(analyse)
                resultat = self.agent_optim.optimiser(analyse, config)
                chemins  = self.agent_docs.generer(
                    analyse, config, resultat,
                    dossier_sortie=DOSSIER_TEST,
                )
                cas_avec_resultats.append({
                    "cas":    cas,
                    "data":   chemins["data"],
                    "textes": chemins["textes"],
                })
            except Exception as e:
                print(f"  [ERREUR] {e}")

        print("\n  LLM-as-Judge en cours...")
        juge = self._evaluer_llm_judge(cas_avec_resultats)
        bert = self._evaluer_bertscore(cas_avec_resultats)

        resultats = {
            "llm_judge": juge,
            "bertscore": bert,
        }

        print(f"\n{'='*60}")
        print("  RÉSULTATS")
        print(f"{'='*60}")
        print(f"  LLM Judge score global    : {juge['score_global']}/5")
        print(f"  Pertinence client         : {juge['pertinence_client']}/5")
        print(f"  Coherence donnees         : {juge['coherence_donnees']}/5")
        print(f"  Qualite commerciale       : {juge['qualite_commerciale']}/5")
        print(f"  BERTScore F1              : {bert['bertscore_f1']:.4f}  ({bert['bertscore_f1']*100:.1f}%)")
        print(f"  BERTScore Precision       : {bert['bertscore_precision']:.4f}")
        print(f"  BERTScore Rappel          : {bert['bertscore_recall']:.4f}")

        os.makedirs("evaluation/resultats", exist_ok=True)
        with open("evaluation/resultats/resultats_agent4.json", 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=2, ensure_ascii=False)
        print(f"\n  Resultats sauvegardes : evaluation/resultats/resultats_agent4.json")

        shutil.rmtree(DOSSIER_TEST, ignore_errors=True)
        return resultats


if __name__ == "__main__":
    EvaluateurAgent4().evaluer()
