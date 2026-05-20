# database/db_manager.py
"""
Gestionnaire de base de données PostgreSQL pour le projet PFE Orange.
Fonctions de sauvegarde des résultats des 4 agents.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


def _get_connexion():
    """Retourne une connexion PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5433),
        dbname=os.getenv("DB_NAME", "pfe_orange"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )


# ═══════════════════════════════════════════════════════════════
# 1. SAUVEGARDER CLIENT
# ═══════════════════════════════════════════════════════════════

def sauvegarder_client(analyse: dict) -> int:
    """
    Insère ou récupère un client depuis la base.
    Retourne l'id du client.
    """
    conn = _get_connexion()
    try:
        with conn.cursor() as cur:
            # Vérifier si le client existe déjà
            cur.execute(
                "SELECT id FROM clients WHERE entreprise = %s",
                (analyse.get("nom_entreprise", ""),)
            )
            row = cur.fetchone()
            if row:
                return row[0]

            # Sinon insérer
            cur.execute("""
                INSERT INTO clients (nom, entreprise, secteur, taille)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                analyse.get("nom_entreprise", ""),
                analyse.get("nom_entreprise", ""),
                analyse.get("secteur", ""),
                analyse.get("taille_entreprise", ""),
            ))
            client_id = cur.fetchone()[0]
            conn.commit()
            print(f"  [DB] Client sauvegardé : id={client_id}")
            return client_id
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 2. SAUVEGARDER PROPOSITION + SCÉNARIOS
# ═══════════════════════════════════════════════════════════════

def sauvegarder_proposition(client_id: int, analyse: dict,
                            resultat_agent3: dict, description: str) -> int:
    """
    Insère la proposition + configuration unique (fibre + microsoft).
    Retourne l'id de la proposition.
    """
    conn = _get_connexion()
    try:
        with conn.cursor() as cur:
            ms    = resultat_agent3.get("microsoft") or {}
            fibre = resultat_agent3.get("fibre") or {}
            plan_rec = ms.get("nom_produit", "") or fibre.get("nom_offre", "")

            # Insérer proposition
            cur.execute("""
                INSERT INTO propositions
                    (client_id, besoin_client, plan_recommande, urgence, statut)
                VALUES (%s, %s, %s, %s, 'brouillon')
                RETURNING id
            """, (
                client_id,
                description,
                plan_rec,
                analyse.get("urgence", ""),
            ))
            proposition_id = cur.fetchone()[0]

            # Insérer le scénario unique
            cur.execute("""
                INSERT INTO scenarios
                    (proposition_id, nom_scenario, cout_revient, prix_vente,
                     marge_brute, taux_marge, est_recommande)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                proposition_id,
                plan_rec,
                resultat_agent3.get("cout_total_annuel", 0),
                resultat_agent3.get("prix_total_annuel", 0),
                resultat_agent3.get("marge_brute", 0),
                resultat_agent3.get("taux_marge", 0),
                True,
            ))
            scenario_id = cur.fetchone()[0]

            # Fibre
            if fibre:
                cur.execute("""
                    INSERT INTO fibre_config
                        (scenario_id, nom_offre, debit_mbps, engagement_mois,
                         distance_metres, cout_initial, cout_mensuel,
                         prix_mensuel, prix_annuel, marge_pct)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    scenario_id,
                    fibre.get("nom_offre", ""),
                    fibre.get("debit_mbps", 0),
                    fibre.get("engagement_mois", 0),
                    fibre.get("distance_metres", 0),
                    fibre.get("cout_initial_total", 0),
                    fibre.get("cout_mensuel_total", 0),
                    fibre.get("prix_mensuel_total", 0),
                    fibre.get("prix_annuel", 0),
                    fibre.get("marge_pct_fibre", 0),
                ))

            # Microsoft
            if ms:
                cur.execute("""
                    INSERT INTO microsoft_config
                        (scenario_id, nom_produit, product_id, nombre_licences,
                         prix_unitaire, prix_annuel, cout_annuel)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    scenario_id,
                    ms.get("nom_produit", ""),
                    ms.get("product_id", ""),
                    ms.get("nombre_licences", 0),
                    ms.get("prix_unitaire_tnd", 0),
                    ms.get("prix_annuel", 0),
                    ms.get("cout_annuel", 0),
                ))

            conn.commit()
            print(f"  [DB] Proposition sauvegardée : id={proposition_id}")
            return proposition_id

    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 3. SAUVEGARDER DOCUMENTS
# ═══════════════════════════════════════════════════════════════

