import os
import requests
import textwrap
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import logging
from config import BASE_DIR, carregar_config

class MediaProcessor:
    
    @staticmethod
    def validar_imagem(url_imagem):
        if not url_imagem:
            return False
        
        try:
            response = requests.get(url_imagem, timeout=10)
            response.raise_for_status()
            
            imagem = Image.open(BytesIO(response.content))
            dados_imagem = np.array(imagem.convert("L"))
            
            if (np.sum(dados_imagem <= 15) / dados_imagem.size) * 100 > 95:
                logging.warning(f"[IMAGEM] Imagem ignorada: predominantemente preta.")
                return False
            
            return True
            
        except Exception as e:
            logging.warning(f"[IMAGEM] Falha ao analisar imagem {url_imagem}: {e}")
            return False
    
    @staticmethod
    def criar_imagem_post(titulo, url_imagem, categoria_ia):
        cfg = carregar_config()
        
        W, H = 1080, 1350
        
        fonte_path = os.path.join(BASE_DIR, "minha_fonte.ttf")
        img_final_path = os.path.join(BASE_DIR, "post_gerado.png")
        
        try:
            img_fundo = Image.open(BytesIO(requests.get(url_imagem, timeout=10).content))
            img_fundo = img_fundo.convert("RGBA").resize((W, H))
        except Exception as e:
            logging.error(f"[IMAGEM] Falha ao carregar imagem {url_imagem}. Erro: {e}")
            return None
        
        overlay = Image.new('RGBA', (W, H), (0, 0, 0, int(255 * cfg["opacidade"])))
        base = Image.alpha_composite(img_fundo, overlay)
        
        try:
            overlay_personalizado = Image.open(os.path.join(BASE_DIR, "overlay.png"))
            overlay_personalizado = overlay_personalizado.convert("RGBA").resize((W, H))
            base = Image.alpha_composite(base, overlay_personalizado)
        except FileNotFoundError:
            pass
        
        draw = ImageDraw.Draw(base)
        M_ESQ, M_DIR, V_INI = 110, 110, H * 0.60
        caixa_w = W - M_ESQ - M_DIR
        caixa_h = H - V_INI - 50
        
        fonte_categoria = ImageFont.truetype(fonte_path, 32)
        categoria_texto = f"#{categoria_ia.upper()}"
        _, _, cat_w, cat_h = draw.textbbox((0, 0), categoria_texto, font=fonte_categoria)
        
        espacamento_cat_titulo = 25
        caixa_h_titulo = caixa_h - cat_h - espacamento_cat_titulo
        
        tamanho_fonte = 52
        texto_fmt = titulo
        
        while tamanho_fonte >= 36:
            fonte = ImageFont.truetype(fonte_path, tamanho_fonte)
            char_w = fonte.getbbox('a')[2]
            chars_linha = int(caixa_w / char_w) if char_w > 0 else 1
            texto_fmt = "\n".join(textwrap.wrap(titulo, width=chars_linha))
            _, _, w, h = draw.textbbox((0, 0), texto_fmt, font=fonte)
            
            if w <= caixa_w and h <= caixa_h_titulo:
                break
            tamanho_fonte -= 2
        
        pos_cat_y = V_INI + (caixa_h - (cat_h + espacamento_cat_titulo + h)) / 2
        draw.text((M_ESQ, pos_cat_y), categoria_texto, font=fonte_categoria, fill="white", align="left")
        
        pos_y_titulo = pos_cat_y + cat_h + espacamento_cat_titulo
        draw.text((M_ESQ, pos_y_titulo), texto_fmt, font=fonte, fill="white", align="left")
        
        base.convert("RGB").save(img_final_path)
        return img_final_path