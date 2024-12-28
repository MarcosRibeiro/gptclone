import os
import subprocess
import sys
import mysql.connector
from mysql.connector import errorcode
import logging
import socket

# --- Configurações ---
PROJECT_NAME = "."  # Usar o diretório atual como raiz do projeto
DB_NAME = "chatgpt_clone"
DB_USER = "root"
DB_PASSWORD = ""
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DEFAULT_PORT = 8000
BACKUP_PORT = 5000

# --- Configuração de Logging ---
logging.basicConfig(
    filename='setup.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Funções Auxiliares ---

def create_directory(path):
    """Cria um diretório se ele não existir."""
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Diretório criado: {path}")

def create_file(path, content=""):
    """Cria um arquivo se ele não existir, com a codificação UTF-8."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Arquivo criado: {path}")

def install_dependencies(requirements_file):
    """Instala as dependências listadas no arquivo requirements.txt."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        logger.info("Dependências instaladas com sucesso.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao instalar dependências: {e}")
        sys.exit(1)

def get_api_keys():
    """
    Obtém as chaves de API do Gemini e GPT-4.
    Verifica se as chaves já estão definidas no config.py antes de pedir ao usuário.
    """
    gemini_key = ""
    gpt_key = ""

    # Tenta carregar as chaves do config.py
    try:
        from config import GEMINI_API_KEY, OPENAI_API_KEY
        gemini_key = GEMINI_API_KEY
        gpt_key = OPENAI_API_KEY
    except ImportError:
        pass  # Se o arquivo não existir ou as chaves não estiverem lá, não tem problema

    print("Bem-vindo ao instalador do ChatGPT Clone!")

    # Só pede a chave do Gemini se ela ainda não estiver definida
    if not gemini_key:
        print("Por favor, insira sua chave da API do Gemini (ou deixe em branco).")
        gemini_key = input("Insira a sua chave da API do Gemini (ou deixe em branco): ").strip()
    else:
        print("Chave da API do Gemini já configurada (config.py).")

    # Só pede a chave do GPT se ela ainda não estiver definida
    if not gpt_key:
        print("Por favor, insira sua chave da API do GPT-4 (ou deixe em branco).")
        gpt_key = input("Insira a sua chave da API do GPT-4 (ou deixe em branco): ").strip()
    else:
        print("Chave da API do GPT-4 já configurada (config.py).")

    if not gemini_key and not gpt_key:
        print("Erro: Pelo menos uma chave de API (Gemini ou GPT-4) deve ser fornecida.")
        sys.exit(1)

    return gemini_key, gpt_key

def save_api_keys(gemini_key, gpt_key):
    """Salva as chaves de API no arquivo config.py."""

    # Define o conteúdo do config.py, usando as chaves existentes se disponíveis.
    config_content = f"""
# Configurações do Projeto ChatGPT Clone
import os

# Chave da API do Gemini (obrigatória se for usar o Gemini)
GEMINI_API_KEY = "{gemini_key if gemini_key is not None else ''}"

# Chave da API do GPT-4 (obrigatória se for usar o GPT-4)
OPENAI_API_KEY = "{gpt_key if gpt_key is not None else ''}"

# Configurações do Banco de Dados
DB_HOST = "{DB_HOST}"
DB_USER = "{DB_USER}"
DB_PASSWORD = "{DB_PASSWORD}"
DB_NAME = "{DB_NAME}"
DB_PORT = {DB_PORT}

# Configurações do Aplicativo Flask
SECRET_KEY = os.urandom(24).hex()  # Chave secreta gerada aleatoriamente e convertida para hexadecimal
"""
    create_file("config.py", config_content)

def check_mysql_connection():
    """Verifica se a conexão com o MySQL está funcionando."""
    try:
        mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        logger.info("Conexão com o MySQL bem-sucedida.")
    except mysql.connector.Error as err:
        logger.error(f"Erro ao conectar ao MySQL: {err}")
        print(f"Erro ao conectar ao MySQL: {err}")
        print("Certifique-se de que o WampServer está em execução e que as credenciais do banco de dados estão corretas.")
        sys.exit(1)

def database_exists():
    """Verifica se o banco de dados já existe."""
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        mycursor = mydb.cursor()
        mycursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        return mycursor.fetchone() is not None
    except mysql.connector.Error as err:
        logger.error(f"Erro ao verificar o banco de dados: {err}")
        print(f"Erro ao verificar o banco de dados: {err}")
        sys.exit(1)

def table_exists():
    """Verifica se a tabela 'conversations' existe no banco de dados."""
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        mycursor = mydb.cursor()
        mycursor.execute(f"SHOW TABLES LIKE 'conversations'")
        return mycursor.fetchone() is not None
    except mysql.connector.Error as err:
        logger.error(f"Erro ao verificar a tabela: {err}")
        print(f"Erro ao verificar a tabela: {err}")
        sys.exit(1)

def create_database_and_table():
    """Cria o banco de dados e a tabela 'conversations'."""
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        mycursor = mydb.cursor()

        mycursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"Banco de dados '{DB_NAME}' criado com sucesso.")

        mydb.database = DB_NAME
        mycursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255),
                user_message TEXT,
                gpt_response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_group DATE,
                model VARCHAR(50)
            )
        """)
        mydb.commit()
        logger.info("Tabela 'conversations' criada com sucesso.")
    except mysql.connector.Error as err:
        logger.error(f"Erro ao criar banco de dados e tabela: {err}")
        print(f"Erro ao criar banco de dados e tabela: {err}")
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Erro de acesso ao banco de dados. Verifique as credenciais do usuário.")
        else:
            print(f"Outro erro do MySQL: {err}")
        sys.exit(1)

def check_port(port):
    """Verifica se a porta especificada está em uso."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_flask_app(port):
    """Inicia o aplicativo Flask na porta especificada."""
    try:
        print(f"Iniciando o aplicativo na porta {port}...")
        # Usar PROJECT_NAME aqui, pois run.py está no diretório principal
        subprocess.Popen([sys.executable, f"{PROJECT_NAME}/run.py", str(port)])
        print(f"Aplicativo iniciado com sucesso. Acesse em http://localhost:{port}")
    except Exception as e:
        logger.error(f"Erro ao iniciar o aplicativo Flask: {e}")
        print(f"Erro ao iniciar o aplicativo Flask: {e}")
        sys.exit(1)

