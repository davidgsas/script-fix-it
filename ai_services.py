import google.generativeai as genai
import logging
import re
from config import PRECO_INPUT_USD_1M_TOKENS, PRECO_OUTPUT_USD_1M_TOKENS, carregar_config

custo_sessao_atual = {"total_custo_usd": 0.0}

class AIServices:
    
    @staticmethod
    def _chamar_gemini(prompt, funcao_nome):
        cfg = carregar_config()
        
        if not cfg.get("google_api_key") or cfg.get("google_api_key") == "SUA_CHAVE_API_DO_GEMINI_AQUI":
            logging.warning(f"[IA] Chave do Gemini não configurada. Pulando '{funcao_nome}'.")
            return None, 0.0
        
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
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
        # Trata caso do conteúdo ser None ou vazio
        conteudo_texto = ""
        if conteudo and len(conteudo.strip()) > 0:
            conteudo_texto = conteudo[:300]
        else:
            conteudo_texto = "Conteúdo não disponível"
            
        prompt = f"""Você é um indexador de notícias da agência Reuters. Sua tarefa é ler um título e o início de um artigo e criar uma manchete canônica, factual e ultra-resumida (máximo 10 palavras) que capture a essência do evento.

O objetivo é que notícias de fontes diferentes sobre o MESMO evento resultem em manchetes canônicas IDÊNTICAS. Padronize termos (ex: 'EUA' e 'Estados Unidos' devem virar 'EUA'). Remova nomes de fontes e linguagem opinativa.

Retorne APENAS a manchete canônica.

Exemplo de Entrada 1: 'Neandertais: Descoberta na Alemanha uma fábrica de gordura de 125.000 anos'
Exemplo de Entrada 2: 'Fábrica de Gordura Pré-Histórica Operava Há 125.000 Anos em Lago Alemão'
Saída Esperada para Ambos: 'Descoberta fábrica de gordura Neandertal de 125.000 anos na Alemanha'

Título real: "{titulo}"
Início do conteúdo: "{conteudo_texto}..."

Manchete Canônica:"""
        
        titulo_canonico, custo = AIServices._chamar_gemini(prompt, "Título Canônico")
        return titulo_canonico, custo
    
    @staticmethod
    def filtrar_relevancia(titulo, conteudo):
        # Trata caso do conteúdo ser None ou vazio
        conteudo_texto = ""
        if conteudo and len(conteudo.strip()) > 0:
            conteudo_texto = conteudo[:700]
        else:
            conteudo_texto = "Conteúdo não disponível"
            
        prompt = f"""Você é um editor de pauta sênior, extremamente criterioso e cético. Sua função é analisar o título e o conteúdo de um artigo para determinar se é uma notícia genuína ou se é conteúdo promocional, marketing, 'caça-cliques' ou de baixo valor jornalístico.

REPROVE o conteúdo se ele se encaixar em qualquer uma destas categorias:

Anúncios, publieditoriais ou marketing disfarçado de notícia.

Venda ou sugestão explícita de cursos, webinars, e-books ou produtos.

Listas de "dicas" ou "curiosidades" de baixo impacto (ex: '5 formas de limpar seu celular', 'o segredo para descascar um ovo').

Notícias "bestas", fofocas de celebridades ou entretenimento de baixo valor que não se encaixam em editorias sérias.

Resultados de loteria, horóscopo, ou conteúdo sobre sorte e previsões.

Artigos de opinião pessoal sem base em fatos concretos.

Qualquer noticia que nao seja de jogos extremamente conhecidos como GTA.

APROVE apenas se for uma notícia genuína sobre:

Eventos globais ou nacionais significativos.

Anúncios de produtos ou tecnologias de grandes empresas (ex: Apple, Google, NASA).

Descobertas científicas ou avanços médicos importantes.

Análises sobre o mercado financeiro e economia.

Resultados e eventos de esportes relevantes.

Responda APENAS com APROVADA ou REPROVADA.

Texto:
---
Título: {titulo}
Conteúdo: {conteudo_texto}...
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
        if not texto:
            return texto, 0.0
            
        prompt = f"""Traduza o seguinte texto de {idioma_original} para o Português do Brasil, mantendo o sentido e o tom jornalístico. 

Retorne apenas o texto traduzido:

{texto}"""
        
        traducao, custo = AIServices._chamar_gemini(prompt, "Tradução")
        return traducao or texto, custo
    
    @staticmethod
    def reescrever_legenda(texto_original):
        if not texto_original:
            return texto_original, 0.0
            
        prompt = f"""Aja como um copywriter sênior da página @noticiasbr.ai. Sua tarefa é transformar o artigo de notícia a seguir em uma legenda de Instagram magnética e de fácil leitura.

O formato da sua resposta deve ser EXATAMENTE: um parágrafo de resumo (máx 250 palavras) seguido do marcador especial `|||` e depois um gancho final (uma frase ou pergunta curta e provocativa).

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
        # Trata caso do conteúdo ser None ou vazio
        conteudo_texto = ""
        if conteudo and len(conteudo.strip()) > 0:
            conteudo_texto = conteudo
        else:
            conteudo_texto = "Conteúdo não disponível"
            
        prompt = f"""Você é um classificador de conteúdo especialista. Sua tarefa é ler o título e o conteúdo de uma notícia e classificá-la na categoria mais apropriada de uma lista pré-definida.

A lista de categorias permitidas é: Política, Economia, Ciência, IA, Tecnologia, Educação, Saúde, Governo, Mundo, Guerra.

Analise o texto e retorne APENAS o nome de UMA categoria da lista. Se nenhuma se encaixar perfeitamente, escolha a mais próxima ou 'Mundo'.

Retorne APENAS o nome da categoria.

Texto:
Título: "{titulo}"
Conteúdo: "{conteudo_texto}"

Categoria:"""
        
        categoria, custo = AIServices._chamar_gemini(prompt, "Categorização")
        return categoria or "Geral", custo
    
    @staticmethod
    def gerar_hashtags(texto_para_seo):
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