import os
from flask import Flask, request
from db import init_db, save_message, get_last_messages
import openai
from twilio.rest import Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")

MAX_HISTORY = int(os.getenv("MAX_HISTORY_MESSAGES", 20))
CRISIS_HOOK_ENABLED = os.getenv("CRISIS_HOOK_ENABLED", "true").lower() == "true"

openai.api_key = OPENAI_API_KEY

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = Flask(__name__)
init_db()

SYSTEM_PROMPT = "Eres un asistente empático que actúa como psicólogo. Responde con comprensión y apoyo."

def contains_crisis(text):
    # Simple ejemplo, podes mejorar
    keywords = ["suicid", "matarme", "morir"]
    return any(k in text.lower() for k in keywords)

def send_whatsapp_message(to, body):
    print(f"Enviando mensaje a {to}: {body}")
    client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=to,
        body=body
    )

def handle_message(user_id, text):
    print(f"Mensaje recibido de {user_id}: {text}")
    save_message(user_id, "user", text)

    if CRISIS_HOOK_ENABLED and contains_crisis(text):
        crisis_msg = (
            "Lamento que te sientas así. "
            "Si estás en peligro inmediato, contactá a emergencias (911) o Línea 135. "
            "¿Querés que te pase más recursos de ayuda?"
        )
        save_message(user_id, "assistant", crisis_msg)
        send_whatsapp_message(user_id, crisis_msg)
        return

    history = get_last_messages(user_id, MAX_HISTORY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": text}]

    try:
        resp = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        reply = resp.choices[0].message.content.strip()
        print(f"Respuesta del bot: {reply}")
        save_message(user_id, "assistant", reply)
        send_whatsapp_message(user_id, reply)
    except Exception as e:
        print("Error con OpenAI:", e)
        send_whatsapp_message(user_id, "Perdón, tuve un problema procesando tu mensaje. Intentá de nuevo en unos minutos.")

@app.route("/webhook/twilio", methods=["POST"])
def webhook_twilio():
    from_number = request.values.get("From")
    body = request.values.get("Body")
    if from_number and body:
        handle_message(from_number, body)
    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

