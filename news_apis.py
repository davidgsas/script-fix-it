import requests
import logging
import sqlite3
from config import carregar_config
from datetime import datetime, timedelta, timezone

class NewsAPIs:
    
    @staticmethod
    def get_gnews(categoria, idioma, pais):
        cfg = carregar_config()
        
        if not cfg.get("gnews_api_key"):
            return []
        
        url = f"https://gnews.io/api/v4/top-headlines?topic={categoria}&lang={idioma}&country={pais}&max=10&expand=content&apikey={cfg['gnews_api_key']}"
        
        try:
            logging.info(f"[BUSCA] Buscando em GNews/{categoria} ({pais.upper()})...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            articles = response.json().get("articles", [])
            
            # Filtro temporal - últimas 3 horas
            ponto_de_corte = datetime.now(timezone.utc) - timedelta(hours=3)
            noticias_filtradas = []
            
            for article in articles:
                data_publicacao_str = article.get("publishedAt")
                if not data_publicacao_str:
                    continue
                
                data_publicacao_obj = datetime.fromisoformat(data_publicacao_str.replace('Z', '+00:00'))
                
                if data_publicacao_obj >= ponto_de_corte:
                    noticias_filtradas.append(article)
            
            logging.info(f"[FILTRO] GNews/{categoria}: {len(articles)} recebidos, {len(noticias_filtradas)} aprovados (últimas 3h).")
            
            return [{
                "title": article.get("title"),
                "description": article.get("description"),
                "content": article.get("content"),
                "image": article.get("image"),
                "source": {"name": article.get("source", {}).get("name")}
            } for article in noticias_filtradas]
            
        except Exception as e:
            logging.error(f"[BUSCA] ERRO ao buscar em GNews/{categoria} ({pais.upper()}): {e}")
            return []
    
    @staticmethod
    def get_newsdata(categoria, idioma, pais):
        cfg = carregar_config()
        
        if not cfg.get("newsdata_api_key"):
            return []
        
        lang_map = {'pt': 'pt', 'en': 'en'}
        country_map = {'br': 'br', 'us': 'us'}
        
        if categoria == 'breaking-news':
            categoria = 'top'
        if categoria == 'nation':
            categoria = 'politics'
        
        url = f"https://newsdata.io/api/1/news?apikey={cfg['newsdata_api_key']}&category={categoria}&language={lang_map[idioma]}&country={country_map[pais]}"
        
        try:
            logging.info(f"[BUSCA] Buscando em NewsData/{categoria} ({pais.upper()})...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            articles = response.json().get("results", [])
            
            return [{
                "title": article.get("title"),
                "description": article.get("description"),
                "content": article.get("content"),
                "image": article.get("image_url"),
                "source": {"name": article.get("source_id")}
            } for article in articles]
            
        except Exception as e:
            logging.error(f"[BUSCA] ERRO ao buscar em NewsData/{categoria} ({pais.upper()}): {e}")
            return []
    
    @staticmethod
    def get_local_news(pasta_feed=None):
        """
        Busca notícias via API REST do servidor interno
        """
        api_url = 'http://10.100.5.56:8000/api/feed'
        if pasta_feed:
            api_url += f'?pasta={pasta_feed}'
        
        logging.info(f"[BUSCA] Buscando via API REST: {api_url}")
        
        try:
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            articles = response.json()
            
            # Filtro temporal - últimos 30 minutos
            ponto_de_corte = datetime.now() - timedelta(minutes=30)
            noticias_filtradas = []
            
            for article in articles:
                date_inserted_str = article.get("date_inserted")
                if not date_inserted_str:
                    continue
                
                # Converte a data ISO 8601 para datetime
                try:
                    date_inserted_obj = datetime.fromisoformat(date_inserted_str.replace('Z', '+00:00'))
                    # Remove timezone info para comparar com datetime local
                    date_inserted_obj = date_inserted_obj.replace(tzinfo=None)
                except ValueError:
                    # Se houver erro na conversão, pula o artigo
                    continue
                
                if date_inserted_obj >= ponto_de_corte:
                    noticias_filtradas.append(article)
            
            logging.info(f"[FILTRO] API REST Local: {len(articles)} recebidos, {len(noticias_filtradas)} aprovados (últimos 30min).")
            
            return [{
                "title": article.get("title"),
                "description": None,  # API não retorna description
                "content": article.get("content_text"),
                "image": article.get("main_image_url"),
                "source": {"name": article.get("source_name")}
            } for article in noticias_filtradas]
            
        except requests.RequestException as e:
            logging.error(f"[BUSCA] ERRO na requisição para API REST: {e}")
            return []
        except Exception as e:
            logging.error(f"[BUSCA] ERRO inesperado na API REST: {e}")
            return []
    
    @staticmethod
    def obter_pastas_disponiveis():
        """
        Busca as pastas disponíveis no servidor local
        """
        api_url = 'http://10.100.5.56:8000/api/pastas'
        
        logging.info(f"[CONFIG] Buscando pastas disponíveis: {api_url}")
        
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            pastas = response.json()
            
            logging.info(f"[CONFIG] Pastas encontradas: {pastas}")
            return pastas
            
        except requests.RequestException as e:
            logging.error(f"[CONFIG] ERRO ao buscar pastas: {e}")
            # Retorna pastas padrão em caso de erro
            return ['geral', 'esportes', 'tecnologia', 'politica', 'economia', 'saude', 'entretenimento']
        except Exception as e:
            logging.error(f"[CONFIG] ERRO inesperado ao buscar pastas: {e}")
            return ['geral', 'esportes', 'tecnologia', 'politica', 'economia', 'saude', 'entretenimento']
    
    @staticmethod
    def buscar_todas_noticias(agent_config=None):
        if agent_config is None:
            cfg = carregar_config()
        else:
            cfg = agent_config
        
        if not cfg.get("apis_ativas") or not cfg.get("idiomas_busca") or not cfg.get("categorias_ativas"):
            return []
        
        pasta_feed = cfg.get("pasta_feed", "geral")
        logging.info(f"--- [BUSCA] Iniciando ciclo de busca nas APIs {cfg['apis_ativas']} (pasta: {pasta_feed}) ---")
        todas_noticias = []
        
        for api in cfg["apis_ativas"]:
            # Condição especial para API local
            if api == 'servidor_local':
                artigos = NewsAPIs.get_local_news(pasta_feed)
                for artigo in artigos:
                    artigo['api_fonte'] = 'servidor_local'
                    artigo['idioma_original'] = 'pt'  # Assumindo português
                    artigo['categoria_busca'] = 'local'
                    artigo['pasta_feed'] = pasta_feed
                todas_noticias.extend(artigos)
                continue  # Pula para próxima API
            
            # Lógica para APIs online
            for idioma in cfg["idiomas_busca"]:
                pais = 'us' if idioma == 'en' else 'br'
                
                for categoria in cfg["categorias_ativas"]:
                    artigos = []
                    
                    if api == 'gnews':
                        artigos = NewsAPIs.get_gnews(categoria, idioma, pais)
                    elif api == 'newsdata':
                        artigos = NewsAPIs.get_newsdata(categoria, idioma, pais)
                    
                    for artigo in artigos:
                        artigo['api_fonte'] = api
                        artigo['idioma_original'] = idioma
                        artigo['categoria_busca'] = categoria
                    
                    todas_noticias.extend(artigos)
        
        logging.info(f"--- [BUSCA] Ciclo finalizado. {len(todas_noticias)} notícias encontradas ---")
        return todas_noticias