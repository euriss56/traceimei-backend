"""
Connexion à Supabase — utilisée par toutes les routes
"""

import os
from supabase import create_client, Client

def get_supabase() -> Client:
    url  = os.getenv("SUPABASE_URL")
    key  = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL et SUPABASE_KEY doivent être définis dans .env")

    return create_client(url, key)