# --- Estrutura de Pastas e Arquivos ---

def create_project_structure():
    """Cria a estrutura de pastas e arquivos do projeto."""
    create_directory("app")
    create_directory("app/templates")
    create_directory("app/static")

    create_file("requirements.txt", """
flask
mysql-connector-python
openai
google-generativeai
""")

    create_file("app/__init__.py", f"""
from flask import Flask
import mysql.connector
from config import SECRET_KEY, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

app = Flask(__name__)
app.secret_key = SECRET_KEY

def get_db_connection():
    mydb = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )
    return mydb

from app import routes
""")

    create_file("app/models.py", """
from datetime import datetime
import mysql.connector
from app import get_db_connection
import google.generativeai as genai
import openai
from config import GEMINI_API_KEY, OPENAI_API_KEY

def save_conversation(user_id, user_message, gpt_response, model):
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        sql = "INSERT INTO conversations (user_id, user_message, gpt_response, date_group, model) VALUES (%s, %s, %s, %s, %s)"
        val = (user_id, user_message, gpt_response, datetime.now().date(), model)
        mycursor.execute(sql, val)
        mydb.commit()
        mydb.close()
    except mysql.connector.Error as err:
        print(f"Erro ao salvar conversa: {err}")

def load_conversations(user_id):
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT user_message, gpt_response, DATE(timestamp) as date_group FROM conversations WHERE user_id = %s ORDER BY timestamp ASC", (user_id,))
        conversations = mycursor.fetchall()
        mydb.close()
        return conversations
    except mysql.connector.Error as err:
        print(f"Erro ao carregar conversas: {err}")
        return []

def clear_conversations(user_id):
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        mycursor.execute("DELETE FROM conversations WHERE user_id = %s", (user_id,))
        mydb.commit()
        mydb.close()
    except mysql.connector.Error as err:
        print(f"Erro ao limpar histórico de conversas: {err}")

def enviar_mensagem_gemini(modelo, mensagem):
    try:
        resposta = modelo.generate_content(mensagem)
        return resposta.text
    except Exception as e:
        print(f"Erro ao enviar mensagem ao Gemini: {e}")
        return None

def enviar_mensagem_gpt(mensagem):
    try:
        if not OPENAI_API_KEY:
            raise Exception("Chave da API do GPT não configurada.")
        openai.api_key = OPENAI_API_KEY
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": mensagem}
            ]
        )
        resposta_texto = resposta.choices[0].message.content
        return resposta_texto
    except Exception as e:
        print(f"Erro ao enviar mensagem ao GPT-4: {e}")
        return "Erro ao obter resposta do GPT-4 (verifique a chave da API)."

def get_response(model, prompt):
    if model == "gpt":
        return enviar_mensagem_gpt(prompt)
    elif model == "gemini":
        genai.configure(api_key=GEMINI_API_KEY)
        modelo_gemini = genai.GenerativeModel('gemini-pro')
        return enviar_mensagem_gemini(modelo_gemini, prompt)
    else:
        return "Modelo inválido."
""")

    create_file("app/routes.py", f"""
from flask import render_template, request, session, redirect, url_for
from app import app, get_db_connection
from app.models import save_conversation, load_conversations, clear_conversations, get_response
import os
from config import GEMINI_API_KEY, OPENAI_API_KEY

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        session["user_id"] = os.urandom(16).hex()

    user_id = session["user_id"]
    conversations = load_conversations(user_id)

    if GEMINI_API_KEY and not OPENAI_API_KEY:
      default_model = "gemini"
    elif OPENAI_API_KEY and not GEMINI_API_KEY:
      default_model = "gpt"
    else:
      default_model = "gpt"

    if request.method == "POST":
        user_message = request.form["message"]
        selected_model = request.form.get("model", default_model)

        response = get_response(selected_model, user_message)

        save_conversation(user_id, user_message, response, selected_model)
        conversations = load_conversations(user_id)

        messages_html = render_template(
            "messages.html",
            conversations=conversations
        )
        return messages_html

    return render_template(
        "index.html",
        conversations=conversations,
        default_model=default_model
    )

@app.route("/clear", methods=["POST"])
def clear_history():
    user_id = session.get("user_id")
    if user_id:
        clear_conversations(user_id)
    return redirect(url_for("index"))

@app.route("/new", methods=["POST"])
def new_chat():
    session["user_id"] = os.urandom(16).hex()
    return redirect(url_for("index"))
""")

    create_file("app/templates/index.html", """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatGPT Clone</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN" crossorigin="anonymous">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 sidebar">
                <div class="d-flex flex-column h-100">
                    <div class="logo-container">
                       <img src="https://logowik.com/content/uploads/images/openai-chatgpt5786.jpg" alt="ChatGPT Logo" class="logo">
                    </div>
                    <div class="mt-3">
                        <form method="POST" action="/new">
                            <button class="btn new-chat-btn w-100 mb-2" type="submit">Novo Chat</button>
                        </form>
                    </div>
                    <div class="model-select-container mt-3">
                        <label for="model-select">Escolha o Modelo:</label>
                        <select id="model-select" class="form-select">
                            <option value="gpt" {% if default_model == 'gpt' %}selected{% endif %}>GPT-4</option>
                            <option value="gemini" {% if default_model == 'gemini' %}selected{% endif %}>Gemini</option>
                        </select>
                    </div>
                    <div class="chat-list flex-grow-1">
                        <!-- Chat list will be loaded here -->
                        {% for date_group, messages in conversations|groupby('date_group') %}
                        <div class="chat-date-group">
                           <p class="mt-3" >{{ date_group }}</p>
                            {% for message in messages %}
                                {% if message.user_message %}
                                <div class="chat-item user-chat-item">
                                    <p class="mt-3" >{{ message.user_message }}</p>
                                </div>
                                {% else %}
                                <div class="chat-item gpt-chat-item">
                                    <p class="mt-3" >{{ message.gpt_response }}</p>
                                </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                        {% endfor %}
                    </div>
                    <div class="mt-auto">
                        <form method="POST" action="/clear">
                            <button class="btn clear-chat-btn w-100 mb-2" type="submit">Limpar Conversas</button>
                        </form>
                        <button class="btn settings-btn w-100 mb-3">Configurações</button>
                    </div>
                </div>
            </div>
            <!-- Main Chat Area -->
            <div class="col-md-9 main-chat-area">
                <div class="chat-header">
                    <h2>ChatGPT</h2>
                </div>
                <div class="chat-body flex-grow-1">
                    <div class="chat-messages">
                      {% for date_group, messages in conversations|groupby('date_group') %}
                        <div class="date-group">
                            <p class="date-separator"><span>{{ date_group }}</span></p>
                            {% for message in messages %}
                                {% if message.user_message %}
                                <div class="message user-message">
                                  <img src="https://s.gravatar.com/avatar/7945097d945af8579324c9599859f760?s=48&d=identicon&r=PG" alt="User Avatar" class="user-avatar">
                                    <div class="message-content user-message-content">
                                        <p>{{ message.user_message }}</p>
                                    </div>
                                </div>
                                {% else %}
                                <div class="message gpt-message">
                                   <img src="https://logowik.com/content/uploads/images/openai-chatgpt5786.jpg" alt="GPT Avatar" class="gpt-avatar">
                                    <div class="message-content gpt-message-content">
                                        <p>{{ message.gpt_response }}</p>
                                    </div>
                                </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                        {% endfor %}
                    </div>
                </div>
                <div class="chat-footer">
                    <form method="POST" class="input-form">
                        <input type="text" name="message" class="form-control" placeholder="Digite sua mensagem" required>
                        <button type="submit" class="btn send-btn"><svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 mr-1" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg></button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap 5 JS (optional, for some features like dropdowns) -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL" crossorigin="anonymous"></script>
    <script>
        // JavaScript functions for handling message submission, etc.
        document.addEventListener('DOMContentLoaded', function() {
            const chatBody = document.querySelector('.chat-body');
            chatBody.scrollTop = chatBody.scrollHeight;

            document.querySelector('.input-form').addEventListener('submit', function(e) {
                e.preventDefault();
                const messageInput = document.querySelector('input[name="message"]');
                const message = messageInput.value;
                messageInput.value = '';

                // AJAX to send the message and get a response
                fetch('/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'message=' + encodeURIComponent(message) + '&model=' + getSelectedModel()
                })
                .then(response => response.text())
                .then(data => {
                    // Update the chat messages area with the new message and response
                    const chatMessages = document.querySelector('.chat-messages');
                    chatMessages.innerHTML = data;

                    // Scroll to the bottom of the chat body
                    chatBody.scrollTop = chatBody.scrollHeight;
                });
            });
        });

        function getSelectedModel() {
            return document.getElementById('model-select').value;
        }
    </script>
</body>
</html>
""")

    create_file("app/templates/messages.html", """
{% for date_group, messages in conversations|groupby('date_group') %}
<div class="date-group">
    <p class="date-separator"><span>{{ date_group }}</span></p>
    {% for message in messages %}
        {% if message.user_message %}
        <div class="message user-message">
            <img src="https://s.gravatar.com/avatar/7945097d945af8579324c9599859f760?s=48&d=identicon&r=PG" alt="User Avatar" class="user-avatar">
            <div class="message-content user-message-content">
                <p>{{ message.user_message }}</p>
            </div>
        </div>
        {% else %}
        <div class="message gpt-message">
            <img src="https://logowik.com/content/uploads/images/openai-chatgpt5786.jpg" alt="GPT Avatar" class="gpt-avatar">
            <div class="message-content gpt-message-content">
                <p>{{ message.gpt_response }}</p>
            </div>
        </div>
        {% endif %}
    {% endfor %}
</div>
{% endfor %}
""")

    create_file("app/static/style.css", """
/* General Styles */
body {
    font-family: Arial, sans-serif;
    background-color: #f4f4f4;
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow: hidden;
}

/* Sidebar Styles */
.sidebar {
    background-color: #1e293b;
    color: #fff;
    padding: 15px;
    border-right: 1px solid #ddd;
    overflow-y: auto;
}

.logo-container {
    display: flex;
    align-items: center;
    justify-content: start;
    padding: 10px;
}

.logo {
    width: 40px;
    height: auto;
}

.new-chat-btn, .clear-chat-btn, .settings-btn {
    background-color: #0D6EFD;
    color: #fff;
    border: none;
    margin-bottom: 5px;
}

.new-chat-btn:hover, .clear-chat-btn:hover, .settings-btn:hover {
    background-color: #0b5ed7;
}

.chat-list {
    overflow-y: auto;
    flex-grow: 1;
}

.chat-list .chat-item {
    padding: 10px;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.chat-list .chat-item.user-chat-item {
    background-color: #343541;
    color: #fff;
    border-radius: 5px;
}
.chat-list .chat-item.gpt-chat-item {
    background-color: #444654;
    color: #fff;
    border-radius: 5px;
}

.chat-list .chat-item:hover {
    background-color: #495057;
}

/* Main Chat Area Styles */
.main-chat-area {
    background-color: #f8f9fa;
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.chat-header {
    background-color: #fff;
    padding: 15px;
    border-bottom: 1px solid #ddd;
    z-index: 10;
}

.chat-body {
    flex-grow: 1;
    overflow-y: auto;
    padding: 15px;
}

.chat-messages {
    display: flex;
    flex-direction: column;
}

.date-group {
    margin-bottom: 20px;
}

.date-separator {
    text-align: center;
    margin-bottom: 15px;
    color: #868e96;
}

.date-separator span {
    background-color: #f8f9fa;
    padding: 5px 10px;
    border-radius: 5px;
    border: 1px solid #ddd;
}

.message {
    display: flex;
    margin-bottom: 15px;
}

.user-message {
    justify-content: flex-end;
}

.gpt-message {
    justify-content: flex-start;
}

.user-avatar, .gpt-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin-right: 10px;
}

.user-message .user-avatar {
    order: 2; /* Puts the avatar on the right for user messages */
    margin-right: 0;
    margin-left: 10px;
}

.message-content {
    padding: 10px;
    border-radius: 5px;
    max-width: 80%;
    word-wrap: break-word;
}

.user-message-content {
    background-color: #343541;
    color: #fff;
    border-top-left-radius: 5px;
    border-top-right-radius: 0px;
}

.gpt-message-content {
    background-color: #444654;
    color: #fff;
    border-top-left-radius: 0px;
    border-top-right-radius: 5px;
}

.chat-footer {
    background-color: #fff;
    padding: 15px;
    border-top: 1px solid #ddd;
}

.input-form {
    display: flex;
}

.input-form input[type="text"] {
    flex-grow: 1;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    margin-right: 10px;
}

.send-btn {
    background-color: #19c37d;
    color: #fff;
    border: none;
    border-radius: 5px;
    padding: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.send-btn:hover {
    background-color: #19c37d;
}

.send-btn svg {
    margin-right: 5px;
}
/* Model Selection Styles */
.model-select-container {
    margin-bottom: 20px;
}

.model-select-container label {
    color: #fff;
    margin-bottom: 5px;
}

.model-select-container .form-select {
    background-color: #343541;
    color: #fff;
    border: 1px solid #6c757d;
    padding: 5px 10px;
    border-radius: 5px;
}

.model-select-container .form-select:focus {
    border-color: #86b7fe;
    outline: 0;
    box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}
""")

    create_file("run.py", """
import os
import sys
from app import app

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    app.run(debug=True, host='0.0.0.0', port=port)
""")