def sauvegarder_documents(proposition_id: int, chemins: dict) -> None:
    """
    Insère les chemins des 3 fichiers générés par Agent 4.
    chemins = {"pptx": "...", "pdf": "...", "docx": "..."}
    """
    conn = _get_connexion()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                    (proposition_id, chemin_pptx, chemin_pdf, chemin_docx)
                VALUES (%s, %s, %s, %s)
            """, (
                proposition_id,
                chemins.get("pptx", ""),
                chemins.get("pdf", ""),
                chemins.get("docx", ""),
            ))
            conn.commit()
            print(f"  [DB] Documents sauvegardés : proposition_id={proposition_id}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 4. SAUVEGARDER LOG AGENT
# ═══════════════════════════════════════════════════════════════

def sauvegarder_log(proposition_id: int, agent_nom: str,
                    statut: str, message: str = "") -> None:
    """
    Insère un log d'exécution d'un agent.
    statut = 'succes' ou 'erreur'
    """
    conn = _get_connexion()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO logs_agents
                    (proposition_id, agent_nom, statut, message)
                VALUES (%s, %s, %s, %s)
            """, (proposition_id, agent_nom, statut, message))
            conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 5. RÉCUPÉRER L'HISTORIQUE
# ═══════════════════════════════════════════════════════════════

def get_historique() -> list:
    """Retourne toutes les propositions avec les infos client, triées par date."""
    conn = _get_connexion()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.id,
                    c.entreprise,
                    c.secteur,
                    c.taille,
                    p.plan_recommande,
                    p.statut,
                    p.created_at,
                    s.prix_vente   AS prix_annuel,
                    s.taux_marge,
                    EXISTS(SELECT 1 FROM fibre_config     fc WHERE fc.scenario_id = s.id) AS a_fibre,
                    EXISTS(SELECT 1 FROM microsoft_config mc WHERE mc.scenario_id = s.id) AS a_microsoft
                FROM propositions p
                JOIN clients   c ON c.id = p.client_id
                LEFT JOIN scenarios s ON s.proposition_id = p.id AND s.est_recommande = TRUE
                ORDER BY p.created_at DESC
                LIMIT 50
            """)
            return cur.fetchall()
    finally:
        conn.close()


def get_proposition_detail(proposition_id: int) -> dict:
    """Retourne toutes les données d'une proposition pour la recharger dans l'interface."""
    conn = _get_connexion()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Proposition + client
            cur.execute("""
                SELECT p.*, c.entreprise, c.secteur, c.taille
                FROM propositions p
                JOIN clients c ON c.id = p.client_id
                WHERE p.id = %s
            """, (proposition_id,))
            prop = cur.fetchone()
            if not prop:
                return None
            prop = dict(prop)

            # Scénario recommandé
            cur.execute("""
                SELECT * FROM scenarios
                WHERE proposition_id = %s AND est_recommande = TRUE
                LIMIT 1
            """, (proposition_id,))
            scenario = cur.fetchone()
            if not scenario:
                return prop
            scenario = dict(scenario)

            # Fibre
            cur.execute("SELECT * FROM fibre_config WHERE scenario_id = %s", (scenario["id"],))
            fibre = cur.fetchone()

            # Microsoft
            cur.execute("SELECT * FROM microsoft_config WHERE scenario_id = %s", (scenario["id"],))
            ms = cur.fetchone()

            # Documents
            cur.execute("SELECT * FROM documents WHERE proposition_id = %s LIMIT 1", (proposition_id,))
            docs = cur.fetchone()

            prix_annuel  = scenario.get("prix_vente", 0) or 0
            prix_mensuel = round(prix_annuel / 12, 0)

            def rel(path):
                if not path:
                    return None
                return path.replace("\\", "/")

            return {
                "client":    prop.get("entreprise", ""),
                "secteur":   prop.get("secteur", ""),
                "taille":    prop.get("taille", ""),
                "prix_annuel":  prix_annuel,
                "prix_mensuel": prix_mensuel,
                "taux_marge":   scenario.get("taux_marge", 0),
                "contrainte_ok": True,
                "fibre": dict(fibre) if fibre else None,
                "microsoft": {
                    "nom_produit":      ms.get("nom_produit", ""),
                    "nombre_licences":  ms.get("nombre_licences", 0),
                    "prix_unitaire_tnd": ms.get("prix_unitaire", 0),
                    "prix_annuel":      ms.get("prix_annuel", 0),
                } if ms else None,
                "pitch_commercial": f"Proposition commerciale Orange Business pour {prop.get('entreprise', '')} — {prop.get('plan_recommande', '')}.",
                "pptx_path": rel(docs.get("chemin_pptx")) if docs else None,
                "word_path": rel(docs.get("chemin_docx")) if docs else None,
                "pdf_path":  rel(docs.get("chemin_pdf"))  if docs else None,
                "proposition_id": proposition_id,
                "temps_generation": None,
                "agent_times": None,
            }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        conn = _get_connexion()
        conn.close()
        print("[DB] Connexion PostgreSQL reussie !")

        # Test sauvegarde client
        analyse_test = {
            "nom_entreprise": "DevSoft",
            "secteur": "Tech",
            "taille_entreprise": "PME",
            "urgence": "haute"
        }
        client_id = sauvegarder_client(analyse_test)
        print(f"[DB] Client id : {client_id}")

    except Exception as e:
        print(f"[DB] Erreur : {e}")
