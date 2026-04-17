import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import _get_connexion

conn = _get_connexion()
print("Connexion reussie !")
conn.close()