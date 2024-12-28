from flask import render_template, request, session, redirect, url_for, jsonify
from app import app, get_db_connection
from app.models import save_conversation, load_conversations, clear_conversations, get_response
import os
from config import GEMINI_API_KEY, OPENAI_API_KEY
import re
import uuid

@app.route("/", methods=["GET", "POST"])
def index():
    # Define um user_id padrão (1) se não existir na sessão
    if "user_id" not in session:
        session["user_id"] = "1"  # Usando '1' como user_id padrão

    # Se não houver um chat_id na sessão, cria um novo
    if "chat_id" not in session:
        session["chat_id"] = generate_chat_id()

    user_id = session["user_id"]
    chat_id = session["chat_id"]

    # Carrega as conversas do chat atual, usando user_id e chat_id
    conversations = load_conversations(user_id, chat_id)

    # Agrupa as conversas por data para a barra lateral
    sidebar_conversations = {}
    for conv in conversations:
        date_group = conv['date_group'].strftime('%Y-%m-%d')
        if date_group not in sidebar_conversations:
            sidebar_conversations[date_group] = []
        sidebar_conversations[date_group].append(conv)

    # Define o modelo padrão com base nas chaves de API
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
        formatted_response = format_response(response)

        # Salva a conversa no banco de dados
        save_conversation(user_id, chat_id, user_message, formatted_response, selected_model)

        # Retorna a resposta formatada como JSON
        return jsonify({'response': formatted_response})

    # Renderiza o template index.html com as conversas e o modelo padrão
    return render_template(
        "index.html",
        conversations=conversations,
        sidebar_conversations=sidebar_conversations,
        default_model=default_model
    )

@app.route("/clear", methods=["POST"])
def clear_history():
    user_id = session.get("user_id")
    if user_id:
        clear_conversations(user_id)
    # Retorna um JSON indicando sucesso
    return jsonify({"status": "success", "action": "clear_chat"})

@app.route("/new", methods=["POST"])
def new_chat():
    # Verifica se 'user_id' existe na sessão
    if 'user_id' not in session:
        session['user_id'] = "1"  # Define o user_id padrão se não existir

    # Gera um novo chat_id
    session["chat_id"] = generate_chat_id()

    # Retorna um JSON indicando sucesso e o novo chat_id
    return jsonify({"status": "success", "action": "new_chat", "chat_id": session["chat_id"]})

def generate_chat_id():
    """Gera um novo chat_id único usando uuid."""
    return str(uuid.uuid4())

def format_response(response):
    """Formata a resposta do Gemini para melhor legibilidade."""
    # Divide a resposta em linhas
    lines = response.split('\n')
    formatted_lines = []

    for line in lines:
        # Quebra linhas longas
        while len(line) > 80:
            split_point = line.rfind(' ', 0, 80)
            if split_point == -1:
                split_point = 80
            formatted_lines.append(line[:split_point])
            line = line[split_point:].strip()

        # Adiciona linhas formatadas (removendo linhas muito curtas)
        if len(line.strip()) > 5:
            formatted_lines.append(line)

    # Junta as linhas formatadas com quebras de linha HTML
    formatted_response = "<br>".join(formatted_lines)

    # Formata em negrito trechos que parecem ser títulos ou itens de lista
    formatted_response = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_response)

    return formatted_response

@app.route("/chat/<chat_id>", methods=["GET"])
def load_chat(chat_id):
    user_id = session.get("user_id", "1")  # Obtém o user_id da sessão ou usa '1' como padrão

    # Carrega as conversas do chat_id selecionado
    conversations = load_conversations(user_id, chat_id)

    # Atualiza o chat_id atual na sessão
    session["chat_id"] = chat_id

    # Retorna as conversas como JSON
    return jsonify({"conversations": conversations})

@app.route("/conversations", methods=["GET"])
def get_conversations():
    user_id = session.get("user_id", "1")  # Obtém o user_id da sessão ou usa '1' como padrão
    chat_id = session.get("chat_id")  # Obtém o chat_id atual da sessão

    if not chat_id:
        return jsonify({"conversations": [], "sidebar_conversations": {}})

    conversations = load_conversations(user_id, chat_id)
    sidebar_conversations = {}
    for conv in conversations:
        date_group = conv['date_group'].strftime('%Y-%m-%d')
        if date_group not in sidebar_conversations:
            sidebar_conversations[date_group] = []
        sidebar_conversations[date_group].append(conv)

    return jsonify({
        "conversations": conversations,
        "sidebar_conversations": sidebar_conversations,
        "current_chat_id": chat_id
    })