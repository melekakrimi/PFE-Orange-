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
        # 1. Création du modèle IA
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0  # Température 0 pour un JSON parfait
        )
        
        # 2. Chargement du Prompt depuis le fichier séparé
        self.prompt = PromptTemplate(
            input_variables=["description_client"],
            template=TEMPLATE_ANALYSTE
        )
        
        # 3. Connexion du Prompt à l'IA
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

        # Cas 1 : LLM entoure avec ```json ... ``` ou ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", texte)
        if match:
            return match.group(1).strip()

        # Cas 2 : JSON brut sans backticks
        match = re.search(r"(\{[\s\S]*\})", texte)
        if match:
            return match.group(1).strip()

        # Cas 3 : Retourner tel quel (laisse json.loads gérer l'erreur)
        return texte
    
    def _valider_analyse(self, analyse: dict) -> bool:
        """Vérifie que l'analyse contient les champs essentiels"""
        champs_requis = ["besoins_fibre", "besoins_microsoft", "urgence"]
        
        for champ in champs_requis:
            if champ not in analyse:
                print(f"    Champ manquant : {champ}")
                return False
        
        # Vérifier la structure de besoins_fibre
        if "demande_fibre" not in analyse["besoins_fibre"]:
            print("    besoins_fibre.demande_fibre manquant")
            return False
        
        # Vérifier la structure de besoins_microsoft
        if "demande_microsoft" not in analyse["besoins_microsoft"]:
            print("    besoins_microsoft.demande_microsoft manquant")
            return False

        #  FIX 1 : Vérification du nouveau champ taille_entreprise
        if "taille_entreprise" not in analyse:
            print("    Champ manquant : taille_entreprise")
            return False
        
        return True


# ============================================
# TESTS

if __name__ == "__main__":
    
    print(" Tests de l'Agent 1 - Analyste Fibre & Microsoft")
    print("=" * 70)
    
    agent = AgentAnalyste()
    
    # Test 1 : Fibre + Microsoft
    print("\n TEST 1 : Startup (Fibre + Microsoft)")
    print("-" * 70)
    description1 = """
    Bonjour, c'est l'entreprise DevSoft. On déménage.
    Il nous faut la fibre avec 500 mega minimum.
    Le boîtier Orange est à 120 mètres de nos locaux.
    Aussi, on a recruté, il nous faut    pour l'équipe avec Word et Teams.
    C'est urgent. Budget total : 500/TND mois max.
    """
    analyse1 = agent.analyser(description1)
    print(json.dumps(analyse1, indent=2, ensure_ascii=False))
    
    # Test 2 : Juste Fibre
    print("\n\n TEST 2 : Restaurant (Fibre uniquement)")
    print("-" * 70)
    description2 = """
    Restaurant La Belle Vue, on veut juste internet rapide
    pour les caisses et le WiFi clients. 100 Mega suffit.
    Distance du boîtier Orange : environ 80 mètres.
    Budget : 400 TND/mois max.
    """
    analyse2 = agent.analyser(description2)
    print(json.dumps(analyse2, indent=2, ensure_ascii=False))
    
    # Test 3 : Juste Microsoft
    print("\n\n TEST 3 : Cabinet comptable (Microsoft uniquement)")
    print("-" * 70)
    description3 = """
    Cabinet d'expertise comptable National Pen.
    On a déjà internet, mais on veut passer sur Power BI
    pour nos 12 comptables. Il nous faut Excel, Word, et le cloud
    pour partager les dossiers. Budget : 500 TND/mois.
    """
    analyse3 = agent.analyser(description3)
    print(json.dumps(analyse3, indent=2, ensure_ascii=False))
    
    # Test 4 : Cas complexe multi-sites
    print("\n\n TEST 4 : PME multi-sites (Cas complexe)")
    print("-" * 70)
    description4 = """
    Entreprise LogiTrans, secteur transport
    (Tunis). On veut la fibre
    Débit minimum 500 Mbps. Distance estimée : 200m pour Tunis,
    150m pour Sfax, 180m pour Sousse.
    
    Aussi, 80 employés ont besoin de Microsoft 365 avec Teams
    pour les réunions à distance entre sites.
    
    Budget global : 5000 TND/mois. C'est assez urgent.
    """
    analyse4 = agent.analyser(description4)
    print(json.dumps(analyse4, indent=2, ensure_ascii=False))
    
    print("\n\n" + "=" * 70)
    print(" Tous les tests terminés !")