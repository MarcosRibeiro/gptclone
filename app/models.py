from datetime import datetime
import mysql.connector
from app import get_db_connection
import google.generativeai as genai
import openai
from config import GEMINI_API_KEY, OPENAI_API_KEY

def save_conversation(user_id, chat_id, user_message, gpt_response, model):
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        sql = "INSERT INTO conversations (user_id, chat_id, user_message, gpt_response, date_group, model) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (user_id, chat_id, user_message, gpt_response, datetime.now().date(), model)
        mycursor.execute(sql, val)
        mydb.commit()
        mydb.close()
    except mysql.connector.Error as err:
        print(f"Erro ao salvar conversa: {err}")

def load_conversations(user_id, chat_id):
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT user_message, gpt_response, DATE(timestamp) as date_group, chat_id FROM conversations WHERE user_id = %s AND chat_id = %s ORDER BY timestamp ASC", (user_id, chat_id))
        conversations = mycursor.fetchall()
        mydb.close()
        print("Conversas carregadas do banco:", conversations)
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
        print(f"Detalhes do erro: {e.args}")
        return "Desculpe, não consegui entender sua pergunta, por favor, reformule"

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