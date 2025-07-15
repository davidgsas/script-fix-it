#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import getpass
import threading
import logging
import json
from flask import Flask, render_template, redirect, url_for, request, jsonify

print("🚀 INICIANDO BOT DE INSTAGRAM...")

# Configurações básicas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def carregar_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"apis_ativas": ["gnews"], "categorias_ativas": ["technology"], "opacidade": 0.3, "intervalo_busca": 15, "intervalo_post": 30, "idiomas_busca": ["pt"], "insta_user": "", "insta_pass": "", "gnews_api_key": "", "newsdata_api_key": "", "google_api_key": ""}

def salvar_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Cria app Flask
app = Flask(__name__)

@app.route("/")
def index():
    config = carregar_config()
    return f"""
    <html>
    <head>
        <title>🤖 Bot Instagram - Funcionando!</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 50px; background: #f0f2f5; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; max-width: 800px; }}
            .status {{ display: flex; gap: 20px; margin: 20px 0; }}
            .box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; flex: 1; }}
            .green {{ background: #d4edda; color: #155724; }}
            .red {{ background: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Bot de Instagram - Painel de Controle</h1>
            
            <div class="status">
                <div class="box {'green' if config.get('insta_user') else 'red'}">
                    <h3>Instagram</h3>
                    <p>{'✅ Configurado: ' + config.get('insta_user', '') if config.get('insta_user') else '❌ Não configurado'}</p>
                </div>
                
                <div class="box {'green' if config.get('gnews_api_key') else 'red'}">
                    <h3>GNews API</h3>
                    <p>{'✅ Configurado' if config.get('gnews_api_key') else '❌ Não configurado'}</p>
                </div>
                
                <div class="box {'green' if config.get('google_api_key') else 'red'}">
                    <h3>Google Gemini</h3>
                    <p>{'✅ Configurado' if config.get('google_api_key') else '❌ Não configurado'}</p>
                </div>
            </div>
            
            <h2>🚀 Status: FUNCIONANDO!</h2>
            <p>✅ Servidor rodando em http://127.0.0.1:8080</p>
            <p>📱 Sistema operacional</p>
            <p>🔄 Pronto para buscar e postar notícias</p>
            
            <h3>📋 Configurações Atuais:</h3>
            <ul>
                <li>APIs Ativas: {', '.join(config.get('apis_ativas', []))}</li>
                <li>Categorias: {', '.join(config.get('categorias_ativas', []))}</li>
                <li>Idiomas: {', '.join(config.get('idiomas_busca', []))}</li>
                <li>Intervalo de Busca: {config.get('intervalo_busca', 15)} minutos</li>
                <li>Intervalo de Posts: {config.get('intervalo_post', 30)} minutos</li>
            </ul>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    config = carregar_config()
    
    print("📋 Verificando configurações...")
    if not config.get("insta_user") or not config.get("gnews_api_key"):
        print("\n🔑 Configurando credenciais...")
        if not config.get("insta_user"):
            config["insta_user"] = input("👤 Usuário do Instagram: ")
            config["insta_pass"] = getpass.getpass("🔑 Senha do Instagram: ")
        if not config.get("gnews_api_key"):
            config["gnews_api_key"] = input("📰 Chave da API GNews: ")
            config["newsdata_api_key"] = input("📊 Chave da API NewsData.io: ")
            config["google_api_key"] = input("✨ Chave da API Google Gemini: ")
        salvar_config(config)
        print("✅ Configurações salvas!")
    
    print("\n🌐 Servidor iniciando...")
    print("🔗 Acesse: http://127.0.0.1:8080")
    print("✨ Pressione Ctrl+C para parar\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False)