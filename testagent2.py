# test_agent_configurateur.py
"""
Tests complets pour l'Agent 2 - Configurateur Fibre + Microsoft
Teste les 3 stratégies de gestion des marges Fibre
"""

import sys
import os
import json

# Ajouter le dossier parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_configurateur import AgentConfigurateur, NumpyEncoder


def test_distance_normale():
    """
    TEST 1 : Distance normale (50m)
    Résultat attendu : Marge positive, engagement 24 mois
    """
    print("\n" + "=" * 80)
    print("📋 TEST 1 : Distance normale (50m - Rentable)")
    print("=" * 80)
    
    agent = AgentConfigurateur()
    
    analyse = {
        "nom_entreprise": "DevSoft SARL",
        "secteur": "Tech",
        "taille_entreprise": "PME",
        "urgence": "moyenne",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 100,
            "nombre_sites": 1,
            "distance_metres": 50
        },
        "besoins_microsoft": {
            "demande_microsoft": False
        },
        "budget_mensuel": 1000
    }
    
    resultats = agent.configurer(analyse)
    
    print("\n📊 RÉSULTATS :")
    print(json.dumps(resultats, indent=2, ensure_ascii=False, cls=NumpyEncoder))
    
    # Vérifications
    print("\n✅ VÉRIFICATIONS :")
    config_eco = resultats["fibre"]["configurations"][0]
    
    assert config_eco["marge_positive"] == True, "❌ La marge devrait être positive"
    assert config_eco["engagement_mois"] == 24, "❌ L'engagement devrait être 24 mois"
    assert config_eco["distance_metres"] == 50, "❌ La distance ne devrait pas être limitée"
    
    print(f"✓ Marge positive : {config_eco['marge_pct']}%")
    print(f"✓ Engagement : {config_eco['engagement_mois']} mois")
    print(f"✓ Distance : {config_eco['distance_metres']}m (inchangée)")
    print(f"✓ Prix mensuel : {config_eco['prix_mensuel_total']} TND")
    
    return True


def test_distance_elevee():
    """
    TEST 2 : Distance élevée (200m)
    Résultat attendu : Marge 24M négative → Basculé sur 12M
    """
    print("\n" + "=" * 80)
    print("📋 TEST 2 : Distance élevée (200m - Marge réduite)")
    print("=" * 80)
    
    agent = AgentConfigurateur()
    
    analyse = {
        "nom_entreprise": "Restaurant La Belle Vue",
        "secteur": "Restauration",
        "taille_entreprise": "TPE",
        "urgence": "élevée",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 50,
            "nombre_sites": 1,
            "distance_metres": 200
        },
        "besoins_microsoft": {
            "demande_microsoft": False
        },
        "budget_mensuel": 500
    }
    
    resultats = agent.configurer(analyse)
    
    print("\n📊 RÉSULTATS :")
    print(json.dumps(resultats, indent=2, ensure_ascii=False, cls=NumpyEncoder))
    
    # Vérifications
    print("\n✅ VÉRIFICATIONS :")
    config_eco = resultats["fibre"]["configurations"][0]
    
    assert config_eco["marge_positive"] == True, "❌ La marge devrait être positive (même réduite)"
    assert config_eco["distance_metres"] == 200, "❌ La distance ne devrait pas être limitée"
    
    # Vérifier si engagement ajusté
    if config_eco["engagement_mois"] == 12:
        print(f"⚠️  Engagement ajusté à 12 mois (24M non rentable)")
    
    print(f"✓ Marge positive : {config_eco['marge_pct']}%")
    print(f"✓ Engagement : {config_eco['engagement_mois']} mois")
    print(f"✓ Distance : {config_eco['distance_metres']}m")
    print(f"✓ Prix mensuel : {config_eco['prix_mensuel_total']} TND")
    
    # Vérifier les alertes
    if "alertes" in resultats["fibre"]:
        print(f"\n⚠️  {len(resultats['fibre']['alertes'])} alerte(s) :")
        for alerte in resultats["fibre"]["alertes"]:
            print(f"   - {alerte['message']}")
    
    return True


def test_distance_excessive():
    """
    TEST 3 : Distance excessive (500m)
    Résultat attendu : Distance limitée automatiquement
    """
    print("\n" + "=" * 80)
    print("📋 TEST 3 : Distance excessive (500m - Limite dépassée)")
    print("=" * 80)
    
    agent = AgentConfigurateur()
    
    analyse = {
        "nom_entreprise": "Ferme Bio du Sud",
        "secteur": "Agriculture",
        "taille_entreprise": "TPE",
        "urgence": "faible",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 50,
            "nombre_sites": 1,
            "distance_metres": 500
        },
        "besoins_microsoft": {
            "demande_microsoft": False
        },
        "budget_mensuel": 300
    }
    
    resultats = agent.configurer(analyse)
    
    print("\n📊 RÉSULTATS :")
    print(json.dumps(resultats, indent=2, ensure_ascii=False, cls=NumpyEncoder))
    
    # Vérifications
    print("\n✅ VÉRIFICATIONS :")
    config_eco = resultats["fibre"]["configurations"][0]
    
    assert config_eco["marge_positive"] == True, "❌ La marge devrait être positive"
    assert config_eco["distance_metres"] < 500, "❌ La distance devrait avoir été limitée"
    
    print(f"✓ Marge positive : {config_eco['marge_pct']}%")
    print(f"✓ Engagement : {config_eco['engagement_mois']} mois")
    print(f"✓ Distance demandée : 500m")
    print(f"✓ Distance appliquée : {config_eco['distance_metres']}m (LIMITÉE)")
    print(f"✓ Prix mensuel : {config_eco['prix_mensuel_total']} TND")
    
    # Vérifier les alertes
    assert "alertes" in resultats["fibre"], "❌ Il devrait y avoir des alertes"
    
    print(f"\n🔴 {len(resultats['fibre']['alertes'])} alerte(s) critique(s) :")
    for alerte in resultats["fibre"]["alertes"]:
        print(f"   - {alerte['message']}")
        if "distance_reduite" in alerte and alerte["distance_reduite"]:
            print(f"     → Distance max rentable : {alerte['distance_max']}m")
    
    return True


