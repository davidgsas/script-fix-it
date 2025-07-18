#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sistema Multi-Agente para Instagram
Permite executar múltiplos bots simultaneamente com diferentes contas e configurações
"""

import os
import getpass
import logging
import json
import google.generativeai as genai
from flask import Flask, render_template, redirect, url_for, request, jsonify

print("🚀 INICIANDO SISTEMA MULTI-AGENTE...")

# Importa os módulos
try:
    from config import setup_logging, carregar_config, salvar_config, listar_agentes, criar_novo_agente
    from agent_manager import agent_manager
    from ai_services import custo_sessao_atual
    print("✅ Todos os módulos importados com sucesso!")
except Exception as e:
    print(f"❌ Erro ao importar módulos: {e}")
    exit(1)

# Configuração Flask
app = Flask(__name__)

# === ROTAS WEB ===

@app.route("/")
def index():
    """Página principal com lista de agentes"""
    agentes = listar_agentes()
    status_agentes = agent_manager.get_status_agentes()
    
    # Combina informações dos agentes
    for agente in agentes:
        if agente['id'] in status_agentes:
            agente.update(status_agentes[agente['id']])
    
    return render_template("multiagent_index.html", agentes=agentes)

@app.route("/agente/<agent_id>")
def visualizar_agente(agent_id):
    """Página de visualização/controle de um agente específico"""
    from database import Database
    config = carregar_config(agent_id)
    
    if not config:
        return redirect(url_for('index'))
    
    # Pega dados do agente
    fila = Database.pegar_fila_completa_agente(agent_id) if agent_id in agent_manager.agents else []
    historico = Database.pegar_historico_agente(agent_id) if agent_id in agent_manager.agents else []
    
    return render_template("agente_dashboard.html", 
                         agent_id=agent_id, 
                         config=config, 
                         fila=fila, 
                         historico=historico[:50])  # Últimos 50

@app.route("/criar_agente", methods=['POST'])
def criar_agente():
    """Cria um novo agente"""
    agent_id = criar_novo_agente()
    return redirect(url_for('configurar_agente', agent_id=agent_id))

@app.route("/configurar/<agent_id>")
def configurar_agente(agent_id):
    """Página de configuração de um agente"""
    from news_apis import NewsAPIs
    config = carregar_config(agent_id)
    pastas_disponiveis = NewsAPIs.obter_pastas_disponiveis()
    return render_template("configurar_agente.html", 
                          agent_id=agent_id, 
                          config=config, 
                          pastas_disponiveis=pastas_disponiveis)

@app.route("/salvar_config/<agent_id>", methods=['POST'])
def salvar_config_agente(agent_id):
    """Salva configuração de um agente"""
    config = carregar_config(agent_id)
    
    # Atualiza configurações básicas
    config['agent_name'] = request.form.get('agent_name', f'Agente {agent_id}')
    config['pasta_feed'] = request.form.get('pasta_feed', 'geral')
    config['insta_user'] = request.form.get('insta_user', '')
    config['insta_pass'] = request.form.get('insta_pass', '')
    
    # Atualiza APIs e configurações
    config['apis_ativas'] = request.form.getlist('apis')
    config['categorias_ativas'] = request.form.getlist('categorias')
    config['idiomas_busca'] = request.form.getlist('idiomas')
    config['intervalo_busca'] = int(request.form.get('intervalo_busca', 15))
    config['intervalo_post'] = int(request.form.get('intervalo_post', 30))
    config['intervalo_post_min'] = int(request.form.get('intervalo_post_min', 8))
    config['intervalo_post_max'] = int(request.form.get('intervalo_post_max', 10))
    config['usar_intervalo_aleatorio'] = 'usar_intervalo_aleatorio' in request.form
    config['opacidade'] = int(request.form.get('opacidade', 30)) / 100.0
    
    salvar_config(config, agent_id)
    logging.info(f"[AGENT-{agent_id}] Configurações salvas")
    
    return redirect(url_for('visualizar_agente', agent_id=agent_id))

@app.route("/iniciar_agente/<agent_id>", methods=['POST'])
def iniciar_agente(agent_id):
    """Inicia um agente específico"""
    if agent_manager.inicializar_agente(agent_id):
        # Marca como ativo na configuração
        config = carregar_config(agent_id)
        config['ativo'] = True
        salvar_config(config, agent_id)
        logging.info(f"[AGENT-{agent_id}] Iniciado pelo usuário")
    
    return redirect(url_for('visualizar_agente', agent_id=agent_id))

@app.route("/parar_agente/<agent_id>", methods=['POST'])
def parar_agente(agent_id):
    """Para um agente específico"""
    agent_manager.parar_agente(agent_id)
    
    # Marca como inativo na configuração
    config = carregar_config(agent_id)
    config['ativo'] = False
    salvar_config(config, agent_id)
    
    logging.info(f"[AGENT-{agent_id}] Parado pelo usuário")
    return redirect(url_for('visualizar_agente', agent_id=agent_id))

@app.route("/postar_agente/<agent_id>", methods=['POST'])
def postar_manual_agente(agent_id):
    """Postagem manual para um agente específico"""
    import threading
    item_id = request.form.get('item_id')
    
    if agent_id in agent_manager.agents:
        if item_id:
            threading.Thread(target=agent_manager.postar_da_fila_agente, args=(agent_id, item_id)).start()
        else:
            threading.Thread(target=agent_manager.postar_da_fila_agente, args=(agent_id,)).start()
        
        logging.info(f"[AGENT-{agent_id}] Postagem manual solicitada")
    
    return redirect(url_for('visualizar_agente', agent_id=agent_id))

@app.route("/reprovar_item/<agent_id>/<item_id>", methods=['POST'])
def reprovar_item_agente(agent_id, item_id):
    """Reprova um item específico de um agente"""
    from database import Database
    
    if agent_id in agent_manager.agents:
        item = Database.pegar_item_fila_agente(agent_id, item_id)
        if item:
            Database.registrar_no_historico_agente(agent_id, item, "REJEITADA", "Rejeitado manualmente")
            Database.remover_da_fila_agente(agent_id, item_id)
            logging.info(f"[AGENT-{agent_id}] Item {item_id} reprovado manualmente")
    
    return redirect(url_for('visualizar_agente', agent_id=agent_id))

@app.route("/status_sistema")
def status_sistema():
    """API para status geral do sistema"""
    config_global = carregar_config()
    agentes = listar_agentes()
    status_agentes = agent_manager.get_status_agentes()
    
    return jsonify({
        'total_agentes': len(agentes),
        'agentes_ativos': len(status_agentes),
        'config_global': config_global,
        'agentes': status_agentes,
        'custo_sessao': custo_sessao_atual
    })

@app.route("/config_global")
def config_global():
    """Página de configuração global (APIs, etc.)"""
    config = carregar_config()
    return render_template("config_global.html", config=config)

@app.route("/salvar_config_global", methods=['POST'])
def salvar_config_global():
    """Salva configuração global"""
    config = carregar_config()
    
    config['gnews_api_key'] = request.form.get('gnews_api_key', '')
    config['newsdata_api_key'] = request.form.get('newsdata_api_key', '')
    config['google_api_key'] = request.form.get('google_api_key', '')
    
    salvar_config(config)
    
    # Reconfigura Gemini se necessário
    if config.get("google_api_key"):
        genai.configure(api_key=config["google_api_key"])
    
    logging.info("Configuração global salva")
    return redirect(url_for('config_global'))

# === INICIALIZAÇÃO ===

if __name__ == "__main__":
    print("⚙️ Configurando logging...")
    setup_logging()
    
    print("🔧 Carregando configurações...")
    config = carregar_config()
    
    # Verifica configurações básicas
    if not config.get("google_api_key"):
        print("\n🔑 CONFIGURAÇÃO NECESSÁRIA:")
        print("Configurando APIs globais...")
        config["gnews_api_key"] = input("📰 Chave da API GNews (opcional): ") or ""
        config["newsdata_api_key"] = input("📊 Chave da API NewsData.io (opcional): ") or ""
        config["google_api_key"] = input("✨ Chave da API Google Gemini: ")
        salvar_config(config)
        print("✅ Configurações globais salvas!")
    
    # Configura Gemini
    if config.get("google_api_key"):
        genai.configure(api_key=config.get("google_api_key"))
        print("✅ Google Gemini configurado!")
    
    print("🤖 Carregando agentes configurados...")
    agent_manager.carregar_agentes()
    
    print("\n🌐 Sistema Multi-Agente iniciado!")
    print("🔗 Acesse: http://127.0.0.1:8080")
    print("✨ Sistema funcionando! Pressione Ctrl+C para parar.\n")
    
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Parando sistema...")
        agent_manager.parar_todos()
        print("✅ Sistema parado com segurança!")