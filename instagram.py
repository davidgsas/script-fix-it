# -*- coding: utf-8 -*-
import os
import time
import random
import logging
from instagrapi import Client
from config import carregar_config, SESSION_FILE

class InstagramManager:
    """Gerenciador do Instagram"""
    
    def __init__(self):
        self.client = Client()
    
    def login_com_sessao(self):
        """Faz login no Instagram usando sessão salva ou nova"""
        cfg = carregar_config()
        
        try:
            # Tenta carregar sessão existente
            if os.path.exists(SESSION_FILE):
                self.client.load_settings(SESSION_FILE)
                logging.info("[INSTAGRAM] Sessão de login carregada.")
            else:
                raise Exception("Sem sessão")
            
            # Valida login
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
        """Posta uma foto no Instagram"""
        if not self.client.user_id:
            logging.error("[INSTAGRAM] Cliente não está logado")
            return False
        
        try:
            logging.info(f"[INSTAGRAM] Iniciando upload da imagem...")
            
            # Delay aleatório para parecer mais humano
            atraso = random.uniform(5, 10)
            logging.info(f"Aguardando {atraso:.1f} segundos...")
            time.sleep(atraso)
            
            # Faz o upload
            self.client.photo_upload(caminho_imagem, legenda)
            logging.info("[INSTAGRAM] Postagem realizada com sucesso!")
            return True
            
        except Exception as e:
            logging.error(f"[INSTAGRAM] ERRO durante a postagem: {e}")
            return False
    
    def esta_conectado(self):
        """Verifica se está conectado"""
        return bool(self.client.user_id)
    
    def status_conexao(self):
        """Retorna status da conexão formatado"""
        return "Conectado ✅" if self.esta_conectado() else "Desconectado 🔴"