def test_fibre_microsoft_combine():
    """
    TEST 4 : Fibre + Microsoft combinés
    Résultat attendu : Les deux configurations générées
    """
    print("\n" + "=" * 80)
    print("📋 TEST 4 : Fibre + Microsoft combinés")
    print("=" * 80)
    
    agent = AgentConfigurateur()
    
    analyse = {
        "nom_entreprise": "Cabinet Expertise Plus",
        "secteur": "Finance",
        "taille_entreprise": "PME",
        "urgence": "moyenne",
        "besoins_fibre": {
            "demande_fibre": True,
            "debit_souhaite_mbps": 100,
            "nombre_sites": 1,
            "distance_metres": 80
        },
        "besoins_microsoft": {
            "demande_microsoft": True,
            "nombre_licences": 15,
            "type_besoin": "bureautique",
            "services_mentionnes": ["Word", "Excel", "Outlook"]
        },
        "budget_mensuel": 1500
    }
    
    resultats = agent.configurer(analyse)
    
    print("\n📊 RÉSULTATS :")
    print(json.dumps(resultats, indent=2, ensure_ascii=False, cls=NumpyEncoder))
    
    # Vérifications
    print("\n✅ VÉRIFICATIONS :")
    
    # Vérifier Fibre
    assert "fibre" in resultats, "❌ Résultats Fibre manquants"
    assert "configurations" in resultats["fibre"], "❌ Configurations Fibre manquantes"
    print(f"✓ Fibre : {len(resultats['fibre']['configurations'])} configurations")
    
    # Vérifier Microsoft
    assert "microsoft" in resultats, "❌ Résultats Microsoft manquants"
    if "erreur" not in resultats["microsoft"]:
        assert "configuration_economique" in resultats["microsoft"], "❌ Config économique manquante"
        print(f"✓ Microsoft : 3 configurations générées")
    else:
        print(f"⚠️  Microsoft : {resultats['microsoft']['erreur']}")
    
    return True


def test_calcul_distance_max():
    """
    TEST 5 : Calcul distances maximales
    Affiche les limites pour différents débits
    """
    print("\n" + "=" * 80)
    print("📋 TEST 5 : Calcul distances maximales par débit")
    print("=" * 80)
    
    agent = AgentConfigurateur()
    
    print("\n📊 DISTANCES MAXIMALES RENTABLES :")
    print("-" * 80)
    print(f"{'Débit':<10} {'12 mois':<15} {'24 mois':<15} {'Différence':<15}")
    print("-" * 80)
    
    for debit in [50, 100, 200, 500, 1000]:
        dist_12m = agent._calculer_distance_max(debit, 12)
        dist_24m = agent._calculer_distance_max(debit, 24)
        diff = dist_24m - dist_12m
        
        print(f"{debit} Mbps {dist_12m:>6}m {dist_24m:>12}m {diff:>12}m (+{diff}m)")
    
    print("-" * 80)
    print("\n💡 OBSERVATIONS :")
    print("   • L'engagement 24 mois permet des distances plus élevées")
    print("   • Plus le débit est élevé, plus la distance max diminue")
    print("   • Raison : Coût mensuel bande passante = débit × 1.2 TND")
    
    return True


def executer_tous_les_tests():
    """
    Exécute tous les tests dans l'ordre
    """
    print("\n" + "=" * 80)
    print("🧪 SUITE DE TESTS - AGENT 2 CONFIGURATEUR")
    print("=" * 80)
    print("\nTests de la stratégie de gestion des marges Fibre :")
    print("1. Distance normale (50m)")
    print("2. Distance élevée (200m)")
    print("3. Distance excessive (500m)")
    print("4. Fibre + Microsoft combinés")
    print("5. Calcul distances maximales")
    
    tests = [
        ("Distance normale", test_distance_normale),
        ("Distance élevée", test_distance_elevee),
        ("Distance excessive", test_distance_excessive),
        ("Fibre + Microsoft", test_fibre_microsoft_combine),
        ("Calcul distances max", test_calcul_distance_max),
    ]
    
    resultats = []
    
    for nom, test_func in tests:
        try:
            succes = test_func()
            resultats.append((nom, "✅ RÉUSSI" if succes else "❌ ÉCHOUÉ"))
            print(f"\n✅ Test '{nom}' : RÉUSSI")
        except Exception as e:
            resultats.append((nom, f"❌ ERREUR : {str(e)}"))
            print(f"\n❌ Test '{nom}' : ERREUR")
            print(f"   Détails : {e}")
    
    # Résumé final
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    for nom, statut in resultats:
        print(f"{nom:<30} {statut}")
    
    nb_reussis = sum(1 for _, s in resultats if "✅" in s)
    nb_total = len(resultats)
    
    print("\n" + "=" * 80)
    print(f"🎯 RÉSULTAT GLOBAL : {nb_reussis}/{nb_total} tests réussis")
    print("=" * 80)
    
    if nb_reussis == nb_total:
        print("\n🎉 TOUS LES TESTS SONT RÉUSSIS ! 🎉")
        return True
    else:
        print(f"\n⚠️  {nb_total - nb_reussis} test(s) échoué(s)")
        return False


if __name__ == "__main__":
    # Exécuter tous les tests
    succes = executer_tous_les_tests()
    
    # Code de sortie
    exit(0 if succes else 1)