import pandas as pd

print("⏳ Début du nettoyage des données...")

# ⚠️ N'oublie pas de mettre le nom exact de ton gros fichier CSV ici !
chemin_gros_fichier = "data/orange_reel/Feb_Licenses.csv"

try:
    df = pd.read_csv(chemin_gros_fichier)
    total_lignes_avant = len(df)
    print(f"📊 Fichier chargé : {total_lignes_avant} lignes trouvées.")

    # 1. FILTRE DES LIGNES : On garde P1Y ET le paiement Annuel
    df_propre = df[(df['TermDuration'] == 'P1Y') & (df['BillingPlan'] == 'Annual')]
    
    # 2. SUPPRESSION DES COLONNES : On enlève unitPrice et currency
    # Attention aux majuscules/minuscules ! Si dans ton fichier c'est écrit "UnitPrice", modifie-le ici.
    colonnes_a_supprimer = ['UnitPrice(DT)', 'Currency']
    df_propre = df_propre.drop(columns=colonnes_a_supprimer)
    
    # 3. SAUVEGARDE du nouveau fichier tout beau, tout propre
    chemin_nouveau_fichier = "data/orange_propre/catalogue_propre.csv"
    df_propre.to_csv(chemin_nouveau_fichier, index=False)
    
    total_lignes_apres = len(df_propre)
    print(f"✅ Nettoyage terminé avec succès !")
    print(f"📉 Lignes réduites : de {total_lignes_avant} à {total_lignes_apres}")
    print(f"🧹 Colonnes {colonnes_a_supprimer} supprimées !")
    print(f"📁 Fichier final prêt pour l'IA : {chemin_nouveau_fichier}")

except FileNotFoundError:
    print(f"❌ Erreur : Je ne trouve pas le fichier {chemin_gros_fichier}.")
except KeyError as e:
    print(f"❌ Erreur de colonne : La colonne {e} n'existe pas. Vérifie les majuscules (ex: 'UnitPrice' au lieu de 'unitPrice') !")