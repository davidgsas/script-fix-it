import os
import time
import random
import logging
from instagrapi import Client
from config import carregar_config, SESSION_FILE

class InstagramManager:
    
    def __init__(self):
        self.client = Client()
    
    def login_com_sessao(self):
        cfg = carregar_config()
        
        try:
            if os.path.exists(SESSION_FILE):
                self.client.load_settings(SESSION_FILE)
                logging.info("[INSTAGRAM] Sessão de login carregada.")
            else:
                raise Exception("Sem sessão")
            
            self.client.login(cfg["insta_user"], cfg["insta_pass"])
            self.client.get_timeline_feed()
            
        except Exception as e:
            logging.warning(f"[INSTAGRAM] Não foi possível usar a sessão ({e}). Realizando login completo...")
            
            try:
                self.client.login(cfg["insta_user"], cfg["insta_pass"])
                self.client.dump_settings(SESSION_FILE)
                logging.info("[INSTAGRAM] Login completo realizado e nova sessão salva.")
                
            except Exception as e2:
                logging.error(f"[INSTAGRAM] ERRO CRÍTICO DE LOGIN: {e2}")
                return False
        
        return True
    
    def postar_foto(self, caminho_imagem, legenda):
        if not self.client.user_id:
            logging.error("[INSTAGRAM] Cliente não está logado")
            return False
        
        try:
            logging.info(f"[INSTAGRAM] Iniciando upload da imagem...")
            
            atraso = random.uniform(5, 10)
            logging.info(f"Aguardando {atraso:.1f} segundos...")
            time.sleep(atraso)
            
            self.client.photo_upload(caminho_imagem, legenda)
            logging.info("[INSTAGRAM] Postagem realizada com sucesso!")
            return True
            
        except Exception as e:
            logging.error(f"[INSTAGRAM] ERRO durante a postagem: {e}")
            return False
    
    def esta_conectado(self):
        return bool(self.client.user_id)
    
    def status_conexao(self):
        return "Conectado ✅" if self.esta_conectado() else "Desconectado 🔴"