#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import getpass
import threading
import logging
import json
import random
import google.generativeai as genai
from flask import Flask, render_template, redirect, url_for, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

print("🚀 INICIANDO BOT DE INSTAGRAM...")

# Importa os módulos criados
try:
    from config import setup_logging, carregar_config, salvar_config
    from database import setup_database, Database
    from ai_services import AIServices, custo_sessao_atual
    from news_apis import NewsAPIs
    from instagram import InstagramManager
    from media import MediaProcessor
    print("✅ Todos os módulos importados com sucesso!")
except Exception as e:
    print(f"❌ Erro ao importar módulos: {e}")
    exit(1)

# Configuração inicial
app = Flask(__name__)

# Instâncias globais
instagram = InstagramManager()
scheduler = BackgroundScheduler(daemon=True, timezone='America/Sao_Paulo')

def processar_noticias():
    """Processa novas notícias encontradas pelas APIs"""
    noticias = NewsAPIs.buscar_todas_noticias()
    
    for noticia in noticias:
        custo_total_noticia = 0.0
        
        # Extrai dados básicos
        titulo_bruto = noticia.get("title")
        url_imagem = noticia.get("image")
        
        if not titulo_bruto or not MediaProcessor.validar_imagem(url_imagem):
            continue
        
        # Remove fonte do título se presente
        titulo_original = titulo_bruto.rsplit(" - ", 1)[0] if " - " in titulo_bruto else titulo_bruto
        conteudo_original = noticia.get("content") or noticia.get("description", "")
        
        # Gera hash semântico para detectar duplicatas
        semantic_hash, custo_hash = AIServices.gerar_titulo_canonico(titulo_original, conteudo_original)
        custo_total_noticia += custo_hash
        
        # Prepara dados para histórico
        dados_para_historico = {
            "titulo_original": titulo_original,
            "conteudo_original": conteudo_original,
            "idioma_original": noticia['idioma_original'],
            "api_fonte": noticia['api_fonte'],
            "custo_usd": custo_total_noticia,
            "semantic_hash": semantic_hash
        }
        
        # Verifica duplicata por título primeiro
        if Database.verificar_titulo_duplicado(titulo_original):
            dados_para_historico.update({"titulo_refinado": f"[DUPLICATA TÍTULO] {titulo_original[:150]}"})
            Database.registrar_no_historico(dados_para_historico, "REJEITADA", "Título já processado")
            logging.info(f"[FILTRO] Notícia ignorada - título já processado: {titulo_original[:100]}...")
            continue
        
        # Verifica duplicata semântica
        if Database.verificar_duplicata_semantica(semantic_hash):
            dados_para_historico.update({"titulo_refinado": f"[DUPLICATA] {titulo_original[:150]}"})
            Database.registrar_no_historico(dados_para_historico, "REJEITADA", "Duplicata Semântica")
            continue
        
        # Filtra relevância
        veredito, custo_filtro = AIServices.filtrar_relevancia(titulo_original, conteudo_original)
        custo_total_noticia += custo_filtro
        dados_para_historico["custo_usd"] = custo_total_noticia
        
        if veredito != "APROVADA":
            dados_para_historico.update({
                "titulo_refinado": f"[REJEITADO] {titulo_original[:150]}",
                "conteudo_reescrito": ""
            })
            Database.registrar_no_historico(dados_para_historico, "REJEITADA", veredito)
            continue
        
        # Traduz se necessário
        if noticia['idioma_original'] == 'en':
            titulo_processado, custo_trad_titulo = AIServices.traduzir_texto(titulo_original, 'Inglês')
            conteudo_processado, custo_trad_conteudo = AIServices.traduzir_texto(conteudo_original, 'Inglês')
            custo_total_noticia += custo_trad_titulo + custo_trad_conteudo
        else:
            titulo_processado = titulo_original
            conteudo_processado = conteudo_original
        
        # Refina título
        titulo_refinado, custo_refino = AIServices.melhorar_titulo(titulo_processado)
        custo_total_noticia += custo_refino
        dados_para_historico.update({"titulo_refinado": titulo_refinado})
        
        # Reescreve conteúdo e categoriza
        conteudo_reescrito, custo_reescrita = AIServices.reescrever_legenda(conteudo_processado)
        categoria_ia, custo_categoria = AIServices.categorizar_noticia(titulo_refinado, conteudo_reescrito)
        custo_total_noticia += custo_reescrita + custo_categoria
        
        # Finaliza dados
        dados_para_historico.update({
            "conteudo_reescrito": conteudo_reescrito,
            "categoria_ia": categoria_ia,
            "custo_usd": custo_total_noticia,
            "url_imagem": url_imagem,
            "fonte": noticia.get("source", {}).get("name"),
            "descricao": noticia.get("description")
        })
        
        # Adiciona na fila
        Database.adicionar_na_fila(dados_para_historico)

