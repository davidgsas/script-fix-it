#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("🚀 INICIANDO BOT DE INSTAGRAM...")

import os
import sys
import getpass
import logging

# Força output imediato
sys.stdout.flush()

print("📦 Importando módulos...")

try:
    from config import carregar_config, salvar_config, setup_logging
    print("✅ Config importado")
    
    from database import setup_database, Database
    print("✅ Database importado")
    
    from ai_services import AIServices, custo_sessao_atual
    print("✅ AI Services importado")
    
    from news_apis import NewsAPIs
    print("✅ News APIs importado")
    
    from instagram import InstagramManager
    print("✅ Instagram importado")
    
    from media import MediaProcessor
    print("✅ Media importado")
    
except Exception as e:
    print(f"❌ ERRO no import: {e}")
    sys.exit(1)

print("⚙️ Configurando logging...")
setup_logging()

print("📊 Configurando banco de dados...")
setup_database()

print("🔧 Carregando configurações...")
config = carregar_config()

print(f"📋 Status das configurações:")
print(f"   - insta_user: {'✅' if config.get('insta_user') else '❌'}")
print(f"   - gnews_api_key: {'✅' if config.get('gnews_api_key') else '❌'}")

if not config.get("insta_user") or not config.get("gnews_api_key"):
    print("\n🔑 CONFIGURAÇÕES NECESSÁRIAS:")
    print("Precisamos configurar as APIs e credenciais...")
    
    config["insta_user"] = input("👤 Usuário do Instagram: ")
    config["insta_pass"] = getpass.getpass("🔑 Senha do Instagram: ")
    config["gnews_api_key"] = input("📰 Chave da API GNews: ")
    config["newsdata_api_key"] = input("📊 Chave da API NewsData.io: ")
    config["google_api_key"] = input("✨ Chave da API Google Gemini: ")
    
    salvar_config(config)
    print("✅ Configurações salvas!")

print("\n🎯 Todas as configurações prontas!")
print("🌐 Servidor será iniciado em http://127.0.0.1:8080")
print("✨ Bot de Instagram configurado com sucesso!")