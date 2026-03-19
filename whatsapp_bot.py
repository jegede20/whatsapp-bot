from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq

app = Flask(__name__)

# =============================================
# STEP 1: Paste your API keys here
# =============================================
GROQ_API_KEY = "your_groq_api_key_here"   # from console.groq.com
# Twilio keys are NOT needed in this file - they go in your Render environment variables

groq_client = Groq(api_key=GROQ_API_KEY)

# Stores conversation history per user (in-memory, resets on restart)
conversations = {}

SYSTEM_PROMPT = """You are a helpful WhatsApp personal assistant. You help users with three main tasks:

1. SUMMARIZE: When a user pastes an article or long text, summarize it clearly and concisely.
2. WRITE: Help users write or improve emails, messages, and other content. Ask for tone/purpose if unclear.
3. ANSWER: Answer any questions the user has using your knowledge.

Keep responses concise and WhatsApp-friendly (avoid overly long replies).
Always be friendly, clear, and helpful."""


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "unknown")

    # Initialize conversation history for new users
    if sender not in conversations:
        conversations[sender] = []

    # Add user message to history
    conversations[sender].append({"role": "user", "content": incoming_msg})

    # Keep only last 10 messages to stay within token limits
    if len(conversations[sender]) > 10:
        conversations[sender] = conversations[sender][-10:]

    # Call Groq API
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",  # Free model on Groq
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversations[sender],
            max_tokens=500,
        )
        reply = response.choices[0].message.content

        # Add assistant reply to history
        conversations[sender].append({"role": "assistant", "content": reply})

    except Exception as e:
        reply = f"Sorry, I ran into an error: {str(e)}"

    # Send reply via Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(reply)
    return str(twilio_response)


if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
