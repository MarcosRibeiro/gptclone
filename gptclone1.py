import os
import openai
import mysql.connector
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from mysql.connector import errorcode
from datetime import datetime
import google.generativeai as genai
import logging
import sys
import subprocess

# Configuração de logging
logging.basicConfig(
    filename='chat_assistente.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações do aplicativo
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Chave secreta para a sessão

# Configurações do banco de dados MySQL
DB_HOST = "localhost"
DB_USER = "chatgpt_user"  # Usuário padrão
DB_PASSWORD = "chatgpt_password"  # Senha padrão
DB_NAME = "chatgpt_clone"

# --- CONFIGURAÇÃO DAS APIS ---

def verificar_e_instalar_bibliotecas():
    """
    Verifica se as bibliotecas necessárias estão instaladas e as instala automaticamente, se necessário.
    """
    bibliotecas = ["google-generativeai", "openai"]
    for biblioteca in bibliotecas:
        try:
            __import__(biblioteca.replace("-", "_"))
            logger.info(f"Biblioteca {biblioteca} já está instalada.")
        except ImportError:
            logger.warning(f"Biblioteca {biblioteca} não encontrada. Instalando...")
            try:
                # Suprime a saída do pip
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", biblioteca],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"Biblioteca {biblioteca} instalada com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao instalar a biblioteca {biblioteca}: {e}")
                raise

def obter_chaves_api():
    """
    Obtém as chaves de API do Gemini e GPT-4 das variáveis de ambiente ou solicita ao usuário.
    Retorna um dicionário com as chaves.
    """
    chaves = {
        "gemini": os.environ.get("GOOGLE_GEMINI_API_KEY"),
        "gpt": os.environ.get("OPENAI_API_KEY")
    }

    if not chaves["gemini"]:
        logger.warning("Chave da API do Gemini não encontrada nas variáveis de ambiente.")
        chaves["gemini"] = input("Por favor, insira sua chave da API do Gemini: ")
        os.environ["GOOGLE_GEMINI_API_KEY"] = chaves["gemini"]
        logger.info("Chave da API do Gemini definida na variável de ambiente.")

    if not chaves["gpt"]:
        logger.warning("Chave da API do GPT-4 não encontrada nas variáveis de ambiente.")
        chaves["gpt"] = input("Por favor, insira sua chave da API do GPT-4: ")
        os.environ["OPENAI_API_KEY"] = chaves["gpt"]
        logger.info("Chave da API do GPT-4 definida na variável de ambiente.")

    return chaves

# Configuração da API do Gemini
GEMINI_API_KEY = ""

# Configuração da API do GPT
OPENAI_API_KEY = ""

# --- FUNÇÕES DO GEMINI ---

def inicializar_gemini(chave_gemini):
    """
    Configura e inicializa o modelo Gemini.
    """
    try:
        genai.configure(api_key=chave_gemini)
        modelo = genai.GenerativeModel('gemini-pro')
        logger.info("Modelo Gemini inicializado com sucesso.")
        return modelo
    except Exception as e:
        logger.error(f"Erro ao inicializar o Gemini: {e}")
        return None

def enviar_mensagem_gemini(modelo, mensagem):
    """
    Envia uma mensagem ao Gemini e retorna a resposta.
    """
    try:
        resposta = modelo.generate_content(mensagem)
        logger.info(f"Resposta do Gemini: {resposta.text}")
        return resposta.text
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem ao Gemini: {e}")
        return None

# --- FUNÇÕES DO GPT ---

def enviar_mensagem_gpt(mensagem):
    """
    Envia uma mensagem ao GPT-4 e retorna a resposta.
    """
    try:
        openai.api_key = OPENAI_API_KEY
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": mensagem}
            ]
        )
        resposta_texto = resposta.choices[0].message.content
        logger.info(f"Resposta do GPT-4: {resposta_texto}")
        return resposta_texto
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem ao GPT-4: {e}")
        return None

