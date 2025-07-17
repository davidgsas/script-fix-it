import json
import os
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
DB_PATH = os.path.join(BASE_DIR, "bot_database.db")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SESSION_FILE = os.path.join(BASE_DIR, "session.json")

def get_agent_config_path(agent_id):
    return os.path.join(AGENTS_DIR, f"agent_{agent_id}.json")

def get_agent_session_path(agent_id):
    return os.path.join(AGENTS_DIR, f"session_{agent_id}.json")

def get_agent_db_path(agent_id):
    return os.path.join(AGENTS_DIR, f"database_{agent_id}.db")

PRECO_INPUT_USD_1M_TOKENS = 0.10
PRECO_OUTPUT_USD_1M_TOKENS = 0.40

DEFAULT_CONFIG = {
    "apis_ativas": ["gnews"],
    "categorias_ativas": ["technology"],
    "opacidade": 0.3,
    "intervalo_busca": 15,
    "intervalo_post": 30,
    "intervalo_post_min": 8,
    "intervalo_post_max": 10,
    "usar_intervalo_aleatorio": True,
    "idiomas_busca": ["pt"],
    "insta_user": "",
    "insta_pass": "",
    "gnews_api_key": "",
    "newsdata_api_key": "",
    "google_api_key": ""
}

def carregar_config(agent_id=None):
    if agent_id:
        config_path = get_agent_config_path(agent_id)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return get_default_agent_config()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def get_default_agent_config():
    return {
        "agent_name": "Novo Agente",
        "pasta_feed": "geral",
        "insta_user": "",
        "insta_pass": "",
        "apis_ativas": ["local_db"],
        "categorias_ativas": ["general"],
        "idiomas_busca": ["pt"],
        "intervalo_busca": 15,
        "intervalo_post": 30,
        "intervalo_post_min": 8,
        "intervalo_post_max": 10,
        "usar_intervalo_aleatorio": True,
        "opacidade": 0.3,
        "ativo": False
    }

def salvar_config(data, agent_id=None):
    if agent_id:
        os.makedirs(AGENTS_DIR, exist_ok=True)
        config_path = get_agent_config_path(agent_id)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logging.info("[SISTEMA] Configurações salvas")

def listar_agentes():
    if not os.path.exists(AGENTS_DIR):
        return []
    
    agentes = []
    for filename in os.listdir(AGENTS_DIR):
        if filename.startswith("agent_") and filename.endswith(".json"):
            agent_id = filename.replace("agent_", "").replace(".json", "")
            config = carregar_config(agent_id)
            agentes.append({
                "id": agent_id,
                "name": config.get("agent_name", f"Agente {agent_id}"),
                "pasta_feed": config.get("pasta_feed", "geral"),
                "insta_user": config.get("insta_user", ""),
                "ativo": config.get("ativo", False)
            })
    return agentes

def criar_novo_agente():
    import uuid
    agent_id = str(uuid.uuid4())[:8]
    config = get_default_agent_config()
    salvar_config(config, agent_id)
    return agent_id

def setup_logging():
    log_file_handler = logging.FileHandler('bot.log', mode='w', encoding='utf-8')
    log_stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[log_file_handler, log_stream_handler]
    )
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)