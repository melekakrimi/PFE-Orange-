# api.py
"""
Backend FastAPI — Orange Business AI
Expose le pipeline multi-agents via HTTP pour l'interface React.

Lancement : python api.py
URL       : http://localhost:8000
"""

import os
import sys
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.agent_analyste      import AgentAnalyste
from agents.agent_configurateur import AgentConfigurateur
from agents.agent_optimiseur    import AgentOptimiseur
from agents.agent_documents     import AgentDocuments
from database.db_manager        import (sauvegarder_client,
                                        sauvegarder_proposition,
                                        sauvegarder_documents,
                                        sauvegarder_log,
                                        get_historique,
                                        get_proposition_detail)

app = FastAPI(title="Orange Business AI", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = os.path.dirname(os.path.abspath(__file__))


# ── Schémas ────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    description: str


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "Orange Business AI"}


@app.post("/generate")
def generate(req: GenerateRequest):
    t_global = time.time()

    # ── Agent 1 : Analyste ──────────────────────────────────────────
    t1 = time.time()
    analyse = AgentAnalyste().analyser(req.description)
    dur1 = round(time.time() - t1, 1)

    if "erreur" in analyse:
        raise HTTPException(status_code=422, detail=analyse["erreur"])

    # ── Agent 2 : Configurateur ─────────────────────────────────────
    t2 = time.time()
    configuration = AgentConfigurateur().configurer(analyse)
    dur2 = round(time.time() - t2, 1)

    # ── Agent 3 : Optimiseur ────────────────────────────────────────
    t3 = time.time()
    resultat = AgentOptimiseur().optimiser(analyse, configuration)
    dur3 = round(time.time() - t3, 1)

    # ── Agent 4 : Documents ─────────────────────────────────────────
    t4 = time.time()
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    dossier = os.path.join(ROOT, "output", ts)
    chemins = AgentDocuments().generer(analyse, configuration, resultat, dossier)
    dur4 = round(time.time() - t4, 1)

    t_total = round(time.time() - t_global, 1)

    # ── Sauvegarde DB ───────────────────────────────────────────────
    proposition_id = None
    try:
        client_id      = sauvegarder_client(analyse)
        proposition_id = sauvegarder_proposition(
            client_id, analyse, resultat, req.description
        )
        sauvegarder_documents(proposition_id, chemins)
        sauvegarder_log(proposition_id, "api", "succes")
    except Exception as e:
        print(f"  Avertissement DB : {e}")

    # ── Chemins relatifs pour le téléchargement ─────────────────────
    def rel(path):
        if not path:
            return None
        return os.path.relpath(path, ROOT).replace("\\", "/")

    prix_annuel  = resultat.get("prix_total_annuel", 0)
    prix_mensuel = round(prix_annuel / 12, 0)

    return {
        # Infos client
        "client":  analyse.get("nom_entreprise", ""),
        "secteur": analyse.get("secteur", ""),
        "taille":  analyse.get("taille_entreprise", ""),

        # Pricing
        "prix_annuel":  prix_annuel,
        "prix_mensuel": prix_mensuel,
        "taux_marge":   resultat.get("taux_marge", 0),
        "contrainte_ok": resultat.get("contrainte_ok", True),

        # Solutions
        "fibre":     resultat.get("fibre"),
        "microsoft": resultat.get("microsoft"),

        # Texte commercial
        "pitch_commercial":      resultat.get("pitch_commercial", ""),
        "arguments_negociation": resultat.get("arguments_negociation", []),

        # Fichiers générés
        "pptx_path": rel(chemins.get("pptx")),
        "word_path": rel(chemins.get("word")),
        "pdf_path":  rel(chemins.get("pdf")),

        # Méta
        "proposition_id":  proposition_id,
        "temps_generation": t_total,
        "agent_times": [
            {"label": "Agent 1", "name": "Analyste",      "time": f"{dur1}s"},
            {"label": "Agent 2", "name": "Configurateur", "time": f"{dur2}s"},
            {"label": "Agent 3", "name": "Optimiseur",    "time": f"{dur3}s"},
            {"label": "Agent 4", "name": "Documents",     "time": f"{dur4}s"},
        ],
    }


@app.get("/history")
def history():
    """Retourne l'historique des propositions pour la sidebar."""
    try:
        rows = get_historique()
        return [dict(r) for r in rows]
    except Exception as e:
        return []


@app.get("/proposition/{proposition_id}")
def proposition_detail(proposition_id: int):
    """Retourne le détail complet d'une proposition pour la recharger."""
    try:
        data = get_proposition_detail(proposition_id)
        if not data:
            raise HTTPException(status_code=404, detail="Proposition introuvable")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filepath:path}")
def download(filepath: str):
    full = os.path.join(ROOT, filepath)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(full, filename=os.path.basename(full))


# ── Lancement ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n" + "█" * 50)
    print("  Orange Business AI — Backend FastAPI")
    print("  http://localhost:8000")
    print("█" * 50 + "\n")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