# --- HTML e CSS embutidos ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatGPT Clone</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN" crossorigin="anonymous">
    <style>
        {{ css }}
    </style>
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
                            <option value="gpt">GPT-4</option>
                            <option value="gemini">Gemini</option>
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
"""

CSS_STYLES = """
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
/* ... (Rest of your CSS) */
"""

# --- FUNÇÕES DO APLICATIVO ---

# Função para criar o banco de dados, usuário e tabela
def create_database_user_and_table():
    try:
        # Conecta ao MySQL usando a conta root (ou uma conta com privilégios para criar usuários e bancos de dados)
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user="root",  # Substitua se necessário
            password="password"  # Substitua se necessário
        )
        mycursor = mydb.cursor()

        # Cria o banco de dados se ele não existir
        mycursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")

        # Tenta criar o usuário (ignora se ele já existir)
        try:
            mycursor.execute(f"CREATE USER IF NOT EXISTS '{DB_USER}'@'{DB_HOST}' IDENTIFIED BY '{DB_PASSWORD}'")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_CANNOT_USER:
                print("Usuário já existe, continuando...")
            else:
                print(f"Erro ao criar usuário: {err}")

        # Garante os privilégios ao usuário no banco de dados
        mycursor.execute(f"GRANT ALL PRIVILEGES ON {DB_NAME}.* TO '{DB_USER}'@'{DB_HOST}'")
        mycursor.execute("FLUSH PRIVILEGES")

        # Conecta ao banco de dados usando as credenciais do novo usuário
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        mycursor = mydb.cursor()

        # Cria a tabela de conversas se ela não existir
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
        print("Banco de dados, usuário e tabela criados com sucesso.")

    except mysql.connector.Error as err:
        print(f"Erro ao criar banco de dados, usuário ou tabela: {err}")

# Função para obter resposta do GPT ou Gemini
def get_response(model, prompt):
    if model == "gpt":
        return enviar_mensagem_gpt(prompt)
    elif model == "gemini":
        modelo_gemini = inicializar_gemini(GEMINI_API_KEY)
        return enviar_mensagem_gemini(modelo_gemini, prompt)
    else:
        return "Modelo inválido."

# Função para salvar conversa no banco de dados
def save_conversation(user_id, user_message, gpt_response, model):
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        mycursor = mydb.cursor()
        sql = "INSERT INTO conversations (user_id, user_message, gpt_response, date_group, model) VALUES (%s, %s, %s, %s, %s)"
        val = (user_id, user_message, gpt_response, datetime.now().date(), model)
        mycursor.execute(sql, val)
        mydb.commit()
    except mysql.connector.Error as err:
        print(f"Erro ao salvar conversa: {err}")

# Função para carregar histórico de conversas
def load_conversations(user_id):
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT user_message, gpt_response, DATE(timestamp) as date_group FROM conversations WHERE user_id = %s ORDER BY timestamp ASC", (user_id,))
        conversations = mycursor.fetchall()
        return conversations
    except mysql.connector.Error as err:
        print(f"Erro ao carregar conversas: {err}")
        return []

# --- ROTAS DO APLICATIVO ---

# Rota principal
@app.route("/", methods=["GET", "POST"])
def index():
    global GEMINI_API_KEY, OPENAI_API_KEY
    if "user_id" not in session:
        session["user_id"] = os.urandom(16).hex()

    user_id = session["user_id"]
    conversations = load_conversations(user_id)

    if request.method == "POST":
        user_message = request.form["message"]
        selected_model = request.form.get("model", "gpt")

        # Obter resposta do modelo selecionado
        response = get_response(selected_model, user_message)

        save_conversation(user_id, user_message, response, selected_model)
        conversations = load_conversations(user_id)

        # Renderizar apenas a parte das mensagens para atualização via AJAX
        messages_html = render_template_string("""
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
        """, conversations=conversations)
        return messages_html

    # Configuração da API do Gemini
    chaves = obter_chaves_api()
    GEMINI_API_KEY = chaves["gemini"]

    # Configuração da API do GPT
    OPENAI_API_KEY = chaves["gpt"]

    return render_template_string(HTML_TEMPLATE, css=CSS_STYLES, conversations=conversations)

# Rota para limpar o histórico de conversas
@app.route("/clear", methods=["POST"])
def clear_history():
    user_id = session.get("user_id")
    if user_id:
        try:
            mydb = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            mycursor = mydb.cursor()
            mycursor.execute("DELETE FROM conversations WHERE user_id = %s", (user_id,))
            mydb.commit()
        except mysql.connector.Error as err:
            print(f"Erro ao limpar histórico de conversas: {err}")
    return redirect(url_for("index"))

# Rota para criar um novo chat (novo user_id)
@app.route("/new", methods=["POST"])
def new_chat():
    session["user_id"] = os.urandom(16).hex()  # Cria um novo user_id
    return redirect(url_for("index"))

# --- INICIALIZAÇÃO DO APLICATIVO ---

# Verifica e instala as bibliotecas antes de iniciar o aplicativo
verificar_e_instalar_bibliotecas()

# Cria o banco de dados, usuário e tabela se não existirem
create_database_user_and_table()

# Inicia o aplicativo Flask (usando o servidor de desenvolvimento para simular produção)
if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000) # Para teste de produção