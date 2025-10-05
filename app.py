from flask import Flask, request, jsonify, redirect, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import datetime

# ==============================================================
# Initialisation de l’application Flask
# ==============================================================

app = Flask(__name__)
app.secret_key = "super_secret_key"  # À changer pour une vraie clé secrète en prod

SCOPES = ['https://www.googleapis.com/auth/calendar']


# ==============================================================
# Accueil
# ==============================================================

@app.route('/')
def home():
    return "🌐 Assistant Alamo Agenda connecté et en ligne."


# ==============================================================
# Autorisation Google OAuth
# ==============================================================

@app.route('/authorize')
def authorize():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    flow.redirect_uri = 'https://alamo-agenda-assistant.onrender.com/oauth2callback'

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES, state=state)
    flow.redirect_uri = 'https://alamo-agenda-assistant.onrender.com/oauth2callback'

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    creds = flow.credentials
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    return "✅ Authentication completed! You can close this window."


# ==============================================================
# Test de connexion Google Calendar
# ==============================================================

@app.route('/test')
def test_connection():
    try:
        creds = Credentials.from_authorized_user_file(
            "token.json", SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        calendar = service.calendars().get(calendarId='primary').execute()
        return jsonify({
            "status": "✅ Assistant connecté à Google Calendar !",
            "calendar": calendar["summary"]
        })
    except Exception as e:
        return jsonify({
            "status": "❌ Erreur de connexion",
            "message": str(e)
        })


# ==============================================================
# Endpoint /command — interprétation d’une commande naturelle
# ==============================================================

@app.route('/command', methods=['POST'])
def add_event():
    try:
        data = request.get_json()
        instruction = data.get("instruction", "").lower()

        # Exemple simple : "rajoute un rendez-vous FNAC le 10 octobre à 14h"
        import re
        import dateparser

        match = re.search(r"le (\d{1,2} [a-zéû]+)(?: à (\d{1,2}h\d{0,2}))?", instruction)
        title_match = re.search(r"rendez-vous (.+?) le", instruction)

        if not match or not title_match:
            return jsonify({"status": "❌", "message": "Impossible de comprendre la commande."})

        title = title_match.group(1).strip().capitalize()
        date_text = match.group(1)
        time_text = match.group(2) if match.group(2) else "10h00"

        event_datetime = dateparser.parse(f"{date_text} {time_text}", languages=["fr"])

        start_time = event_datetime.isoformat()
        end_time = (event_datetime + datetime.timedelta(hours=1)).isoformat()

        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': title,
            'start': {'dateTime': start_time, 'timeZone': 'Europe/Paris'},
            'end': {'dateTime': end_time, 'timeZone': 'Europe/Paris'},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()

        return jsonify({
            "status": "✅",
            "message": f"Événement ajouté : {title}",
            "eventLink": event.get('htmlLink')
        })

    except Exception as e:
        return jsonify({"status": "❌ Erreur", "message": str(e)})


# ==============================================================
# Lancement de l’application
# ==============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