def postar_da_fila(item_id=None):
    """Posta próximo item da fila ou item específico"""
    if item_id:
        from database import get_db_connection
        conn = get_db_connection()
        item_row = conn.execute("SELECT * FROM fila_postagem WHERE id = ?", (item_id,)).fetchone()
        conn.close()
    else:
        item_row = Database.pegar_proximo_da_fila()
        if item_row:
            item_row = {k: v for k, v in item_row.items()}
    
    if not item_row:
        if not item_id:
            logging.info("[FILA] Fila de postagem vazia.")
        return
    
    item = dict(item_row) if hasattr(item_row, 'keys') else item_row
    logging.info(f"--- [POST] Iniciando processo de postagem para: {item['titulo_refinado']} ---")
    
    # Cria imagem
    caminho_imagem = MediaProcessor.criar_imagem_post(
        item['titulo_refinado'], 
        item['url_imagem'], 
        item['categoria_ia']
    )
    
    if caminho_imagem:
        # Prepara legenda
        conteudo_curado = item.get("conteudo_reescrito") or "Sem conteúdo adicional."
        fonte = item.get("fonte", "Fonte não informada")
        categoria_ia = item.get("categoria_ia", "noticias")
        
        # Gera hashtags
        hashtags_ia, custo_hashtags = AIServices.gerar_hashtags(f"{item['titulo_refinado']} {conteudo_curado}")
        item['custo_usd'] += custo_hashtags
        
        legenda = f"siga: @noticiasbr.ai | {conteudo_curado}\n\nFonte: {fonte}\n\n#{categoria_ia.replace(' ','')} {hashtags_ia}"
        
        # Posta
        sucesso = instagram.postar_foto(caminho_imagem, legenda)
        
        if sucesso:
            Database.registrar_no_historico(item, "POSTADO")
        else:
            Database.registrar_no_historico(item, "FALHA", "Erro durante postagem")
        
        # Remove da fila
        Database.remover_da_fila(item['id'])
        
        # Reagenda próximo post com intervalo aleatório
        reagendar_proximo_post()

def reagendar_proximo_post():
    """Reagenda o próximo post com intervalo aleatório"""
    cfg = carregar_config()
    
    if cfg.get("usar_intervalo_aleatorio", True):
        min_intervalo = cfg.get("intervalo_post_min", 8)
        max_intervalo = cfg.get("intervalo_post_max", 10)
        intervalo_aleatorio = random.uniform(min_intervalo, max_intervalo)
        
        # Remove o job atual e cria um novo com intervalo aleatório
        try:
            scheduler.remove_job('postador_fila')
        except:
            pass
        
        scheduler.add_job(
            postar_da_fila,
            'interval',
            minutes=intervalo_aleatorio,
            id='postador_fila'
        )
        
        logging.info(f"[SCHEDULER] Próximo post agendado para {intervalo_aleatorio:.1f} minutos")
    else:
        # Usa intervalo fixo
        intervalo_fixo = cfg.get("intervalo_post", 30)
        scheduler.reschedule_job('postador_fila', trigger='interval', minutes=intervalo_fixo)

