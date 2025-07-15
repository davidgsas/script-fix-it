import requests
import logging
from config import carregar_config

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
            
            return [{
                "title": article.get("title"),
                "description": article.get("description"),
                "content": article.get("content"),
                "image": article.get("image"),
                "source": {"name": article.get("source", {}).get("name")}
            } for article in articles]
            
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
    def buscar_todas_noticias():
        cfg = carregar_config()
        
        if not cfg.get("apis_ativas") or not cfg.get("idiomas_busca") or not cfg.get("categorias_ativas"):
            return []
        
        logging.info(f"--- [BUSCA] Iniciando ciclo de busca nas APIs {cfg['apis_ativas']} ---")
        todas_noticias = []
        
        for api in cfg["apis_ativas"]:
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