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

    FIBRE (catalogue réel Orange Business) :
    ─────────────────────────────────────────
    Coûts fixes (one-time, par site) :
        • Travaux FO    : distance_metres × 50 TND/mètre (VARIABLE selon distance)
        • Routeur       : 300 TND
        • Installation  : 200 TND

    Coût variable mensuel (par site) :
        • Bande passante : debit_mbps × 1.2 TND/mois (FIXE)

    Prix de vente mensuel (tarif catalogue Orange) :
        • debit_mbps × 10 TND/mois

    STRATÉGIE MARGE :
    ─────────────────
    1. Priorité engagement 24 mois (marge optimale ~63%)
    2. Si marge 24M négative → essayer 12 mois
    3. Si les deux négatifs → limiter distance ou refuser offre
    """

    # ── Tarifs Fibre Orange Business (source : catalogue réel) ──
    FIBRE_COUT_PAR_METRE     = 50    # TND/mètre
    FIBRE_COUT_ROUTEUR       = 300   # TND
    FIBRE_COUT_INSTALLATION  = 200   # TND
    FIBRE_COUT_PAR_MBPS      = 1.2   # TND/Mbps/mois
    FIBRE_PRIX_VENTE_PAR_MBPS = 10.0 # TND/Mbps/mois

    # Paliers de débit disponibles (Mbps)
    FIBRE_PALIERS_DEBIT = [50, 100, 200, 500, 1000]

    MAX_RETRIES = 3

    def __init__(self):
        # Charger le catalogue Microsoft
        self.catalogue_microsoft_brut = pd.read_csv("data/orange_propre/catalogue_propre.csv")
        self.catalogue_microsoft = self._preparer_catalogue_microsoft(self.catalogue_microsoft_brut)
        print(f" Catalogue Microsoft chargé ({len(self.catalogue_microsoft)} produits)")
        print(" Catalogue Fibre : modèle de calcul Orange Business (distance variable)")

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

    def _palier_debit(self, debit_min: float) -> int:
        """Retourne le palier de débit disponible >= debit_min."""
        for p in self.FIBRE_PALIERS_DEBIT:
            if p >= debit_min:
                return p
        return self.FIBRE_PALIERS_DEBIT[-1]

    def _calculer_distance_max(self, debit_mbps: int, engagement_mois: int) -> int:
        """
        Calcule la distance maximale pour avoir une marge positive.
        
        Formule :
        Revenu total = prix_vente × engagement_mois
        Coût mensuel total = (debit × 1.2) × engagement_mois
        Coût fixe max = Revenu - Coût mensuel
        Distance max = (Coût fixe max - Routeur - Installation) ÷ 50
        """
        prix_vente_mensuel = debit_mbps * self.FIBRE_PRIX_VENTE_PAR_MBPS
        cout_mensuel = debit_mbps * self.FIBRE_COUT_PAR_MBPS
        
        revenu_total = prix_vente_mensuel * engagement_mois
        cout_mensuel_total = cout_mensuel * engagement_mois
        
        cout_fixe_max = revenu_total - cout_mensuel_total
        cout_travaux_fo_max = cout_fixe_max - self.FIBRE_COUT_ROUTEUR - self.FIBRE_COUT_INSTALLATION
        
        if cout_travaux_fo_max <= 0:
            return 0
        
        distance_max = int(cout_travaux_fo_max / self.FIBRE_COUT_PAR_METRE)
        return max(0, distance_max)

    def _calculer_fibre(self, debit_mbps: int, distance_metres: int,
                        nombre_sites: int, engagement_mois: int) -> dict:
        """
        Calcule les coûts et revenus pour une configuration Fibre.
        
        Coûts fixes (one-time, par site) :
            - Travaux FO    : distance × 50 TND/m (VARIABLE)
            - Routeur       : 300 TND
            - Installation  : 200 TND

        Coût variable mensuel (par site) :
            - Bande passante : debit × 1.2 TND/mois (FIXE)

        Prix de vente mensuel (tarif catalogue) :
            - debit × 10 TND/mois
        """
        # Par site
        cout_fo          = distance_metres * self.FIBRE_COUT_PAR_METRE
        cout_initial_site = cout_fo + self.FIBRE_COUT_ROUTEUR + self.FIBRE_COUT_INSTALLATION
        cout_mensuel_site = round(debit_mbps * self.FIBRE_COUT_PAR_MBPS, 2)
        prix_vente_site   = round(debit_mbps * self.FIBRE_PRIX_VENTE_PAR_MBPS, 2)

        # Total (tous sites)
        cout_initial_total = round(cout_initial_site * nombre_sites, 2)
        cout_mensuel_total = round(cout_mensuel_site * nombre_sites, 2)
        prix_vente_total   = round(prix_vente_site * nombre_sites, 2)

        # Sur la durée d'engagement
        cout_total_engagement   = round(cout_initial_total + cout_mensuel_total * engagement_mois, 2)
        revenu_total_engagement = round(prix_vente_total * engagement_mois, 2)
        marge_tnd = round(revenu_total_engagement - cout_total_engagement, 2)
        marge_pct = round(marge_tnd / revenu_total_engagement * 100, 1) if revenu_total_engagement > 0 else 0

        return {
            "debit_mbps":            debit_mbps,
            "nombre_sites":          nombre_sites,
            "engagement_mois":       engagement_mois,
            "distance_metres":       distance_metres,
            # Coûts détaillés
            "cout_travaux_fo":       round(cout_fo * nombre_sites, 2),
            "cout_routeur":          round(self.FIBRE_COUT_ROUTEUR * nombre_sites, 2),
            "cout_installation":     round(self.FIBRE_COUT_INSTALLATION * nombre_sites, 2),
            "cout_initial_total":    cout_initial_total,
            "cout_mensuel_total":    cout_mensuel_total,
            # Prix de vente
            "prix_mensuel_total":    prix_vente_total,
            # Rentabilité
            "marge_pct":             marge_pct,
            "marge_tnd":             marge_tnd,
            "marge_positive":        marge_tnd > 0,
        }

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

        # Calcul des prix annuels (marge 14%)
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
    # CONFIGURATION FIBRE (avec gestion intelligente des marges)
    # ═══════════════════════════════════════════════════════════════

    def configurer_fibre(self, analyse_agent1: dict) -> dict:
        """
        Configure 3 offres Fibre (Économique, Standard, Premium)
        avec gestion intelligente des marges.
        
        STRATÉGIE :
        1. Priorité engagement 24 mois (meilleure marge)
        2. Si marge 24M négative → essayer 12 mois
        3. Si les deux négatifs → limiter distance ou alerter
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

        # Sélectionner 3 débits distincts
        debit_eco = self._palier_debit(debit_souhaite)
        debit_std = self._palier_debit(debit_souhaite * 1.5)
        debit_pre = self._palier_debit(debit_souhaite * 2)

        # Forcer des paliers distincts
        if debit_std == debit_eco:
            idx = self.FIBRE_PALIERS_DEBIT.index(debit_eco)
            debit_std = self.FIBRE_PALIERS_DEBIT[min(idx + 1, len(self.FIBRE_PALIERS_DEBIT) - 1)]
        if debit_pre <= debit_std:
            idx = self.FIBRE_PALIERS_DEBIT.index(debit_std)
            debit_pre = self.FIBRE_PALIERS_DEBIT[min(idx + 1, len(self.FIBRE_PALIERS_DEBIT) - 1)]

        configurations = []
        alertes = []

        for niveau, debit in [
            ("economique", debit_eco),
            ("standard", debit_std),
            ("premium", debit_pre)
        ]:
            # STRATÉGIE : Essayer d'abord 24 mois (meilleure marge)
            calc_24m = self._calculer_fibre(debit, distance_metres, nombre_sites, 24)
            
            if calc_24m["marge_positive"]:
                #  Marge 24M positive → on garde 24 mois
                calc = calc_24m
                engagement_choisi = 24
                raison_engagement = "Engagement 24 mois pour marge optimale"
            else:
                #  Marge 24M négative → essayer 12 mois
                calc_12m = self._calculer_fibre(debit, distance_metres, nombre_sites, 12)
                
                if calc_12m["marge_positive"]:
                    #  Marge 12M positive → on prend 12 mois
                    calc = calc_12m
                    engagement_choisi = 12
                    raison_engagement = "Engagement 12 mois (24M non rentable)"
                    alertes.append({
                        "niveau": niveau,
                        "message": f" {niveau.capitalize()} : Marge négative sur 24M, basculé sur 12M"
                    })
                else:
                    #  Les deux négatifs → calculer distance max
                    distance_max_24m = self._calculer_distance_max(debit, 24)
                    distance_max_12m = self._calculer_distance_max(debit, 12)
                    
                    # Prendre la meilleure option (24M si possible)
                    if distance_max_24m >= distance_max_12m:
                        distance_limite = distance_max_24m
                        engagement_choisi = 24
                    else:
                        distance_limite = distance_max_12m
                        engagement_choisi = 12
                    
                    # Recalculer avec distance limitée
                    calc = self._calculer_fibre(debit, distance_limite, nombre_sites, engagement_choisi)
                    raison_engagement = f"Distance limitée à {distance_limite}m pour marge positive"
                    
                    alertes.append({
                        "niveau": niveau,
                        "message": f" {niveau.capitalize()} : Distance {distance_metres}m trop élevée. "
                                    f"Distance max rentable : {distance_limite}m ({engagement_choisi} mois).",
                        "distance_demandee": distance_metres,
                        "distance_max": distance_limite,
                        "distance_reduite": True
                    })
            
            configurations.append({
                "niveau": niveau,
                "nom_offre": f"Fibre Orange Business {debit}M",
                "debit_mbps": calc["debit_mbps"],
                "nombre_sites": calc["nombre_sites"],
                "engagement_mois": calc["engagement_mois"],
                "distance_metres": calc["distance_metres"],
                
                # Coûts
                "cout_travaux_fo": calc["cout_travaux_fo"],
                "cout_routeur": calc["cout_routeur"],
                "cout_installation": calc["cout_installation"],
                "cout_initial_total": calc["cout_initial_total"],
                "cout_mensuel_total": calc["cout_mensuel_total"],
                
                # Prix
                "prix_mensuel_total": calc["prix_mensuel_total"],
                
                # Rentabilité
                "marge_pct": calc["marge_pct"],
                "marge_tnd": calc["marge_tnd"],
                "marge_positive": calc["marge_positive"],
                
                # Explications
                "raison_engagement": raison_engagement,
                "justification": self._generer_justification_fibre(niveau, debit, debit_souhaite, calc)
            })

        # Recommandation selon budget vs prix réels des configurations
        budget = analyse_agent1.get("budget_mensuel", 0) or 0
        if configurations and budget > 0:
            prix_std = configurations[1]["prix_mensuel_total"]
            prix_pre = configurations[2]["prix_mensuel_total"]
            if budget >= prix_pre:
                recommandation = "premium"
            elif budget >= prix_std:
                recommandation = "standard"
            else:
                recommandation = "economique"
        else:
            recommandation = "standard"

        resultat = {
            "configurations": configurations,
            "recommandation": recommandation,
        }
        
        # Ajouter les alertes si présentes
        if alertes:
            resultat["alertes"] = alertes
            resultat["note"] = " Certaines configurations ont nécessité des ajustements (distance ou engagement)"
        
        return resultat

    def _generer_justification_fibre(self, niveau: str, debit_offert: int, debit_demande: int, calc: dict) -> str:
        """Génère une justification pour une offre Fibre"""
        base_justifications = {
            "economique": f"Offre la plus économique répondant au besoin de {debit_demande} Mbps. "
                            f"Débit de {debit_offert} Mbps avec engagement {calc['engagement_mois']} mois.",
            
            "standard": f"Bon équilibre entre performance et prix. "
                        f"Débit de {debit_offert} Mbps pour anticiper la croissance. "
                        f"Engagement {calc['engagement_mois']} mois.",
            
            "premium": f"Solution haut de gamme avec {debit_offert} Mbps. "
                        f"Performance maximale et fiabilité garantie. "
                        f"Engagement {calc['engagement_mois']} mois."
        }
        
        justif = base_justifications.get(niveau, "Configuration adaptée aux besoins")
        
        # Ajouter info marge
        if calc["marge_pct"] >= 50:
            justif += f" Excellent retour ({calc['marge_pct']}% de marge)."
        elif calc["marge_pct"] >= 30:
            justif += f" Bon retour ({calc['marge_pct']}% de marge)."
        elif calc["marge_pct"] > 0:
            justif += f" Marge réduite ({calc['marge_pct']}%)."
        
        return justif

    # ═══════════════════════════════════════════════════════════════
    # CONFIGURATION MICROSOFT
    # ═══════════════════════════════════════════════════════════════

    def configurer_microsoft(self, analyste_agent1: dict) -> dict:
        """Configure 3 offres Microsoft (Économique, Standard, Premium)"""
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
        """Méthode principale : Configure Fibre ET Microsoft selon les besoins"""
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

    # Test 1 : Distance normale (rentable)
    print("\n\n" + "=" * 70)
    print(" TEST 1 : Distance normale (50m - Rentable)")
    print("=" * 70)
    
    analyse_test1 = {
        "nom_entreprise": "DevSoft",
        "secteur": "Tech",
        "taille_entreprise": "PME",
        "urgence": "moyenne",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 100,
            "nombre_sites": 1,
            "distance_metres": 50
        },
        "besoins_microsoft": {"demande_microsoft": False},
        "budget_mensuel": 1000
    }
    
    resultats1 = agent_config.configurer(analyse_test1)
    print("\n RÉSULTATS :")
    print(json.dumps(resultats1, indent=2, ensure_ascii=False, cls=NumpyEncoder))

    # Test 2 : Distance élevée (marge limite)
    print("\n\n" + "=" * 70)
    print(" TEST 2 : Distance élevée (200m - Marge réduite)")
    print("=" * 70)
    
    analyse_test2 = {
        "nom_entreprise": "RestoBay",
        "secteur": "Restauration",
        "taille_entreprise": "TPE",
        "urgence": "élevée",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 50,
            "nombre_sites": 1,
            "distance_metres": 200
        },
        "besoins_microsoft": {"demande_microsoft": False},
        "budget_mensuel": 500
    }
    
    resultats2 = agent_config.configurer(analyse_test2)
    print("\n RÉSULTATS :")
    print(json.dumps(resultats2, indent=2, ensure_ascii=False, cls=NumpyEncoder))

    # Test 3 : Distance très élevée (non rentable)
    print("\n\n" + "=" * 70)
    print(" TEST 3 : Distance très élevée (500m - Limite dépassée)")
    print("=" * 70)
    
    analyse_test3 = {
        "nom_entreprise": "Ferme Rurale",
        "secteur": "Agriculture",
        "taille_entreprise": "TPE",
        "urgence": "faible",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 50,
            "nombre_sites": 1,
            "distance_metres": 500
        },
        "besoins_microsoft": {"demande_microsoft": False},
        "budget_mensuel": 300
    }
    
    resultats3 = agent_config.configurer(analyse_test3)
    print("\n RÉSULTATS :")
    print(json.dumps(resultats3, indent=2, ensure_ascii=False, cls=NumpyEncoder))

    print("\n\n" + "=" * 70)
    print(" Tests terminés !")
    print("\nRésumé des stratégies appliquées :")
    print("- Test 1 (50m)  :  Marge positive → Engagement 24M")
    print("- Test 2 (200m) :  Marge réduite → Engagement ajusté")
    print("- Test 3 (500m) :  Distance limitée automatiquement")