# --- ROTAS FLASK ---

@app.route("/")
def index():
    return render_template("index.html", status=carregar_config())

@app.route("/historico")
def historico():
    return render_template("historico.html", historico=Database.pegar_historico_completo())

@app.route("/limpar_fila", methods=["POST"])
def limpar_fila():
    Database.limpar_fila()
    logging.info("Fila de postagens foi limpa manualmente.")
    return redirect(url_for('index'))

@app.route("/status_update")
def status_update():
    cfg = carregar_config()
    status_json = cfg.copy()
    
    status_json["fila_de_noticias"] = Database.pegar_fila_completa()
    status_json["conexao_insta"] = instagram.status_conexao()
    status_json["log_recente"] = list(Database.pegar_log_recente())
    status_json["custo_sessao"] = custo_sessao_atual
    status_json["custo_total"] = Database.obter_custo_total()
    
    try:
        status_json["proxima_busca"] = scheduler.get_job('buscador_noticias').next_run_time.strftime('%H:%M:%S')
        status_json["proximo_post"] = scheduler.get_job('postador_fila').next_run_time.strftime('%H:%M:%S')
    except Exception:
        status_json["proxima_busca"] = "Aguardando..."
        status_json["proximo_post"] = "Aguardando..."
    
    return jsonify(status_json)

@app.route("/postar_proximo", methods=["POST"])
def postar_agora():
    logging.info("Postagem manual do próximo item da fila solicitada...")
    threading.Thread(target=postar_da_fila).start()
    return redirect(url_for('index'))

@app.route("/postar_item/<item_id>", methods=["POST"])
def postar_item_especifico(item_id):
    logging.info(f"Postagem manual do item {item_id} solicitada...")
    threading.Thread(target=postar_da_fila, args=(item_id,)).start()
    return redirect(url_for('index'))

