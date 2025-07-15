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
    def get_local_news():
        """
        Busca notícias do banco SQLite local dos últimos 30 minutos
        """
        db_path = '/Users/davidgabriel/hubbots/scrapernews/articles.db'
        logging.info(f"[BUSCA] Buscando no banco SQLite local: {db_path}")
        
        try:
            # Filtro temporal - últimos 30 minutos
            ponto_de_corte = datetime.now() - timedelta(minutes=30)
            ponto_de_corte_str = ponto_de_corte.strftime('%Y-%m-%d %H:%M:%S')
            
            # Conecta ao banco
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Busca artigos recentes
            query = "SELECT id, title, source_name, main_image_url, content_text FROM articles WHERE datetime(date_inserted) >= datetime(?)"
            cursor.execute(query, (ponto_de_corte_str,))
            articles = cursor.fetchall()
            conn.close()
            
            logging.info(f"[FILTRO] SQLite Local: {len(articles)} artigos encontrados (últimos 30min).")
            
            return [{
                "title": article["title"],
                "description": None,  # SQLite não tem description
                "content": article["content_text"],
                "image": article["main_image_url"],
                "source": {"name": article["source_name"]}
            } for article in articles]
            
        except sqlite3.Error as e:
            logging.error(f"[BUSCA] ERRO SQLite: {e}")
            return []
        except Exception as e:
            logging.error(f"[BUSCA] ERRO inesperado no SQLite: {e}")
            return []
    
    @staticmethod
    def buscar_todas_noticias():
        cfg = carregar_config()
        
        if not cfg.get("apis_ativas") or not cfg.get("idiomas_busca") or not cfg.get("categorias_ativas"):
            return []
        
        logging.info(f"--- [BUSCA] Iniciando ciclo de busca nas APIs {cfg['apis_ativas']} ---")
        todas_noticias = []
        
        for api in cfg["apis_ativas"]:
            # Condição especial para SQLite local
            if api == 'local_db':
                artigos = NewsAPIs.get_local_news()
                for artigo in artigos:
                    artigo['api_fonte'] = 'local_db'
                    artigo['idioma_original'] = 'pt'  # Assumindo português
                    artigo['categoria_busca'] = 'local'
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