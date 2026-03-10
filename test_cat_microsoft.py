import pandas as pd

print(" Test de chargement du catalogue Microsoft")
print("=" * 60)

try:
    df = pd.read_csv("data/orange_propre/catalogue_propre.csv")
    print(f" Catalogue chargé : {len(df)} produits")

    # Aperçu des 5 premiers
    print("\n Aperçu des 5 premiers produits :\n")
    print(df.head()[['ProductTitle', 'ProductId', 'TermDuration', 'BillingPlan', 'UnitPrice(DT)']])

    # Statistiques
    print(f"\n Statistiques :")
    print(f"   - Produits uniques : {df['ProductTitle'].nunique()}")
    print(f"   - Prix moyen (annuel) : {df['UnitPrice(DT)'].mean():.2f} DT")
    print(f"   - Prix min  : {df['UnitPrice(DT)'].min():.2f} DT")
    print(f"   - Prix max  : {df['UnitPrice(DT)'].max():.2f} DT")

    # Répartition par plan de facturation
    print(f"\n Répartition BillingPlan :")
    print(df['BillingPlan'].value_counts())

    print("\n Le catalogue fonctionne parfaitement !")

except FileNotFoundError:
    print(" Erreur : Le fichier data/orange_propre/catalogue_propre.csv est introuvable")
except Exception as e:
    print(f" Erreur : {e}")