@app.route("/reprovar_item/<item_id>", methods=["POST"])
def reprovar_item_especifico(item_id):
    from database import get_db_connection
    conn = get_db_connection()
    item_row = conn.execute("SELECT * FROM fila_postagem WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    
    if item_row:
        item = dict(item_row)
        Database.registrar_no_historico(item, "REJEITADA", "Rejeitado manualmente")
        Database.remover_da_fila(item_id)
        logging.info(f"Notícia com ID {item_id} reprovada e movida para o histórico.")
    
    return redirect(url_for('index'))

@app.route("/atualizar_config", methods=['POST'])
def atualizar_config():
    cfg = carregar_config()
    
    # Atualiza configurações
    cfg["apis_ativas"] = request.form.getlist('apis')
    cfg["categorias_ativas"] = request.form.getlist('categorias')
    cfg["idiomas_busca"] = request.form.getlist('idiomas')
    cfg["opacidade"] = int(request.form.get('opacidade', 30)) / 100.0
    
    # Atualiza intervalos e reagenda se necessário
    novo_intervalo_busca = int(request.form.get('intervalo_busca', 15))
    novo_intervalo_post = int(request.form.get('intervalo_post', 30))
    novo_intervalo_post_min = int(request.form.get('intervalo_post_min', 8))
    novo_intervalo_post_max = int(request.form.get('intervalo_post_max', 10))
    usar_intervalo_aleatorio = 'usar_intervalo_aleatorio' in request.form
    
    if novo_intervalo_busca != cfg.get("intervalo_busca"):
        scheduler.reschedule_job('buscador_noticias', trigger='interval', minutes=novo_intervalo_busca)
    
    # Atualiza configurações de postagem
    if (novo_intervalo_post != cfg.get("intervalo_post") or 
        novo_intervalo_post_min != cfg.get("intervalo_post_min") or
        novo_intervalo_post_max != cfg.get("intervalo_post_max") or
        usar_intervalo_aleatorio != cfg.get("usar_intervalo_aleatorio")):
        
        # Remove job atual
        try:
            scheduler.remove_job('postador_fila')
        except:
            pass
        
        # Cria novo job baseado na configuração
        if usar_intervalo_aleatorio:
            intervalo_inicial = random.uniform(novo_intervalo_post_min, novo_intervalo_post_max)
        else:
            intervalo_inicial = novo_intervalo_post
        
        scheduler.add_job(
            postar_da_fila,
            'interval',
            minutes=intervalo_inicial,
            id='postador_fila'
        )
    
    cfg["intervalo_busca"] = novo_intervalo_busca
    cfg["intervalo_post"] = novo_intervalo_post
    cfg["intervalo_post_min"] = novo_intervalo_post_min
    cfg["intervalo_post_max"] = novo_intervalo_post_max
    cfg["usar_intervalo_aleatorio"] = usar_intervalo_aleatorio
    
    salvar_config(cfg)
    logging.info("Configurações salvas.")
    return redirect(url_for('index'))

# --- INICIALIZAÇÃO ---

if __name__ == "__main__":
    print("⚙️ Configurando logging...")
    setup_logging()
    
    print("📦 Configurando banco de dados...")
    setup_database()
    
    print("🔧 Carregando configurações...")
    config = carregar_config()
    
    print(f"📋 Status das configurações:")
    print(f"   - insta_user: {'✅' if config.get('insta_user') else '❌'}")
    print(f"   - gnews_api_key: {'✅' if config.get('gnews_api_key') else '❌'}")
    
    # Verifica se tem configurações básicas
    if not config.get("insta_user") or not config.get("gnews_api_key"):
        print("\n🔑 CONFIGURAÇÕES NECESSÁRIAS:")
        print("Precisamos configurar as APIs e credenciais...")
        config["insta_user"] = input("👤 Usuário do Instagram: ")
        config["insta_pass"] = getpass.getpass("🔑 Senha do Instagram: ")
        config["gnews_api_key"] = input("📰 Chave da API GNews: ")
        config["newsdata_api_key"] = input("📊 Chave da API NewsData.io: ")
        config["google_api_key"] = input("✨ Chave da API Google Gemini: ")
        salvar_config(config)
        print("✅ Configurações salvas!")
    
    print("\n📱 Fazendo login no Instagram...")
    
    # Login no Instagram
    if instagram.login_com_sessao():
        print("✅ Login no Instagram realizado com sucesso!")
        
        # Configura Gemini
        if config.get("google_api_key"):
            genai.configure(api_key=config.get("google_api_key"))
            print("✅ Google Gemini configurado!")
        
        print("⏰ Configurando agendamento de tarefas...")
        
        # Agenda tarefas
        scheduler.add_job(
            processar_noticias, 
            'interval', 
            minutes=config.get("intervalo_busca", 15), 
            id='buscador_noticias'
        )
        # Configura agendamento de postagem
        if config.get("usar_intervalo_aleatorio", True):
            intervalo_inicial = random.uniform(
                config.get("intervalo_post_min", 8),
                config.get("intervalo_post_max", 10)
            )
        else:
            intervalo_inicial = config.get("intervalo_post", 30)
        
        scheduler.add_job(
            postar_da_fila, 
            'interval', 
            minutes=intervalo_inicial, 
            id='postador_fila'
        )
        
        print("⏰ Agendamento configurado. Primeira busca acontecerá no intervalo programado.")
        # Inicia apenas o scheduler, sem busca inicial
        scheduler.start()
        
        print("\n🌐 Servidor web iniciado!")
        print("🔗 Acesse: http://127.0.0.1:8080")
        print("✨ Bot está funcionando! Pressione Ctrl+C para parar.\n")
        
        app.run(host='0.0.0.0', port=8080, debug=False)
    else:
        print("❌ FALHA: Login no Instagram falhou. Servidor não iniciado.")
        print("   Verifique suas credenciais e tente novamente.")