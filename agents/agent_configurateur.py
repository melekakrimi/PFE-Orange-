# agents/agent_configurateur.py
import pandas as pd
from langchain_groq import ChatGroq
import os

class AgentConfigurateur:
    """
    Agent 2 : Configure des solutions Microsoft selon les besoins
    """
    
    def __init__(self):
        # Charger le catalogue
        self.catalogue = pd.read_csv("data/catalogue_microsoft.csv")
        
        # IA
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3
        )
    
    def configurer(self, analyse_agent1):
        """
        Prend l'analyse de l'Agent 1 et propose des produits Microsoft
        """
        
        # Extraire les besoins Microsoft
        besoins_ms = analyse_agent1["besoins_microsoft"]
        
        if not besoins_ms["demande_microsoft"]:
            return {"message": "Client ne veut pas de Microsoft"}
        
        # Filtrer le catalogue selon le besoin
        # Exemple : Client veut Microsoft 365
        produits_microsoft_365 = self.catalogue[
            self.catalogue['famille'] == 'Microsoft 365'
        ]
        
        # Construire le prompt avec les produits disponibles
        prompt = f"""
        Tu es un expert Orange Business.
        
        CLIENT : 
        - Nombre d'utilisateurs : {besoins_ms['nombre_licences']}
        - Type de besoin : {besoins_ms['type_besoin']}
        - Services mentionnés : {besoins_ms['services_mentionnes']}
        
        PRODUITS MICROSOFT 365 DISPONIBLES CHEZ ORANGE :
        {produits_microsoft_365[['nom_service', 'prix_mensuel_tnd']].head(20).to_string()}
        
        MISSION :
        Propose 3 configurations :
        1. Économique (le moins cher qui répond au besoin)
        2. Standard (bon rapport qualité/prix)
        3. Premium (le plus complet)
        
        Pour chaque config, fournis :
        - Nom du produit
        - Prix unitaire TND/mois
        - Prix total (prix × nombre users)
        - Justification
        
        Réponds en JSON.
        """
        
        # Appel IA
        response = self.llm.invoke(prompt)
        
        return response.content
