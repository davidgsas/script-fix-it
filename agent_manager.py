#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gerenciador de Agentes Multi-Instagram
Permite executar múltiplos bots com diferentes contas e configurações
"""

import os
import threading
import logging
import time
import random
from apscheduler.schedulers.background import BackgroundScheduler
from config import carregar_config, listar_agentes, get_agent_db_path, get_agent_session_path
from database import Database
from ai_services import AIServices
from news_apis import NewsAPIs
from instagram import InstagramManager
from media import MediaProcessor

class AgentManager:
    def __init__(self):
        self.agents = {}  # {agent_id: {'scheduler': scheduler, 'instagram': instagram_instance, 'config': config}}
        self.running = False
    
    def carregar_agentes(self):
        """Carrega todos os agentes configurados"""
        agentes_info = listar_agentes()
        
        for agente_info in agentes_info:
            agent_id = agente_info['id']
            if agente_info['ativo']:
                self.inicializar_agente(agent_id)
        
        logging.info(f"[MANAGER] {len(self.agents)} agentes carregados e ativos")
    
    def inicializar_agente(self, agent_id):
        """Inicializa um agente específico"""
        try:
            config = carregar_config(agent_id)
            
            if not config.get('insta_user') or not config.get('insta_pass'):
                logging.warning(f"[AGENT-{agent_id}] Credenciais do Instagram não configuradas")
                return False
            
            # Configura banco de dados específico do agente
            db_path = get_agent_db_path(agent_id)
            Database.setup_database_for_agent(agent_id, db_path)
            
            # Configura Instagram com sessão específica
            instagram = InstagramManager(get_agent_session_path(agent_id))
            if not instagram.login_com_sessao(config['insta_user'], config['insta_pass']):
                logging.error(f"[AGENT-{agent_id}] Falha no login do Instagram")
                return False
            
            # Configura scheduler
            scheduler = BackgroundScheduler(daemon=True, timezone='America/Sao_Paulo')
            
            # Agenda busca de notícias
            scheduler.add_job(
                self.processar_noticias_agente,
                'interval',
                minutes=config.get("intervalo_busca", 15),
                args=[agent_id],
                id=f'buscador_{agent_id}'
            )
            
            # Agenda postagens
            if config.get("usar_intervalo_aleatorio", True):
                intervalo_inicial = random.uniform(
                    config.get("intervalo_post_min", 8),
                    config.get("intervalo_post_max", 10)
                )
            else:
                intervalo_inicial = config.get("intervalo_post", 30)
            
            scheduler.add_job(
                self.postar_da_fila_agente,
                'interval',
                minutes=intervalo_inicial,
                args=[agent_id],
                id=f'postador_{agent_id}'
            )
            
            scheduler.start()
            
            # Armazena o agente
            self.agents[agent_id] = {
                'scheduler': scheduler,
                'instagram': instagram,
                'config': config,
                'db_path': db_path
            }
            
            logging.info(f"[AGENT-{agent_id}] Iniciado com sucesso (pasta: {config.get('pasta_feed', 'geral')})")
            return True
            
        except Exception as e:
            logging.error(f"[AGENT-{agent_id}] Erro na inicialização: {e}")
            return False
    
    def processar_noticias_agente(self, agent_id):
        """Processa notícias para um agente específico"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        config = agent['config']
        
        logging.info(f"[AGENT-{agent_id}] Iniciando busca de notícias (pasta: {config.get('pasta_feed', 'geral')})")
        
        noticias = NewsAPIs.buscar_todas_noticias(config)
        
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
                "semantic_hash": semantic_hash,
                "pasta_feed": noticia.get('pasta_feed', config.get('pasta_feed', 'geral'))
            }
            
            # Verifica duplicata por título primeiro (específico do agente)
            if Database.verificar_titulo_duplicado_agente(agent_id, titulo_original):
                dados_para_historico.update({"titulo_refinado": f"[DUPLICATA TÍTULO] {titulo_original[:150]}"})
                Database.registrar_no_historico_agente(agent_id, dados_para_historico, "REJEITADA", "Título já processado")
                logging.info(f"[AGENT-{agent_id}] Notícia ignorada - título já processado: {titulo_original[:100]}...")
                continue
            
            # Verifica duplicata semântica (específico do agente)
            if Database.verificar_duplicata_semantica_agente(agent_id, semantic_hash):
                dados_para_historico.update({"titulo_refinado": f"[DUPLICATA] {titulo_original[:150]}"})
                Database.registrar_no_historico_agente(agent_id, dados_para_historico, "REJEITADA", "Duplicata Semântica")
                continue
            
            # Processa conforme lógica original...
            # (resto do processamento idêntico ao app.py original, mas usando funções específicas do agente)
            
            # Filtra relevância
            veredito, custo_filtro = AIServices.filtrar_relevancia(titulo_original, conteudo_original)
            custo_total_noticia += custo_filtro
            dados_para_historico["custo_usd"] = custo_total_noticia
            
            if veredito != "APROVADA":
                dados_para_historico.update({
                    "titulo_refinado": f"[REJEITADO] {titulo_original[:150]}",
                    "conteudo_reescrito": ""
                })
                Database.registrar_no_historico_agente(agent_id, dados_para_historico, "REJEITADA", veredito)
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
            
            # Adiciona na fila do agente
            Database.adicionar_na_fila_agente(agent_id, dados_para_historico)
    
    def postar_da_fila_agente(self, agent_id, item_id=None):
        """Posta próximo item da fila de um agente específico"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        instagram = agent['instagram']
        config = agent['config']
        
        # Pega próximo item da fila do agente
        if item_id:
            item_row = Database.pegar_item_fila_agente(agent_id, item_id)
        else:
            item_row = Database.pegar_proximo_da_fila_agente(agent_id)
        
        if not item_row:
            logging.info(f"[AGENT-{agent_id}] Fila de postagem vazia.")
            return
        
        item = dict(item_row) if hasattr(item_row, 'keys') else item_row
        logging.info(f"--- [AGENT-{agent_id}] Iniciando postagem: {item['titulo_refinado']} ---")
        
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
            
            legenda = f"siga: @{config.get('insta_user', 'noticiasbr.ai')} | {conteudo_curado}\n\nFonte: {fonte}\n\n#{categoria_ia.replace(' ','')} {hashtags_ia}"
            
            # Posta
            sucesso = instagram.postar_foto(caminho_imagem, legenda)
            
            if sucesso:
                Database.registrar_no_historico_agente(agent_id, item, "POSTADO")
            else:
                Database.registrar_no_historico_agente(agent_id, item, "FALHA", "Erro durante postagem")
            
            # Remove da fila
            Database.remover_da_fila_agente(agent_id, item['id'])
            
            # Reagenda próximo post
            self.reagendar_proximo_post_agente(agent_id)
    
    def reagendar_proximo_post_agente(self, agent_id):
        """Reagenda próximo post para um agente específico"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        config = agent['config']
        scheduler = agent['scheduler']
        
        if config.get("usar_intervalo_aleatorio", True):
            min_intervalo = config.get("intervalo_post_min", 8)
            max_intervalo = config.get("intervalo_post_max", 10)
            intervalo_aleatorio = random.uniform(min_intervalo, max_intervalo)
            
            try:
                scheduler.remove_job(f'postador_{agent_id}')
            except:
                pass
            
            scheduler.add_job(
                self.postar_da_fila_agente,
                'interval',
                minutes=intervalo_aleatorio,
                args=[agent_id],
                id=f'postador_{agent_id}'
            )
            
            logging.info(f"[AGENT-{agent_id}] Próximo post agendado para {intervalo_aleatorio:.1f} minutos")
    
    def parar_agente(self, agent_id):
        """Para um agente específico"""
        if agent_id in self.agents:
            self.agents[agent_id]['scheduler'].shutdown()
            del self.agents[agent_id]
            logging.info(f"[AGENT-{agent_id}] Parado")
    
    def parar_todos(self):
        """Para todos os agentes"""
        for agent_id in list(self.agents.keys()):
            self.parar_agente(agent_id)
        logging.info("[MANAGER] Todos os agentes foram parados")
    
    def get_status_agentes(self):
        """Retorna status de todos os agentes"""
        status = {}
        for agent_id, agent in self.agents.items():
            config = agent['config']
            status[agent_id] = {
                'name': config.get('agent_name', f'Agente {agent_id}'),
                'pasta_feed': config.get('pasta_feed', 'geral'),
                'insta_user': config.get('insta_user', ''),
                'conexao_insta': agent['instagram'].status_conexao(),
                'fila_size': len(Database.pegar_fila_completa_agente(agent_id)),
                'ativo': True
            }
        return status

# Instância global do gerenciador
agent_manager = AgentManager()