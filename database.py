import sqlite3
import uuid
import logging
from collections import deque
from config import DB_PATH, get_agent_db_path

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
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
    """)
    
    cursor.execute("""
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
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estatisticas (
            chave TEXT PRIMARY KEY,
            valor REAL
        )
    """)
    
    cursor.execute("INSERT OR IGNORE INTO estatisticas (chave, valor) VALUES ('custo_total_vida', 0.0)")
    
    conn.commit()
    conn.close()
    logging.info("[SISTEMA] Banco de dados verificado e pronto.")

class Database:
    
    @staticmethod
    def adicionar_na_fila(noticia):
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO fila_postagem (
                    id, titulo_original, titulo_refinado, semantic_hash, descricao,
                    conteudo_original, conteudo_reescrito, url_imagem, fonte,
                    categoria_ia, idioma_original, api_fonte, custo_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), noticia['titulo_original'], noticia['titulo_refinado'],
                noticia['semantic_hash'], noticia.get('descricao', ''), noticia['conteudo_original'],
                noticia['conteudo_reescrito'], noticia['url_imagem'], noticia['fonte'],
                noticia['categoria_ia'], noticia['idioma_original'], noticia['api_fonte'],
                noticia['custo_usd']
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()
    
    @staticmethod
    def registrar_no_historico(noticia, status, motivo=''):
        conn = get_db_connection()
        custo = noticia.get('custo_usd', 0.0)
        
        try:
            conn.execute("""
                INSERT INTO historico (
                    id, titulo_original, titulo_refinado, semantic_hash,
                    conteudo_original, conteudo_reescrito, idioma_original,
                    api_fonte, status, motivo_rejeicao, custo_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), noticia.get('titulo_original'), noticia.get('titulo_refinado'),
                noticia.get('semantic_hash'), noticia.get('conteudo_original'),
                noticia.get('conteudo_reescrito'), noticia.get('idioma_original'),
                noticia.get('api_fonte'), status, motivo, custo
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.execute("UPDATE estatisticas SET valor = valor + ? WHERE chave = 'custo_total_vida'", (custo,))
            conn.commit()
            conn.close()
    
    @staticmethod
    def verificar_duplicata_semantica(semantic_hash):
        if not semantic_hash:
            return True
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM historico WHERE semantic_hash = ?", (semantic_hash,))
        if cursor.fetchone():
            conn.close()
            return True
        
        cursor.execute("SELECT 1 FROM fila_postagem WHERE semantic_hash = ?", (semantic_hash,))
        if cursor.fetchone():
            conn.close()
            return True
            
        conn.close()
        return False
    
    @staticmethod
    def obter_custo_total():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM estatisticas WHERE chave = 'custo_total_vida'")
        res = cursor.fetchone()
        conn.close()
        return res['valor'] if res else 0.0
    
    @staticmethod
    def limpar_fila():
        conn = get_db_connection()
        conn.execute("DELETE FROM fila_postagem")
        conn.commit()
        conn.close()
    
    @staticmethod
    def remover_da_fila(item_id):
        conn = get_db_connection()
        conn.execute("DELETE FROM fila_postagem WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def pegar_proximo_da_fila():
        conn = get_db_connection()
        item = conn.execute("SELECT * FROM fila_postagem ORDER BY data_adicionado ASC LIMIT 1").fetchone()
        conn.close()
        return dict(item) if item else None
    
    @staticmethod
    def pegar_fila_completa():
        conn = get_db_connection()
        fila = [dict(row) for row in conn.execute("""
            SELECT id, titulo_refinado as titulo, categoria_ia, api_fonte 
            FROM fila_postagem ORDER BY data_adicionado ASC
        """).fetchall()]
        conn.close()
        return fila
    
    @staticmethod
    def pegar_historico_completo():
        conn = get_db_connection()
        historico = [dict(row) for row in conn.execute("""
            SELECT *, STRFTIME('%d/%m/%Y %H:%M', data_processamento) as data_formatada 
            FROM historico ORDER BY data_processamento DESC LIMIT 100
        """).fetchall()]
        conn.close()
        return historico
    
    @staticmethod
    def pegar_log_recente():
        try:
            with open('bot.log', 'r', encoding='utf-8') as f:
                return deque(f, 30)
        except FileNotFoundError:
            return []
    
    @staticmethod
    def pegar_titulos_recentes():
        conn = get_db_connection()
        titulos = [row['titulo_refinado'] for row in conn.execute("""
            SELECT titulo_refinado FROM fila_postagem 
            ORDER BY data_adicionado DESC LIMIT 15
        """).fetchall()]
        conn.close()
        return titulos
    
    @staticmethod
    def verificar_titulo_duplicado(titulo_original):
        """Verifica se um título similar já existe na fila ou histórico"""
        if not titulo_original:
            return True
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Busca na fila primeiro
        cursor.execute("SELECT titulo_original FROM fila_postagem WHERE titulo_original = ?", (titulo_original,))
        if cursor.fetchone():
            conn.close()
            return True
        
        # Busca no histórico
        cursor.execute("SELECT titulo_original FROM historico WHERE titulo_original = ?", (titulo_original,))
        if cursor.fetchone():
            conn.close()
            return True
            
        conn.close()
        return False
    
    # === MÉTODOS PARA MULTI-AGENTES ===
    
    @staticmethod
    def setup_database_for_agent(agent_id, db_path):
        """Configura banco de dados específico para um agente"""
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
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
                pasta_feed TEXT,
                custo_usd REAL,
                data_adicionado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(semantic_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id TEXT PRIMARY KEY,
                titulo_original TEXT,
                titulo_refinado TEXT,
                semantic_hash TEXT,
                conteudo_original TEXT,
                conteudo_reescrito TEXT,
                idioma_original TEXT,
                api_fonte TEXT,
                pasta_feed TEXT,
                status TEXT,
                motivo_rejeicao TEXT,
                custo_usd REAL,
                data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(semantic_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estatisticas (
                chave TEXT PRIMARY KEY,
                valor REAL
            )
        """)
        
        cursor.execute("INSERT OR IGNORE INTO estatisticas (chave, valor) VALUES ('custo_total_vida', 0.0)")
        
        conn.commit()
        conn.close()
        logging.info(f"[AGENT-{agent_id}] Banco de dados configurado: {db_path}")
    
    @staticmethod
    def get_agent_connection(agent_id):
        """Retorna conexão com banco específico do agente"""
        db_path = get_agent_db_path(agent_id)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def adicionar_na_fila_agente(agent_id, noticia):
        """Adiciona notícia na fila específica do agente"""
        conn = Database.get_agent_connection(agent_id)
        try:
            conn.execute("""
                INSERT INTO fila_postagem (
                    id, titulo_original, titulo_refinado, semantic_hash, descricao,
                    conteudo_original, conteudo_reescrito, url_imagem, fonte,
                    categoria_ia, idioma_original, api_fonte, pasta_feed, custo_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), noticia['titulo_original'], noticia['titulo_refinado'],
                noticia['semantic_hash'], noticia.get('descricao', ''), noticia['conteudo_original'],
                noticia['conteudo_reescrito'], noticia['url_imagem'], noticia['fonte'],
                noticia['categoria_ia'], noticia['idioma_original'], noticia['api_fonte'],
                noticia.get('pasta_feed', 'geral'), noticia['custo_usd']
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()
    
    @staticmethod
    def registrar_no_historico_agente(agent_id, noticia, status, motivo=''):
        """Registra no histórico específico do agente"""
        conn = Database.get_agent_connection(agent_id)
        custo = noticia.get('custo_usd', 0.0)
        
        try:
            conn.execute("""
                INSERT INTO historico (
                    id, titulo_original, titulo_refinado, semantic_hash,
                    conteudo_original, conteudo_reescrito, idioma_original,
                    api_fonte, pasta_feed, status, motivo_rejeicao, custo_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), noticia.get('titulo_original'), noticia.get('titulo_refinado'),
                noticia.get('semantic_hash'), noticia.get('conteudo_original'),
                noticia.get('conteudo_reescrito'), noticia.get('idioma_original'),
                noticia.get('api_fonte'), noticia.get('pasta_feed', 'geral'), status, motivo, custo
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.execute("UPDATE estatisticas SET valor = valor + ? WHERE chave = 'custo_total_vida'", (custo,))
            conn.commit()
            conn.close()
    
    @staticmethod
    def verificar_titulo_duplicado_agente(agent_id, titulo_original):
        """Verifica título duplicado no agente específico"""
        if not titulo_original:
            return True
            
        conn = Database.get_agent_connection(agent_id)
        cursor = conn.cursor()
        
        cursor.execute("SELECT titulo_original FROM fila_postagem WHERE titulo_original = ?", (titulo_original,))
        if cursor.fetchone():
            conn.close()
            return True
        
        cursor.execute("SELECT titulo_original FROM historico WHERE titulo_original = ?", (titulo_original,))
        if cursor.fetchone():
            conn.close()
            return True
            
        conn.close()
        return False
    
    @staticmethod
    def verificar_duplicata_semantica_agente(agent_id, semantic_hash):
        """Verifica duplicata semântica no agente específico"""
        if not semantic_hash:
            return True
            
        conn = Database.get_agent_connection(agent_id)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM historico WHERE semantic_hash = ?", (semantic_hash,))
        if cursor.fetchone():
            conn.close()
            return True
        
        cursor.execute("SELECT 1 FROM fila_postagem WHERE semantic_hash = ?", (semantic_hash,))
        if cursor.fetchone():
            conn.close()
            return True
            
        conn.close()
        return False
    
    @staticmethod
    def pegar_proximo_da_fila_agente(agent_id):
        """Pega próximo item da fila do agente"""
        conn = Database.get_agent_connection(agent_id)
        item = conn.execute("SELECT * FROM fila_postagem ORDER BY data_adicionado ASC LIMIT 1").fetchone()
        conn.close()
        return dict(item) if item else None
    
    @staticmethod
    def pegar_item_fila_agente(agent_id, item_id):
        """Pega item específico da fila do agente"""
        conn = Database.get_agent_connection(agent_id)
        item = conn.execute("SELECT * FROM fila_postagem WHERE id = ?", (item_id,)).fetchone()
        conn.close()
        return dict(item) if item else None
    
    @staticmethod
    def pegar_fila_completa_agente(agent_id):
        """Pega fila completa do agente"""
        conn = Database.get_agent_connection(agent_id)
        fila = [dict(row) for row in conn.execute("""
            SELECT id, titulo_refinado as titulo, categoria_ia, api_fonte, pasta_feed
            FROM fila_postagem ORDER BY data_adicionado ASC
        """).fetchall()]
        conn.close()
        return fila
    
    @staticmethod
    def remover_da_fila_agente(agent_id, item_id):
        """Remove item da fila do agente"""
        conn = Database.get_agent_connection(agent_id)
        conn.execute("DELETE FROM fila_postagem WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def pegar_historico_agente(agent_id):
        """Pega histórico do agente"""
        conn = Database.get_agent_connection(agent_id)
        historico = [dict(row) for row in conn.execute("""
            SELECT *, STRFTIME('%d/%m/%Y %H:%M', data_processamento) as data_formatada 
            FROM historico ORDER BY data_processamento DESC LIMIT 100
        """).fetchall()]
        conn.close()
        return historico