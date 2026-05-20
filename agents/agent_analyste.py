# agents/agent_analyste.py
import os
import sys
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# Astuce pour lier les dossiers : on va chercher le prompt dans le dossier 'prompts'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.prompt_analyste import TEMPLATE_ANALYSTE

# Charger les variables d'environnement (Clé API)
load_dotenv()

class AgentAnalyste:
    """
    Agent 1 : Analyse les besoins d'un client B2B (Fibre FTTO et Microsoft)
    """
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        self.prompt = PromptTemplate(
            input_variables=["description_client"],
            template=TEMPLATE_ANALYSTE
        )
        
        self.chain = self.prompt | self.llm
    
    def analyser(self, description_client: str) -> dict:
        """Analyse la description et retourne un dictionnaire propre"""
        try:
            # Appel à l'IA
            resultat = self.chain.invoke({"description_client": description_client})

            #  FIX 2 : Nettoyage robuste (même méthode que l'Agent 2)
            resultat_clean = self._parser_json(resultat.content)
            
            # Conversion en vrai dictionnaire Python
            analyse = json.loads(resultat_clean)
    
            # VALIDATION
            if self._valider_analyse(analyse):
                print(" Analyse validée")
            else:
                print("  Analyse incomplète")
            
            return analyse
            
        except json.JSONDecodeError as e:
            print(f" Erreur JSON : {e}")
            print(f"Résultat brut : {resultat.content}")
            return {"erreur": "JSON invalide", "brut": resultat.content}
        except Exception as e:
            print(f" Erreur : {e}")
            return {"erreur": str(e)}

    def _parser_json(self, texte: str) -> str:
        """
            FIX 2 : Extraction robuste du JSON depuis la réponse du LLM.
        Gère tous les formats : ```json ... ```, ``` ... ```, ou JSON brut.
        (Méthode identique à celle de l'Agent 2 pour cohérence)
        """
        texte = texte.strip()

        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", texte)
        if match:
            return match.group(1).strip()

        match = re.search(r"(\{[\s\S]*\})", texte)
        if match:
            return match.group(1).strip()

        return texte
    
    def _valider_analyse(self, analyse: dict) -> bool:
        """Vérifie que l'analyse contient les champs essentiels"""
        champs_requis = ["besoins_fibre", "besoins_microsoft", "urgence"]
        
        for champ in champs_requis:
            if champ not in analyse:
                print(f"    Champ manquant : {champ}")
                return False
        
        if "demande_fibre" not in analyse["besoins_fibre"]:
            print("    besoins_fibre.demande_fibre manquant")
            return False
        
        if "demande_microsoft" not in analyse["besoins_microsoft"]:
            print("    besoins_microsoft.demande_microsoft manquant")
            return False

        if "taille_entreprise" not in analyse:
            print("    Champ manquant : taille_entreprise")
            return False
        
        return True
    

# ============================================
# TESTS

if __name__ == "__main__":

    print(" Tests Agent 1 — Analyste")
    print("=" * 70)

    agent = AgentAnalyste()

    cas = [
        ("BIAT — Fibre + MS Premium", """
        BIAT, banque tunisienne, 50 employes au siege.
        On a besoin de la fibre 200 Mbps, le boitier Orange est a 80 metres.
        Et 50 licences Microsoft avec le mail, OneDrive, SharePoint, Pack Office,
        Intune pour les mobiles et Defender antivirus. Urgence haute.
        """),
        ("DevSoft — Fibre + MS Standard", """
        DevSoft, entreprise tech, PME, 25 developpeurs.
        On demenage dans de nouveaux bureaux. Besoin de la fibre 100 Mbps,
        boitier Orange a 50 metres. Et 25 licences Microsoft avec Teams,
        OneDrive, SharePoint et Pack Office. Urgence haute.
        """),
        ("LegalPro — MS Basic uniquement", """
        Cabinet LegalPro, 15 avocats. On a deja internet.
        On veut uniquement Microsoft 365 pour la messagerie professionnelle
        et OneDrive pour stocker les dossiers clients. Pas besoin de fibre.
        """),
        ("FastFood Express — Fibre uniquement", """
        FastFood Express, restaurant, petite entreprise.
        On veut juste internet rapide pour les caisses et le WiFi clients.
        50 Mega suffit. Le boitier Orange est a environ 80 metres.
        Pas besoin de Microsoft.
        """),
    ]

    for titre, desc in cas:
        print(f"\n {'='*60}")
        print(f"  {titre}")
        print(f" {'='*60}")
        resultat = agent.analyser(desc)
        print(json.dumps(resultat, indent=2, ensure_ascii=False))

    print("\n Tests Agent 1 termines !")