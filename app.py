from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import openai
import os
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Configuration API
openai.api_key = os.environ.get("ASSISTANT_API_KEY")

# Scopes pour Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_TIMEZONE = "Europe/Paris"

# Charger les identifiants OAuth
creds = Credentials.from_authorized_user_file("token.json", SCOPES)
service = build("calendar", "v3", credentials=creds)

# Route de test
@app.route("/")
def home():
    return "✅ Assistant Álamo Agenda connecté et opérationnel."

# Fonction d’analyse de commande
def interpret_instruction(instruction):
    """Analyse la phrase et décide s'il faut ajouter, supprimer ou lister un événement"""
    instruction = instruction.lower()
    if "supprime" in instruction or "enlève" in instruction:
        return "delete"
    elif "ajoute" in instruction or "crée" in instruction or "rajoute" in instruction:
        return "add"
    elif "liste" in instruction or "montre" in instruction:
        return "list"
    else:
        return "unknown"

# Ajouter un événement
def add_event(summary, date_str, time_str=None):
    if time_str:
        start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(hours=1)
    else:
        start_time = datetime.strptime(date_str, "%Y-%m-%d")
        end_time = start_time + timedelta(days=1)

    start_time = start_time.astimezone(pytz.timezone(CALENDAR_TIMEZONE))
    end_time = end_time.astimezone(pytz.timezone(CALENDAR_TIMEZONE))

    event = {
        "summary": summary,
        "start": {"dateTime": start_time.isoformat(), "timeZone": CALENDAR_TIMEZONE},
        "end": {"dateTime": end_time.isoformat(), "timeZone": CALENDAR_TIMEZONE},
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    return created.get("htmlLink")

# Supprimer un événement par mot-clé
def delete_event(keyword):
    now = datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(calendarId="primary", timeMin=now, maxResults=20, singleEvents=True, orderBy="startTime").execute()
    events = events_result.get("items", [])

    for event in events:
        if keyword.lower() in event["summary"].lower():
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            return f"🗑️ Événement '{event['summary']}' supprimé."
    return "❌ Aucun événement correspondant trouvé."

# Endpoint principal pour parler à ton assistant
@app.route("/command", methods=["POST"])
def command():
    data = request.get_json()
    instruction = data.get("instruction")

    if not instruction:
        return jsonify({"error": "Aucune instruction reçue."}), 400

    action = interpret_instruction(instruction)

    if action == "add":
        # Exemple : "ajoute rendez-vous FNAC le 10 octobre à 14h"
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant qui extrait des dates et heures de phrases."},
                {"role": "user", "content": instruction},
            ],
        )
        parsed = response.choices[0].message.content
        return jsonify({"message": f"🗓️ Je vais ajouter : {parsed}"})

    elif action == "delete":
        keyword = instruction.replace("supprime", "").replace("enlève", "").strip()
        result = delete_event(keyword)
        return jsonify({"message": result})

    else:
        return jsonify({"message": "❓ Je n’ai pas compris ta commande."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
