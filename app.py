from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

app = Flask(__name__)

# Charger les credentials (token.json) générés après l'autorisation
creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/calendar"])

@app.route('/')
def home():
    return "✅ Assistant Alamo Agenda connecté à Google Calendar et prêt à recevoir des commandes."

@app.route('/command', methods=['POST'])
def command():
    data = request.get_json()
    message = data.get("message", "").lower()

    service = build("calendar", "v3", credentials=creds)

    if "ajoute" in message or "rajoute" in message:
        event = {
            'summary': 'Rendez-vous ajouté via Assistant Alamo',
            'start': {'dateTime': '2025-10-10T15:00:00', 'timeZone': 'Europe/Paris'},
            'end': {'dateTime': '2025-10-10T16:00:00', 'timeZone': 'Europe/Paris'}
        }
        service.events().insert(calendarId='primary', body=event).execute()
        return jsonify({"response": "✅ Événement ajouté avec succès."})

    elif "supprime" in message or "enlève" in message:
        events = service.events().list(calendarId='primary', maxResults=10).execute().get('items', [])
        for event in events:
            if "fnac" in event['summary'].lower():
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                return jsonify({"response": f"🗑️ Événement '{event['summary']}' supprimé."})
        return jsonify({"response": "⚠️ Aucun événement correspondant trouvé."})

    else:
        return jsonify({"response": "Je n’ai pas compris la commande."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
