# -*- coding: utf-8 -*-
import google.generativeai as genai
import logging
import re
from config import PRECO_INPUT_USD_1M_TOKENS, PRECO_OUTPUT_USD_1M_TOKENS, carregar_config

# Contador de custo da sessão atual
custo_sessao_atual = {"total_custo_usd": 0.0}

class AIServices:
    """Serviços de IA usando Google Gemini"""
    
    @staticmethod
    def _chamar_gemini(prompt, funcao_nome):
        """Chama a API do Gemini e calcula custos"""
        cfg = carregar_config()
        
        if not cfg.get("google_api_key") or cfg.get("google_api_key") == "SUA_CHAVE_API_DO_GEMINI_AQUI":
            logging.warning(f"[IA] Chave do Gemini não configurada. Pulando '{funcao_nome}'.")
            return None, 0.0
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            custo_usd = 0.0
            
            if hasattr(response, 'usage_metadata'):
                tokens_in = response.usage_metadata.prompt_token_count
                tokens_out = response.usage_metadata.candidates_token_count
                custo_in = (tokens_in / 1_000_000) * PRECO_INPUT_USD_1M_TOKENS
                custo_out = (tokens_out / 1_000_000) * PRECO_OUTPUT_USD_1M_TOKENS
                custo_usd = custo_in + custo_out
                custo_sessao_atual["total_custo_usd"] += custo_usd
            
            return response.text.strip(), custo_usd
            
        except Exception as e:
            logging.error(f"[IA ERRO] Falha ao chamar Gemini em '{funcao_nome}': {e}.")
            return None, 0.0
    
    @staticmethod
    def gerar_titulo_canonico(titulo, conteudo):
        """Gera título canônico para detecção de duplicatas"""
        prompt = f"""Você é um indexador de notícias da agência Reuters. Sua tarefa é ler um título e o início de um artigo e criar uma manchete canônica, factual e ultra-resumida (máximo 10 palavras) que capture a essência do evento.

O objetivo é que notícias de fontes diferentes sobre o MESMO evento resultem em manchetes canônicas IDÊNTICAS. Padronize termos (ex: 'EUA' e 'Estados Unidos' devem virar 'EUA'). Remova nomes de fontes e linguagem opinativa.

Retorne APENAS a manchete canônica.

Exemplo de Entrada 1: 'Neandertais: Descoberta na Alemanha uma fábrica de gordura de 125.000 anos'
Exemplo de Entrada 2: 'Fábrica de Gordura Pré-Histórica Operava Há 125.000 Anos em Lago Alemão'
Saída Esperada para Ambos: 'Descoberta fábrica de gordura Neandertal de 125.000 anos na Alemanha'

Título real: "{titulo}"
Início do conteúdo: "{conteudo[:300]}..."

Manchete Canônica:"""
        
        titulo_canonico, custo = AIServices._chamar_gemini(prompt, "Título Canônico")
        return titulo_canonico, custo
    
    @staticmethod
    def filtrar_relevancia(titulo, conteudo):
        """Filtra se a notícia é relevante ou spam/marketing"""
        prompt = f"""Você é um editor de pauta sênior e cético. Analise o título e o conteúdo para determinar se é uma notícia genuína ou conteúdo promocional/marketing/caça-cliques.

REPROVE conteúdo de baixo valor. APROVE apenas notícias relevantes.

Responda APENAS com APROVADA ou REPROVADA.

Texto:
---
Título: {titulo}
Conteúdo: {conteudo[:700]}...
---

Veredito:"""
        
        veredito, custo = AIServices._chamar_gemini(prompt, "Filtro de Relevância")
        
        if veredito not in ["APROVADA", "REPROVADA"]:
            logging.warning("[IA - Filtro] Resposta inesperada. Reprovando por segurança.")
            return "REPROVADA", custo
        
        logging.info(f"[IA - Filtro] Veredito para '{titulo[:50]}...': {veredito}")
        return veredito, custo
    
    @staticmethod
    def traduzir_texto(texto, idioma_original='Inglês'):
        """Traduz texto para português"""
        if not texto:
            return texto, 0.0
            
        prompt = f"""Traduza o seguinte texto de {idioma_original} para o Português do Brasil, mantendo o sentido e o tom jornalístico. 

Retorne apenas o texto traduzido:

{texto}"""
        
        traducao, custo = AIServices._chamar_gemini(prompt, "Tradução")
        return traducao or texto, custo
    
    @staticmethod
    def reescrever_legenda(texto_original):
        """Reescreve texto como legenda do Instagram"""
        if not texto_original:
            return texto_original, 0.0
            
        prompt = f"""Aja como um copywriter sênior da página @noticiasbr.ai. Sua tarefa é transformar o artigo de notícia a seguir em uma legenda de Instagram magnética e de fácil leitura.

O formato da sua resposta deve ser EXATAMENTE: um parágrafo de resumo (máx 100 palavras) seguido do marcador especial `|||` e depois um gancho final (uma frase ou pergunta curta e provocativa).

NUNCA use marcadores como '1.' ou '-'.

Exemplo: Notícia sobre o iPhone.|||E você, vai atualizar?

Texto original:
---
{texto_original}
---

Texto reescrito:"""
        
        response_text, custo = AIServices._chamar_gemini(prompt, "Reescrita de Legenda")
        
        if response_text:
            partes = response_text.split('|||')
            if len(partes) == 2:
                resumo = re.sub(r'^\s*[\d\.\-\*]+\s*', '', partes[0].strip())
                gancho = re.sub(r'^\s*[\d\.\-\*]+\s*', '', partes[1].strip())
                texto_formatado = f"{resumo}\n\n{gancho}"
            else:
                texto_formatado = re.sub(r'^\s*[\d\.\-\*]+\s*', '', response_text)
            return texto_formatado, custo
        
        return texto_original, 0.0
    
    @staticmethod
    def melhorar_titulo(titulo_original):
        """Refina o título da notícia"""
        if not titulo_original:
            return titulo_original, 0.0
            
        prompt = f"""Refine o título de notícia a seguir para ser claro e atraente, corrigindo pontuações estranhas.

Retorne APENAS o título refinado.

Título original: "{titulo_original}"

Título refinado:"""
        
        titulo_refinado, custo = AIServices._chamar_gemini(prompt, "Refinamento de Título")
        return titulo_refinado.replace('"', '') if titulo_refinado else titulo_original, custo
    
    @staticmethod
    def categorizar_noticia(titulo, conteudo):
        """Categoriza a notícia"""
        prompt = f"""Você é um classificador de conteúdo especialista. Sua tarefa é ler o título e o conteúdo de uma notícia e criar uma categoria concisa e específica para ela, com no máximo duas palavras.

Exemplo: 'Fórmula 1', 'Inteligência Artificial', 'Cinema', 'Mercado Financeiro', 'Política Nacional'.

Retorne APENAS o nome da categoria.

Texto:
Título: "{titulo}"
Conteúdo: "{conteudo}"

Categoria:"""
        
        categoria, custo = AIServices._chamar_gemini(prompt, "Categorização")
        return categoria or "Geral", custo
    
    @staticmethod
    def gerar_hashtags(texto_para_seo):
        """Gera hashtags relevantes"""
        if not texto_para_seo:
            return "", 0.0
            
        prompt = f"""Você é um especialista em SEO para Instagram. Leia o texto e gere as 3 hashtags mais relevantes em português do Brasil.

Não use hashtags genéricas como #noticia ou #brasil. Foque nos temas específicos.

Retorne APENAS as 3 hashtags separadas por espaço, começando com #.

Exemplo: #inteligenciaartificial #tecnologia #inovacao

Texto base:
---
{texto_para_seo}
---

Hashtags:"""
        
        hashtags, custo = AIServices._chamar_gemini(prompt, "Geração de Hashtags")
        return hashtags or "", custo