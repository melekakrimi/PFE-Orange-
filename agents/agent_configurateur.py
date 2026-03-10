# agents/agent_configurateur.py
import os
import sys
import json
import re
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# Lier au dossier prompts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.prompt_configurateur import TEMPLATE_CONFIGURATEUR_MICROSOFT

load_dotenv()

class AgentConfigurateur:
    """
    Agent 2 : Configure des solutions Fibre + Microsoft selon les besoins analysés
    
    IMPORTANT - Calcul des prix :
    =============================
    
    MICROSOFT :
    - UnitPrice(DT) dans le CSV = Prix d'ACHAT annuel Orange (coût de revient)
    - Marge commerciale Orange = 14% (taux officiel confirmé par encadrant)
    - Prix de vente client = Prix d'achat × 1.14
    
    FIBRE :
    - Prix actuels = Prix publics Orange Tunisie (provisoires)
    - À REMPLACER par coûts réels fournis par l'encadrant
    - Marge à définir selon politique Orange B2B
    """

    MAX_RETRIES = 3

    def __init__(self):
        # Charger les catalogues
        self.catalogue_microsoft_brut = pd.read_csv("data/orange_propre/catalogue_propre.csv")
        self.catalogue_microsoft = self._preparer_catalogue_microsoft(self.catalogue_microsoft_brut)
        
        # Charger le catalogue Fibre (prix publics provisoires)
        try:
            self.catalogue_fibre = pd.read_csv("data/orange_propre/catalogue_fibre_orange.csv")
            print(" Catalogue Fibre chargé (prix publics Orange.tn)")
        except FileNotFoundError:
            print("  Catalogue Fibre non trouvé, création d'un catalogue minimal...")
            self.catalogue_fibre = self._creer_catalogue_fibre_minimal()

        # Créer le modèle IA
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3
        )

        # Charger le prompt Microsoft
        self.prompt_microsoft = PromptTemplate(
            input_variables=[
                "description_client",
                "nombre_licences",
                "type_besoin",
                "services_mentionnes",
                "budget_mensuel",
                "catalogue_produits"
            ],
            template=TEMPLATE_CONFIGURATEUR_MICROSOFT
        )

        # Créer la chaîne Microsoft
        self.chain_microsoft = self.prompt_microsoft | self.llm

    def _creer_catalogue_fibre_minimal(self) -> pd.DataFrame:
        """Crée un catalogue Fibre minimal si le fichier n'existe pas"""
        data = {
            'id': [1, 2, 3, 4, 5, 6, 7],
            'nom_offre': [
                'Fibre Basic 50M', 'Fibre Standard 100M', 'Fibre Pro 50M',
                'Fibre Premium 100M', 'Fibre Business 200M',
                'Fibre Business 500M', 'Fibre Enterprise 1G'
            ],
            'debit_mbps': [50, 100, 50, 100, 200, 500, 1000],
            'prix_vente_mensuel_tnd': [69.9, 110.9, 64.9, 99.9, 180.0, 350.0, 600.0],
            'engagement_mois': [12, 12, 12, 12, 12, 12, 12],
            'type_client': [
                'Particulier', 'Particulier', 'Professionnel', 'Professionnel',
                'Entreprise', 'Entreprise', 'Entreprise'
            ],
            'cout_installation_tnd': [100, 100, 150, 150, 300, 300, 500],
            'description': [
                'Connexion stable 50 Mbps',
                'Très Haut Débit 100 Mbps',
                'Fibre pro 50 Mbps avec support prioritaire',
                'Fibre pro 100 Mbps avec SLA',
                'Débit garanti 200 Mbps',
                'Débit garanti 500 Mbps',
                'Fibre dédiée 1 Gbps symétrique'
            ]
        }
        return pd.DataFrame(data)

    def _preparer_catalogue_microsoft(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforme le catalogue Microsoft brut en catalogue utilisable.
        Calcul avec marge Orange 14%.
        """
        df = df.copy()

        # Renommer les colonnes
        df = df.rename(columns={
            'ProductTitle':  'nom_service',
            'ProductId':     'product_id',
            'SkuId':         'sku_id',
            'TermDuration':  'duree',
            'BillingPlan':   'facturation',
            'UnitPrice(DT)': 'prix_annuel_achat'
        })

        # Garde tout sauf les lignes vraiment vides
        df = df[df['prix_annuel_achat'].notna()].copy()

        # Calcul des prix annuels (marge 14%) — catalogue 100% annuel
        df['cout_revient_tnd'] = df['prix_annuel_achat'].round(2)
        df['prix_vente_tnd']   = (df['cout_revient_tnd'] * 1.14).round(2)
        df['marge_pct'] = 14
        df['marge_tnd'] = (df['prix_vente_tnd'] - df['cout_revient_tnd']).round(2)

        # Classification par famille
        def classifier(nom):
            nom = str(nom).lower()
            if 'teams' in nom:                       return 'Teams'
            if 'exchange' in nom:                    return 'Exchange'
            if 'power bi' in nom:                    return 'Power BI'
            if 'power automate' in nom:              return 'Power Automate'
            if 'power apps' in nom:                  return 'Power Apps'
            if 'microsoft 365' in nom:               return 'Microsoft 365'
            if 'office 365' in nom:                  return 'Office 365'
            if 'defender' in nom:                    return 'Sécurité'
            if 'intune' in nom:                      return 'Intune'
            if 'entra' in nom:                       return 'Entra'
            if 'onedrive' in nom:                    return 'OneDrive'
            if 'purview' in nom:                     return 'Purview'
            if 'planner' in nom or 'project' in nom: return 'Planner & Project'
            return 'Autre'

        df['famille'] = df['nom_service'].apply(classifier)

        # Déduplication
        df['_sku_priority'] = df['sku_id'].apply(lambda x: 0 if str(x) == '1' else 1)
        df = df.sort_values(['nom_service', '_sku_priority', 'prix_vente_tnd'])
        df = df.drop_duplicates(subset=['nom_service']).reset_index(drop=True)
        df = df.drop(columns=['_sku_priority'])

        return df

    # ═══════════════════════════════════════════════════════════════
    # CONFIGURATION FIBRE
    # ═══════════════════════════════════════════════════════════════

    def configurer_fibre(self, analyse_agent1: dict) -> dict:
        """
        Configure 3 offres Fibre (Économique, Standard, Premium)
        selon les besoins analysés.
        """
        besoins_fibre = analyse_agent1.get("besoins_fibre", {})

        if not besoins_fibre.get("demande_fibre", False):
            return {
                "message": "Client ne demande pas de fibre optique",
                "configurations": None
            }

        # Extraire les paramètres
        debit_souhaite = int(besoins_fibre.get("debit_souhaite_mbps", 100) or 100)
        nombre_sites = int(besoins_fibre.get("nombre_sites", 1) or 1)
        distance_metres = int(besoins_fibre.get("distance_metres", 100) or 100)
        zone = besoins_fibre.get("zone", "urbain")

        # Déterminer le type de client (PME ou Entreprise)
        taille = analyse_agent1.get("taille_entreprise", "PME")
        if taille in ["ETI", "GE", "Grande Entreprise"]:
            type_client = "Entreprise"
        elif taille in ["PME", "TPE"]:
            type_client = "Professionnel"
        else:
            type_client = "Particulier"

        # Filtrer les offres selon le type client
        offres_disponibles = self.catalogue_fibre[
            (self.catalogue_fibre['type_client'] == type_client) |
            (self.catalogue_fibre['type_client'] == 'Entreprise')
        ].sort_values('prix_vente_mensuel_tnd')

        if len(offres_disponibles) == 0:
            offres_disponibles = self.catalogue_fibre.sort_values('prix_vente_mensuel_tnd')

        # Sélectionner 3 offres
        configurations = []

        # Économique : débit >= demandé, le moins cher
        eco = offres_disponibles[
            offres_disponibles['debit_mbps'] >= debit_souhaite
        ].head(1)

        if len(eco) == 0:
            eco = offres_disponibles.head(1)

        # Standard : débit confortable (1.5x demandé)
        std = offres_disponibles[
            offres_disponibles['debit_mbps'] >= debit_souhaite * 1.5
        ].iloc[0:1] if len(offres_disponibles) > 1 else offres_disponibles.iloc[1:2]

        # Premium : meilleur débit
        prem = offres_disponibles.tail(1)

        # Construire les configurations
        for idx, (niveau, offre_df) in enumerate([
            ("economique", eco),
            ("standard", std),
            ("premium", prem)
        ]):
            if len(offre_df) > 0:
                offre = offre_df.iloc[0]

                # Calcul coûts
                prix_mensuel = offre['prix_vente_mensuel_tnd'] * nombre_sites
                cout_installation = offre['cout_installation_tnd'] * nombre_sites

                # Coût génie civil si distance > 200m
                cout_genie_civil = 0
                if distance_metres and distance_metres > 200:
                    cout_genie_civil = (distance_metres - 200) * 50

                cout_total_initial = cout_installation + cout_genie_civil

                configurations.append({
                    "niveau": str(niveau),
                    "nom_offre": str(offre['nom_offre']),
                    "debit_mbps": int(offre['debit_mbps']),
                    "prix_mensuel_par_site": float(offre['prix_vente_mensuel_tnd']),
                    "nombre_sites": int(nombre_sites),
                    "prix_mensuel_total": float(round(prix_mensuel, 2)),
                    "cout_installation": float(round(cout_installation, 2)),
                    "cout_genie_civil": float(round(cout_genie_civil, 2)),
                    "cout_total_initial": float(round(cout_total_initial, 2)),
                    "engagement_mois": int(offre['engagement_mois']),
                    "description": str(offre['description']),
                    "justification": self._generer_justification_fibre(
                        niveau, offre, debit_souhaite, nombre_sites
                    )
                })

        # Déterminer la recommandation
        budget = analyse_agent1.get("budget_mensuel", 0)
        if budget and budget < 150:
            recommandation = "economique"
        elif budget and budget < 400:
            recommandation = "standard"
        else:
            recommandation = "premium"

        return {
            "configurations": configurations,
            "recommandation": recommandation,
            "note": "Prix basés sur tarifs publics Orange.tn - À actualiser avec coûts réels B2B"
        }

    def _generer_justification_fibre(self, niveau: str, offre, debit_souhaite: int, nombre_sites: int) -> str:
        """Génère une justification pour une offre Fibre"""
        justifications = {
            "economique": f"Offre la plus économique répondant au besoin de {debit_souhaite} Mbps. "
                            f"Débit de {int(offre['debit_mbps'])} Mbps pour {nombre_sites} site(s).",
            
            "standard": f"Bon équilibre entre performance et prix. "
                        f"Débit confortable de {int(offre['debit_mbps'])} Mbps pour anticiper la croissance.",
            
            "premium": f"Solution haut de gamme avec {int(offre['debit_mbps'])} Mbps. "
                        f"Performance maximale et fiabilité garantie pour activités critiques."
        }
        return justifications.get(niveau, "Configuration adaptée aux besoins")

    # ═══════════════════════════════════════════════════════════════
    # CONFIGURATION MICROSOFT (déjà existant)
    # ═══════════════════════════════════════════════════════════════

    def configurer_microsoft(self, analyste_agent1: dict) -> dict:
        """
        Configure 3 offres Microsoft (Économique, Standard, Premium)
        """
        besoins_ms = analyste_agent1.get("besoins_microsoft", {})

        if not besoins_ms.get("demande_microsoft", False):
            return {
                "message": "Client ne demande pas de services Microsoft",
                "configurations": None
            }

        catalogue_texte    = self._filtrer_catalogue(besoins_ms)
        description_client = self._construire_description(analyste_agent1)

        inputs = {
            "description_client":  description_client,
            "nombre_licences":     besoins_ms.get("nombre_licences", 0),
            "type_besoin":         besoins_ms.get("type_besoin", "Non spécifié"),
            "services_mentionnes": besoins_ms.get("services_mentionnes", []),
            "budget_mensuel":      analyste_agent1.get("budget_mensuel", "Non spécifié"),
            "catalogue_produits":  catalogue_texte
        }

        derniere_erreur = None
        for tentative in range(1, self.MAX_RETRIES + 1):
            print(f"  → Tentative {tentative}/{self.MAX_RETRIES}...")
            try:
                resultat       = self.chain_microsoft.invoke(inputs)
                configurations = self._parser_json(resultat.content)
                self._valider_configurations(configurations)
                self._verifier_prix(configurations, besoins_ms.get("nombre_licences", 0))
                print(" Configurations Microsoft générées avec succès")
                return configurations

            except json.JSONDecodeError as e:
                derniere_erreur = f"JSON invalide : {e}"
                print(f"    {derniere_erreur}")
            except ValueError as e:
                derniere_erreur = f"Validation échouée : {e}"
                print(f"    {derniere_erreur}")
            except Exception as e:
                derniere_erreur = str(e)
                print(f"    Erreur : {e}")

        print(f" Échec après {self.MAX_RETRIES} tentatives")
        return {"erreur": derniere_erreur}

    # ═══════════════════════════════════════════════════════════════
    # CONFIGURATION GLOBALE (Fibre + Microsoft)
    # ═══════════════════════════════════════════════════════════════

    def configurer(self, analyse_agent1: dict) -> dict:
        """
        Méthode principale : Configure Fibre ET Microsoft selon les besoins
        """
        print("\n" + "=" * 70)
        print(" Configuration des solutions Orange")
        print("=" * 70)

        resultats = {}

        # Configurer Fibre si demandé
        if analyse_agent1.get("besoins_fibre", {}).get("demande_fibre", False):
            print("\n Configuration Fibre...")
            resultats["fibre"] = self.configurer_fibre(analyse_agent1)
        else:
            resultats["fibre"] = {"message": "Pas de demande Fibre"}

        # Configurer Microsoft si demandé
        if analyse_agent1.get("besoins_microsoft", {}).get("demande_microsoft", False):
            print("\n  Configuration Microsoft...")
            resultats["microsoft"] = self.configurer_microsoft(analyse_agent1)
        else:
            resultats["microsoft"] = {"message": "Pas de demande Microsoft"}

        return resultats

    # ═══════════════════════════════════════════════════════════════
    # Méthodes utilitaires (Microsoft)
    # ═══════════════════════════════════════════════════════════════

    def _filtrer_catalogue(self, besoins_ms: dict) -> str:
        """Filtre le catalogue Microsoft par pertinence"""
        df = self.catalogue_microsoft[
            self.catalogue_microsoft['famille'] == 'Microsoft 365'
        ].copy()

        if len(df) < 5:
            df = self.catalogue_microsoft.copy()

        mots_cles = []
        services = besoins_ms.get("services_mentionnes", [])
        if isinstance(services, list):
            mots_cles.extend([s.lower() for s in services])
        type_besoin = besoins_ms.get("type_besoin", "")
        if type_besoin:
            mots_cles.extend(type_besoin.lower().split())

        if mots_cles:
            df["_score"] = df["nom_service"].apply(
                lambda nom: sum(1 for mc in mots_cles if mc in str(nom).lower())
            )
            df = df.sort_values(["_score", "prix_vente_tnd"], ascending=[False, True])
        else:
            df = df.sort_values("prix_vente_tnd")

        df = df.head(30)

        return df[
            ['nom_service', 'product_id', 'prix_vente_tnd', 'cout_revient_tnd']
        ].to_string(index=False)

    def _construire_description(self, analyste: dict) -> str:
        """Construit une description client enrichie"""
        lignes = [
            f"Entreprise    : {analyste.get('nom_entreprise', 'Non spécifié')}",
            f"Secteur       : {analyste.get('secteur', 'Non spécifié')}",
            f"Taille        : {analyste.get('taille_entreprise', 'Non spécifié')}",
            f"Nombre sites  : {analyste.get('nombre_sites', 'Non spécifié')}",
            f"Contraintes   : {', '.join(analyste.get('contraintes', [])) or 'Aucune'}",
            f"Urgence       : {analyste.get('urgence', 'moyen')}",
        ]
        return "\n".join(lignes)

    def _parser_json(self, texte: str) -> dict:
        """Extrait le JSON depuis la réponse du LLM"""
        texte = texte.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", texte)
        if match:
            texte = match.group(1).strip()
        else:
            match = re.search(r"(\{[\s\S]*\})", texte)
            if match:
                texte = match.group(1).strip()
        return json.loads(texte)

    def _valider_configurations(self, data: dict) -> None:
        """Valide que les 3 configurations Microsoft sont correctes"""
        niveaux = ["configuration_economique", "configuration_standard", "configuration_premium"]
        champs  = ["nom_produit", "product_id", "prix_unitaire_tnd",
                    "nombre_licences", "prix_total_annuel", "justification",
                    "fonctionnalites_principales"]

        for niveau in niveaux:
            if niveau not in data:
                raise ValueError(f"Niveau manquant : '{niveau}'")
            manquants = [c for c in champs if c not in data[niveau]]
            if manquants:
                raise ValueError(f"Champs manquants dans '{niveau}' : {manquants}")

        produits = [data[n]["nom_produit"] for n in niveaux]
        if len(set(produits)) < 3:
            raise ValueError(
                f"Les 3 configurations doivent avoir des produits différents. "
                f"Produits reçus : {produits}"
            )

        if "recommandation" not in data:
            raise ValueError("Clé 'recommandation' absente du JSON")

    def _verifier_prix(self, data: dict, nombre_licences: int) -> None:
        """Vérifie et corrige les calculs de prix Microsoft"""
        niveaux = ["configuration_economique", "configuration_standard", "configuration_premium"]
        for niveau in niveaux:
            config     = data[niveau]
            pu         = float(config.get("prix_unitaire_tnd", 0))
            nl         = int(config.get("nombre_licences", nombre_licences))
            pt_attendu = round(pu * nl, 2)
            pt_fourni  = float(config.get("prix_total_annuel", 0))

            if abs(pt_attendu - pt_fourni) > 1:
                print(
                    f"    Correction prix '{niveau}': "
                    f"{pu} × {nl} = {pt_attendu} TND (fourni: {pt_fourni} TND)"
                )
            config["prix_total_annuel"] = pt_attendu
            config["nombre_licences"]    = nl


class NumpyEncoder(json.JSONEncoder):
    """Convertit les types numpy en types Python natifs pour la sérialisation JSON."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# ============================================
# TESTS
# ============================================
if __name__ == "__main__":

    print(" Tests de l'Agent 2 - Configurateur Fibre + Microsoft")
    print("=" * 70)

    agent_config = AgentConfigurateur()

    print(f"\n Catalogue Microsoft : {len(agent_config.catalogue_microsoft)} produits")
    print(f" Catalogue Fibre : {len(agent_config.catalogue_fibre)} offres")

    # Test 1 : Client avec Fibre + Microsoft
    print("\n\n" + "=" * 70)
    print(" TEST 1 : Startup (Fibre 200 Mbps + Microsoft 25 users)")
    print("=" * 70)
    
    analyse_test1 = {
        "nom_entreprise": "DevSoft",
        "secteur": "Tech",
        "taille_entreprise": "PME",
        "nombre_sites": 1,
        "urgence": "moyen",
        "contraintes": [],
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 200,
            "nombre_sites": 1,
            "distance_metres": 150,
            "zone": "urbain"
        },
        "besoins_microsoft": {
            "demande_microsoft": True,
            "nombre_licences": 25,
            "type_besoin": "collaboration",
            "services_mentionnes": ["Teams", "Word", "Excel"]
        },
        "budget_mensuel": 2000
    }
    
    resultats1 = agent_config.configurer(analyse_test1)
    print("\n RÉSULTATS :")
    print(json.dumps(resultats1, indent=2, ensure_ascii=False, cls=NumpyEncoder))

    # Test 2 : Client Fibre uniquement
    print("\n\n" + "=" * 70)
    print(" TEST 2 : Restaurant (Fibre 100 Mbps uniquement)")
    print("=" * 70)
    
    analyse_test2 = {
        "nom_entreprise": "La Belle Vue",
        "secteur": "Restauration",
        "taille_entreprise": "TPE",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 100,
            "nombre_sites": 1,
            "distance_metres": 80
        },
        "besoins_microsoft": {
            "demande_microsoft": False
        },
        "budget_mensuel": 150
    }
    
    resultats2 = agent_config.configurer(analyse_test2)
    print("\n RÉSULTATS :")
    print(json.dumps(resultats2, indent=2, ensure_ascii=False, cls=NumpyEncoder))

    print("\n\n" + "=" * 70)
    print(" Tests terminés !")