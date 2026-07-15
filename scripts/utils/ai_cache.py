import os
import json

# Define onde os arquivos de cache serão salvos
CACHE_DIR = "cache"

def _get_path(category, name):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    # Sanitiza o nome para evitar problemas com nomes de arquivos no Windows/Linux
    safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).rstrip()
    return os.path.join(CACHE_DIR, f"{category}_{safe_name}.json")

def load_cache(category, name):
    path = _get_path(category, name)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_cache(category, name, data):
    path = _get_path(category, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)