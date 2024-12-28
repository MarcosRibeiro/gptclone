# Configurações do Projeto ChatGPT Clone
import os  # Adicione esta linha no topo do arquivo

# Chave da API do Gemini (obrigatória se for usar o Gemini)
GEMINI_API_KEY = "AIzaSyA6aznuCF0QX1rCH_uUAYc1yBZmNgL9Jqg"

# Chave da API do GPT-4 (obrigatória se for usar o GPT-4)
OPENAI_API_KEY = ""

# Configurações do Banco de Dados
DB_HOST = "127.0.0.1"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "chatgpt_clone"
DB_PORT = 3306

# Configurações do Aplicativo Flask
SECRET_KEY = os.urandom(24).hex()  # Agora vai funcionar, pois 'os' está importado