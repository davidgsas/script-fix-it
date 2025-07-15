#!/usr/bin/env python3
import sys
print("TESTE: Python iniciando...", flush=True)
sys.stdout.flush()

try:
    print("TESTE: Importando config...", flush=True)
    from config import carregar_config, setup_logging
    print("TESTE: Config importado com sucesso!", flush=True)
    
    print("TESTE: Configurando logging...", flush=True)
    setup_logging()
    print("TESTE: Logging configurado!", flush=True)
    
    print("TESTE: Carregando configurações...", flush=True)
    config = carregar_config()
    print(f"TESTE: Config carregado com {len(config)} chaves", flush=True)
    
    print("TESTE: Verificando se precisa de input...", flush=True)
    if not config.get("insta_user") or not config.get("gnews_api_key"):
        print("TESTE: Configurações faltando - vai pedir input", flush=True)
    else:
        print("TESTE: Configurações completas", flush=True)
        
    print("TESTE: Sucesso completo!", flush=True)
    
except Exception as e:
    print(f"TESTE: ERRO - {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)