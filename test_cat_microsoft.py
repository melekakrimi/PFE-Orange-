# test_catalogue.py
import pandas as pd

print(" Test de chargement du catalogue Microsoft")
print("=" * 60)

try:
    # Charger le catalogue
    df = pd.read_csv("data/catalogue_microsoft.csv")
    print(f" Catalogue chargé : {len(df)} produits")
    
    # Afficher les 5 premiers
    print("\n Aperçu des 5 premiers produits :\n")
    print(df.head()[['id', 'famille', 'nom_service', 'prix_mensuel_tnd']])
    
    # Statistiques
    print(f"\n Statistiques :")
    print(f"   - Nombre de familles : {df['famille'].nunique()}")
    print(f"   - Prix moyen : {df['prix_mensuel_tnd'].mean():.2f} TND/mois")
    print(f"   - Prix min : {df['prix_mensuel_tnd'].min():.2f} TND/mois")
    print(f"   - Prix max : {df['prix_mensuel_tnd'].max():.2f} TND/mois")
    
    # Répartition par famille
    print(f"\n Répartition par famille :")
    print(df['famille'].value_counts())
    
    print("\n Le catalogue fonctionne parfaitement !")
    
except FileNotFoundError:
    print(" Erreur : Le fichier n'est pas trouvé")
except Exception as e:
    print(f" Erreur : {e}")