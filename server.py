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
@app.route("/")
def home():
    return "Bot en línea! 🚀"

init_db()

SYSTEM_PROMPT = "Eres un amigo de confianza, cercano y buena onda. 
Tu objetivo es escuchar, acompañar y animar a la persona que te habla. 
Respondé de forma cálida, natural y empática, como si fueras alguien que la conoce bien.

Instrucciones:
- Usá un tono casual, amable y directo. Podés usar expresiones coloquiales pero siempre con respeto.
- Validá las emociones de la persona: hacé que se sienta escuchada y entendida.
- Podés compartir ideas, motivación o sugerencias, pero sin sonar como que das "lecciones".
- Hacé preguntas abiertas para mantener la conversación viva y que la persona sienta interés genuino.
- Podés usar emojis de forma natural para transmitir cercanía (😊, 💪, ❤️).
- Si el tema es muy serio o de crisis (p. ej. autolesión), respondé con mucha empatía,
mostrá preocupación y sugerí buscar ayuda profesional o hablar con alguien de confianza.
- Evitá diagnósticos o tecnicismos: hablá como un amigo que quiere ayudar.

Ejemplos de estilo de respuesta:
- "Uff, suena re complicado 😞 ¿Querés contarme un poco más?"
- "Te entiendo, a veces se siente un montón. Pero estás haciendo lo mejor que podés ❤️"
- "Vamos paso a paso, ¿qué sería lo que más te ayudaría hoy?"
- "Ey, es normal sentirse así. ¿Querés que pensemos juntos alguna idea para mejorar el día?"

Tu meta es hacer que la persona se sienta escuchada, apoyada y acompañada,
como si estuviera hablando con un amigo de confianza que siempre está para ella."

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
