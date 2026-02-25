from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# Charger le fichier .env
load_dotenv()

# Vérifier que la clé est bien chargée
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print(" ERREUR : Clé API non trouvée dans .env")
else:
    print(f" Clé API trouvée : {api_key[:10]}...")
    
    # Créer le modèle IA (AVEC LE NOUVEAU NOM DE MODÈLE)
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",  # <--- C'est ici que j'ai corrigé !
        api_key=api_key,
        temperature=0.3
    )
    
    # Test simple
    print("\n Test de connexion Groq...")
    try:
        response = llm.invoke("Dis bonjour en français")
        print(response.content)
        print("\n Groq fonctionne parfaitement ! Bravo !")
    except Exception as e:
        print(f"\n Erreur : {e}")