# --- Função Principal ---

def main():
    """Função principal para configurar e iniciar o projeto."""
    logger.info("Iniciando a configuração do projeto ChatGPT Clone...")

    # 1. Cria a estrutura de pastas e arquivos
    create_project_structure()

    # 2. Solicita as chaves de API (se necessário)
    gemini_key, gpt_key = get_api_keys()

    # 3. Salva as chaves de API (mesmo que vazias)
    save_api_keys(gemini_key, gpt_key)

    # 4. Instala as dependências
    install_dependencies("requirements.txt")

    # 5. Verifica a conexão com o MySQL
    check_mysql_connection()

    # 6. Configura o banco de dados
    if not database_exists() or not table_exists():
        create_database_and_table()
    else:
        logger.info("O banco de dados e a tabela já existem. Nenhuma ação necessária.")

    # 7. Inicia o aplicativo Flask
    if check_port(DEFAULT_PORT):
        logger.warning(f"A porta {DEFAULT_PORT} está em uso. Tentando a porta {BACKUP_PORT}...")
        if check_port(BACKUP_PORT):
            logger.error(f"A porta {BACKUP_PORT} também está em uso. Não é possível iniciar o aplicativo.")
            print(f"Erro: As portas {DEFAULT_PORT} e {BACKUP_PORT} estão em uso. Libere uma delas para iniciar o aplicativo.")
            sys.exit(1)
        else:
            start_flask_app(BACKUP_PORT)
    else:
        start_flask_app(DEFAULT_PORT)

    logger.info("Configuração concluída com sucesso!")

if __name__ == "__main__":
    main()