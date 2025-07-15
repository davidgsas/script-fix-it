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
            
            # Atraso aleatório inicial mais variado
            atraso_inicial = random.uniform(3, 15)
            logging.info(f"Aguardando {atraso_inicial:.1f} segundos...")
            time.sleep(atraso_inicial)
            
            # Simulação de comportamento humano - às vezes verifica feed antes de postar
            if random.random() < 0.3:  # 30% de chance
                logging.info("[INSTAGRAM] Verificando feed antes de postar...")
                try:
                    self.client.get_timeline_feed()
                    time.sleep(random.uniform(2, 5))
                except:
                    pass
            
            # Postagem com atraso adicional variado
            atraso_pre_post = random.uniform(1, 4)
            time.sleep(atraso_pre_post)
            
            self.client.photo_upload(caminho_imagem, legenda)
            
            # Atraso pós-postagem para simular comportamento humano
            atraso_pos_post = random.uniform(2, 8)
            time.sleep(atraso_pos_post)
            
            logging.info("[INSTAGRAM] Postagem realizada com sucesso!")
            return True
            
        except Exception as e:
            logging.error(f"[INSTAGRAM] ERRO durante a postagem: {e}")
            return False
    
    def esta_conectado(self):
        return bool(self.client.user_id)
    
    def status_conexao(self):
        return "Conectado ✅" if self.esta_conectado() else "Desconectado 🔴"