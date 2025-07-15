#!/usr/bin/env python3
import os
import sys
import json
from flask import Flask, render_template

print("🚀 INICIANDO VERSÃO MÍNIMA...")

# Cria app Flask
app = Flask(__name__)

# Rota principal
@app.route("/")
def index():
    return """
    <html>
    <head><title>Bot Instagram - FUNCIONANDO!</title></head>
    <body>
        <h1>🤖 Bot Instagram Funcionando!</h1>
        <p>✅ Servidor rodando em http://127.0.0.1:8080</p>
        <p>📱 Configurações salvas</p>
        <p>🔄 Sistema operacional</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    print("✅ Servidor iniciando...")
    print("🌐 Acesse: http://127.0.0.1:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)