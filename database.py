# -*- coding: utf-8 -*-
import sqlite3
import uuid
import logging
from collections import deque
from config import DB_PATH

def get_db_connection():
    """Cria conexão com o banco de dados"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Cria as tabelas necessárias"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela da fila de postagem
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fila_postagem (
            id TEXT PRIMARY KEY,
            titulo_original TEXT,
            titulo_refinado TEXT NOT NULL,
            semantic_hash TEXT NOT NULL,
            descricao TEXT,
            conteudo_original TEXT,
            conteudo_reescrito TEXT,
            url_imagem TEXT,
            fonte TEXT,
            categoria_ia TEXT,
            idioma_original TEXT,
            api_fonte TEXT,
            custo_usd REAL,
            data_adicionado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(semantic_hash)
        )
    ''')
    
    # Tabela do histórico
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id TEXT PRIMARY KEY,
            titulo_original TEXT,
            titulo_refinado TEXT,
            semantic_hash TEXT,
            conteudo_original TEXT,
            conteudo_reescrito TEXT,
            idioma_original TEXT,
            api_fonte TEXT,
            status TEXT,
            motivo_rejeicao TEXT,
            custo_usd REAL,
            data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(semantic_hash)
        )
    ''')
    
    # Tabela de estatísticas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estatisticas (
            chave TEXT PRIMARY KEY,
            valor REAL
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO estatisticas (chave, valor) VALUES ('custo_total_vida', 0.0)")
    
    conn.commit()
    conn.close()
    logging.info("[SISTEMA] Banco de dados verificado e pronto.")

class Database:
    """Classe para operações do banco de dados"""
    
    @staticmethod
    def adicionar_na_fila(noticia):
        """Adiciona notícia na fila de postagem"""
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO fila_postagem (
                    id, titulo_original, titulo_refinado, semantic_hash, descricao,
                    conteudo_original, conteudo_reescrito, url_imagem, fonte,
                    categoria_ia, idioma_original, api_fonte, custo_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()), noticia['titulo_original'], noticia['titulo_refinado'],
                noticia['semantic_hash'], noticia.get('descricao', ''), noticia['conteudo_original'],
                noticia['conteudo_reescrito'], noticia['url_imagem'], noticia['fonte'],
                noticia['categoria_ia'], noticia['idioma_original'], noticia['api_fonte'],
                noticia['custo_usd']
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Duplicata - ignora
        finally:
            conn.close()
    
    @staticmethod
    def registrar_no_historico(noticia, status, motivo=''):
        """Registra notícia no histórico"""
        conn = get_db_connection()
        custo = noticia.get('custo_usd', 0.0)
        
        try:
            conn.execute('''
                INSERT INTO historico (
                    id, titulo_original, titulo_refinado, semantic_hash,
                    conteudo_original, conteudo_reescrito, idioma_original,
                    api_fonte, status, motivo_rejeicao, custo_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()), noticia.get('titulo_original'), noticia.get('titulo_refinado'),
                noticia.get('semantic_hash'), noticia.get('conteudo_original'),
                noticia.get('conteudo_reescrito'), noticia.get('idioma_original'),
                noticia.get('api_fonte'), status, motivo, custo
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            # Atualiza custo total
            conn.execute("UPDATE estatisticas SET valor = valor + ? WHERE chave = 'custo_total_vida'", (custo,))
            conn.commit()
            conn.close()
    
    @staticmethod
    def verificar_duplicata_semantica(semantic_hash):
        """Verifica se já existe notícia com mesmo hash semântico"""
        if not semantic_hash:
            return True
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verifica no histórico
        cursor.execute("SELECT 1 FROM historico WHERE semantic_hash = ?", (semantic_hash,))
        if cursor.fetchone():
            conn.close()
            return True
        
        # Verifica na fila
        cursor.execute("SELECT 1 FROM fila_postagem WHERE semantic_hash = ?", (semantic_hash,))
        if cursor.fetchone():
            conn.close()
            return True
            
        conn.close()
        return False
    
    @staticmethod
    def obter_custo_total():
        """Obtém custo total acumulado"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM estatisticas WHERE chave = 'custo_total_vida'")
        res = cursor.fetchone()
        conn.close()
        return res['valor'] if res else 0.0
    
    @staticmethod
    def limpar_fila():
        """Remove todos os itens da fila"""
        conn = get_db_connection()
        conn.execute("DELETE FROM fila_postagem")
        conn.commit()
        conn.close()
    
    @staticmethod
    def remover_da_fila(item_id):
        """Remove item específico da fila"""
        conn = get_db_connection()
        conn.execute("DELETE FROM fila_postagem WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def pegar_proximo_da_fila():
        """Pega próximo item da fila"""
        conn = get_db_connection()
        item = conn.execute("SELECT * FROM fila_postagem ORDER BY data_adicionado ASC LIMIT 1").fetchone()
        conn.close()
        return dict(item) if item else None
    
    @staticmethod
    def pegar_fila_completa():
        """Retorna toda a fila de postagem"""
        conn = get_db_connection()
        fila = [dict(row) for row in conn.execute('''
            SELECT id, titulo_refinado as titulo, categoria_ia, api_fonte 
            FROM fila_postagem ORDER BY data_adicionado ASC
        ''').fetchall()]
        conn.close()
        return fila
    
    @staticmethod
    def pegar_historico_completo():
        """Retorna histórico completo"""
        conn = get_db_connection()
        historico = [dict(row) for row in conn.execute('''
            SELECT *, STRFTIME('%d/%m/%Y %H:%M', data_processamento) as data_formatada 
            FROM historico ORDER BY data_processamento DESC LIMIT 100
        ''').fetchall()]
        conn.close()
        return historico
    
    @staticmethod
    def pegar_log_recente():
        """Pega log recente do arquivo"""
        try:
            with open('bot.log', 'r', encoding='utf-8') as f:
                return deque(f, 30)
        except FileNotFoundError:
            return []
    
    @staticmethod
    def pegar_titulos_recentes():
        """Pega títulos recentes da fila"""
        conn = get_db_connection()
        titulos = [row['titulo_refinado'] for row in conn.execute('''
            SELECT titulo_refinado FROM fila_postagem 
            ORDER BY data_adicionado DESC LIMIT 15
        ''').fetchall()]
        conn.close()
        return titulos