# -*- coding: utf-8 -*-
import json
import os
import logging

# Constantes
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bot_database.db")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SESSION_FILE = os.path.join(BASE_DIR, "session.json")

# Preços da API
PRECO_INPUT_USD_1M_TOKENS = 0.10
PRECO_OUTPUT_USD_1M_TOKENS = 0.40

# Configuração padrão
DEFAULT_CONFIG = {
    "apis_ativas": ["gnews"],
    "categorias_ativas": ["technology"],
    "opacidade": 0.3,
    "intervalo_busca": 15,
    "intervalo_post": 30,
    "idiomas_busca": ["pt"],
    "insta_user": "",
    "insta_pass": "",
    "gnews_api_key": "",
    "newsdata_api_key": "",
    "google_api_key": ""
}

def carregar_config():
    """Carrega configurações do arquivo JSON"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def salvar_config(data):
    """Salva configurações no arquivo JSON"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logging.info("[SISTEMA] Configurações salvas em config.json")

def setup_logging():
    """Configura o sistema de logging"""
    log_file_handler = logging.FileHandler('bot.log', mode='w', encoding='utf-8')
    log_stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[log_file_handler, log_stream_handler]
    )
    
    # Silencia logs do Flask
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)