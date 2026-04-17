# agents/agent_configurateur.py
"""
Agent 2 : Configurateur de solutions Orange Business

Technique : Chain-of-Thought (CoT) + Grounded Generation
- Microsoft : le LLM reçoit le catalogue des 4 plans et les services demandés,
                il choisit le plan exact qui couvre les besoins (pas plus, pas moins).
- Fibre     : calcul déterministe selon le débit exact demandé par le client.

Résultat : UNE SEULE configuration (pas de scénarios multiples).
"""

import os
import sys
import json
import re
import pandas as pd
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.prompt_configurateur import TEMPLATE_CONFIGURATEUR_MICROSOFT

load_dotenv()


class AgentConfigurateur:
    """
    Agent 2 : Retourne la configuration exacte correspondant aux besoins du client.

    FIBRE — calcul déterministe :
        Coût fixe (one-time) : distance × 50 + routeur 300 + installation 200 TND
        Coût mensuel         : débit × 1.2 TND/mois
        Prix de vente        : débit × 10 TND/mois
        Engagement           : 24 mois (si marge positive) sinon 12 mois

    MICROSOFT — sélection par LLM (Chain-of-Thought) :
        Catalogue : 4 plans (Exchange Online Plan 1 / Basic / Standard / Premium)
        Logique   : plan minimum qui couvre tous les services demandés
        Marge     : 14% fixe Orange (déjà incluse dans le prix du CSV)
    """

    # ── Tarifs Fibre Orange Business ───────────────────────────────
    FIBRE_COUT_PAR_METRE      = 50
    FIBRE_COUT_ROUTEUR        = 300
    FIBRE_COUT_INSTALLATION   = 200
    FIBRE_COUT_PAR_MBPS       = 1.2
    FIBRE_PRIX_VENTE_PAR_MBPS = 10.0
    FIBRE_PALIERS_DEBIT       = [50, 100, 200, 500, 1000]

    MAX_RETRIES = 3

    def __init__(self):
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "orange_propre", "Microsoft licence.csv"
        )
        self.catalogue_df = pd.read_csv(csv_path)
        print(f" Catalogue Microsoft : {len(self.catalogue_df)} plans charges")
        print(" Catalogue Fibre : modele de calcul Orange Business")

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )

        self.prompt = PromptTemplate(
            input_variables=[
                "catalogue_plans",
                "description_client",
                "nombre_licences",
                "services_demandes",
            ],
            template=TEMPLATE_CONFIGURATEUR_MICROSOFT
        )

        self.chain = self.prompt | self.llm

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def configurer(self, analyse_agent1: dict) -> dict:
        """Retourne la configuration exacte (Fibre + Microsoft) selon les besoins."""
        print("\n" + "=" * 70)
        print(" Configuration des solutions Orange")
        print("=" * 70)

        resultats = {}

        if analyse_agent1.get("besoins_fibre", {}).get("demande_fibre", False):
            print("\n Configuration Fibre...")
            resultats["fibre"] = self._configurer_fibre(analyse_agent1)
        else:
            resultats["fibre"] = None

        if analyse_agent1.get("besoins_microsoft", {}).get("demande_microsoft", False):
            print("\n Configuration Microsoft...")
            resultats["microsoft"] = self._configurer_microsoft(analyse_agent1)
        else:
            resultats["microsoft"] = None

        return resultats

    # ═══════════════════════════════════════════════════════════════
    # CONFIGURATION MICROSOFT
    # ═══════════════════════════════════════════════════════════════

    def _configurer_microsoft(self, analyse_agent1: dict) -> dict:
        """
        Appelle le LLM avec le catalogue et les services demandés.
        Le LLM retourne le plan exact qui couvre les besoins du client.
        """
        besoins_ms      = analyse_agent1.get("besoins_microsoft", {})
        services        = besoins_ms.get("services", {})
        nombre_licences = int(besoins_ms.get("nombre_licences", 1) or 1)

        inputs = {
            "catalogue_plans":    self._formater_catalogue(),
            "description_client": self._construire_description(analyse_agent1),
            "nombre_licences":    nombre_licences,
            "services_demandes":  self._formater_services(services),
        }

        for tentative in range(1, self.MAX_RETRIES + 1):
            print(f"  -> Tentative {tentative}/{self.MAX_RETRIES}...")
            try:
                resultat = self.chain.invoke(inputs)
                data     = self._parser_json(resultat.content)
                self._valider_et_corriger(data, nombre_licences)
                print(" Plan Microsoft selectionne :", data["nom_produit"])
                return data
            except json.JSONDecodeError as e:
                print(f"    JSON invalide : {e}")
            except ValueError as e:
                print(f"    Validation echouee : {e}")
            except Exception as e:
                print(f"    Erreur : {e}")

        print(f" Echec apres {self.MAX_RETRIES} tentatives")
        return None

    def _formater_catalogue(self) -> str:
        """Formate le catalogue CSV en tableau lisible pour le LLM."""
        lignes = []
        entete = (
            f"{'Plan':<35} {'OneDrive':<10} {'SharePoint':<12} {'Mail':<6} "
            f"{'Pack Office':<13} {'Intune':<8} {'Defender':<10} Prix/an/licence (TND)"
        )
        lignes.append(entete)
        lignes.append("-" * 105)
        for _, row in self.catalogue_df.iterrows():
            lignes.append(
                f"{row['nom_produit']:<35} {row['onedrive']:<10} {row['sharepoint']:<12} "
                f"{row['mail']:<6} {row['pack_office']:<13} {row['intune']:<8} "
                f"{row['defender']:<10} {row['prix_annuel_tnd']}"
            )
        return "\n".join(lignes)

    def _formater_services(self, services: dict) -> str:
        """Formate les services demandés en texte lisible."""
        if not services:
            return "Non specifie"
        actifs = [s for s, v in services.items() if v]
        return ", ".join(actifs) if actifs else "mail uniquement"

    def _valider_et_corriger(self, data: dict, nombre_licences: int) -> None:
        """Vérifie la structure JSON, corrige le prix total et le product_id."""
        champs = ["nom_produit", "product_id", "prix_unitaire_tnd",
                    "nombre_licences", "prix_total_annuel", "justification"]
        manquants = [c for c in champs if c not in data]
        if manquants:
            raise ValueError(f"Champs manquants : {manquants}")

        # Corriger le product_id si le LLM a mis le nom à la place
        nom = data["nom_produit"]
        ligne = self.catalogue_df[self.catalogue_df["nom_produit"] == nom]
        if not ligne.empty:
            data["product_id"] = ligne.iloc[0]["product_id"]
        else:
            # Recherche partielle
            for _, row in self.catalogue_df.iterrows():
                if row["nom_produit"].lower() in nom.lower() or nom.lower() in row["nom_produit"].lower():
                    data["nom_produit"] = row["nom_produit"]
                    data["product_id"]  = row["product_id"]
                    break

        # Corriger le prix total si mal calculé
        pu         = float(data["prix_unitaire_tnd"])
        pt_attendu = round(pu * nombre_licences, 2)
        pt_fourni  = float(data.get("prix_total_annuel", 0))
        if abs(pt_attendu - pt_fourni) > 1:
            print(f"    Correction prix : {pu} x {nombre_licences} = {pt_attendu} TND")
        data["prix_total_annuel"] = pt_attendu
        data["nombre_licences"]   = nombre_licences

    # ═══════════════════════════════════════════════════════════════
    # CONFIGURATION FIBRE
    # ═══════════════════════════════════════════════════════════════

    def _configurer_fibre(self, analyse_agent1: dict) -> dict:
        """
        Calcule la configuration Fibre exacte selon le débit demandé.
        Engagement 24 mois (marge optimale), 12 mois si 24 non rentable.
        """
        besoins         = analyse_agent1.get("besoins_fibre", {})
        debit_souhaite  = int(besoins.get("debit_souhaite_mbps", 100) or 100)
        distance_metres = int(besoins.get("distance_metres", 100) or 100)

        debit = self._palier_debit(debit_souhaite)

        # Essayer 24 mois d'abord
        calc = self._calculer_fibre(debit, distance_metres, 24)
        raison_engagement = "Engagement 24 mois (marge optimale)"

        if not calc["marge_positive"]:
            # Essayer 12 mois
            calc12 = self._calculer_fibre(debit, distance_metres, 12)
            if calc12["marge_positive"]:
                calc = calc12
                raison_engagement = "Engagement 12 mois (24M non rentable sur cette distance)"
            else:
                # Limiter la distance
                dmax = self._distance_max(debit, 24)
                calc = self._calculer_fibre(debit, dmax, 24)
                raison_engagement = f"Distance limitee a {dmax}m pour marge positive"
                print(f"  Alerte : distance {distance_metres}m trop elevee, limitee a {dmax}m")

        print(f" Fibre : {debit} Mbps, {calc['engagement_mois']} mois, "
                f"marge {calc['marge_pct']}%")

        return {
            "nom_offre":          f"Fibre Orange Business {debit}M",
            "debit_mbps":         calc["debit_mbps"],
            "engagement_mois":    calc["engagement_mois"],
            "distance_metres":    calc["distance_metres"],
            "cout_initial_total": calc["cout_initial_total"],
            "cout_mensuel_total": calc["cout_mensuel_total"],
            "prix_mensuel_total": calc["prix_mensuel_total"],
            "marge_pct":          calc["marge_pct"],
            "marge_tnd":          calc["marge_tnd"],
            "raison_engagement":  raison_engagement,
        }

    def _calculer_fibre(self, debit_mbps: int, distance_metres: int, engagement_mois: int) -> dict:
        cout_fo            = distance_metres * self.FIBRE_COUT_PAR_METRE
        cout_initial_total = round(cout_fo + self.FIBRE_COUT_ROUTEUR + self.FIBRE_COUT_INSTALLATION, 2)
        cout_mensuel_total = round(debit_mbps * self.FIBRE_COUT_PAR_MBPS, 2)
        prix_mensuel_total = round(debit_mbps * self.FIBRE_PRIX_VENTE_PAR_MBPS, 2)

        cout_total   = round(cout_initial_total + cout_mensuel_total * engagement_mois, 2)
        revenu_total = round(prix_mensuel_total * engagement_mois, 2)
        marge_tnd    = round(revenu_total - cout_total, 2)
        marge_pct    = round(marge_tnd / revenu_total * 100, 1) if revenu_total > 0 else 0

        return {
            "debit_mbps":         debit_mbps,
            "engagement_mois":    engagement_mois,
            "distance_metres":    distance_metres,
            "cout_initial_total": cout_initial_total,
            "cout_mensuel_total": cout_mensuel_total,
            "prix_mensuel_total": prix_mensuel_total,
            "marge_pct":          marge_pct,
            "marge_tnd":          marge_tnd,
            "marge_positive":     marge_tnd > 0,
        }

    def _distance_max(self, debit_mbps: int, engagement_mois: int) -> int:
        prix   = debit_mbps * self.FIBRE_PRIX_VENTE_PAR_MBPS
        cout_m = debit_mbps * self.FIBRE_COUT_PAR_MBPS
        budget_fixe = (prix - cout_m) * engagement_mois - self.FIBRE_COUT_ROUTEUR - self.FIBRE_COUT_INSTALLATION
        return max(0, int(budget_fixe / self.FIBRE_COUT_PAR_METRE))

    def _palier_debit(self, debit_min: float) -> int:
        for p in self.FIBRE_PALIERS_DEBIT:
            if p >= debit_min:
                return p
        return self.FIBRE_PALIERS_DEBIT[-1]

    # ═══════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════════

    def _construire_description(self, analyste: dict) -> str:
        return "\n".join([
            f"Entreprise : {analyste.get('nom_entreprise', 'Non specifie')}",
            f"Secteur    : {analyste.get('secteur', 'Non specifie')}",
            f"Taille     : {analyste.get('taille_entreprise', 'Non specifie')}",
            f"Urgence    : {analyste.get('urgence', 'moyen')}",
        ])

    def _parser_json(self, texte: str) -> dict:
        texte = texte.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", texte)
        if match:
            texte = match.group(1).strip()
        else:
            match = re.search(r"(\{[\s\S]*\})", texte)
            if match:
                texte = match.group(1).strip()
        return json.loads(texte)


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    agent = AgentConfigurateur()

    print("\n" + "=" * 70)
    print(" TEST 1 : Client veut juste le mail")
    print("=" * 70)
    analyse1 = {
        "nom_entreprise": "BoutiqueArt",
        "secteur": "Commerce", "taille_entreprise": "TPE", "urgence": "faible",
        "besoins_fibre": {"demande_fibre": False},
        "besoins_microsoft": {
            "demande_microsoft": True, "nombre_licences": 5,
            "services": {"onedrive": False, "sharepoint": False, "mail": True,
                            "pack_office": False, "intune": False, "defender": False}
        }
    }
    r1 = agent.configurer(analyse1)
    print(json.dumps(r1, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print(" TEST 2 : Client veut Fibre 200M + OneDrive + Pack Office")
    print("=" * 70)
    analyse2 = {
        "nom_entreprise": "DevSoft",
        "secteur": "Tech", "taille_entreprise": "PME", "urgence": "haute",
        "besoins_fibre": {"demande_fibre": True, "debit_souhaite_mbps": 200, "distance_metres": 80},
        "besoins_microsoft": {
            "demande_microsoft": True, "nombre_licences": 20,
            "services": {"onedrive": True, "sharepoint": True, "mail": True,
                            "pack_office": True, "intune": False, "defender": False}
        }
    }
    r2 = agent.configurer(analyse2)
    print(json.dumps(r2, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print(" TEST 3 : Client veut antivirus + gestion appareils (Defender + Intune)")
    print("=" * 70)
    analyse3 = {
        "nom_entreprise": "SecureBank",
        "secteur": "Banque", "taille_entreprise": "ETI", "urgence": "haute",
        "besoins_fibre": {"demande_fibre": False},
        "besoins_microsoft": {
            "demande_microsoft": True, "nombre_licences": 50,
            "services": {"onedrive": True, "sharepoint": True, "mail": True,
                            "pack_office": True, "intune": True, "defender": True}
        }
    }
    r3 = agent.configurer(analyse3)
    print(json.dumps(r3, indent=2, ensure_ascii=False))
    print("\n Tests Agent 2 termines !")