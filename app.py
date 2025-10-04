from flask import Flask, request, jsonify, redirect, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "super_secret_key"

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Initialiser OpenAI client
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route('/')
def home():
    return "✅ Assistant Álamo Agenda connecté et intelligent."

@app.route('/authorize')
def authorize():
    flow = InstalledAppFlow.from_client_secrets_file(
        '/etc/secrets/credentials.json', SCOPES)
    flow.redirect_uri = "https://alamo-agenda-assistant.onrender.com/oauth2callback"
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = InstalledAppFlow.from_client_secrets_file(
        '/etc/secrets/credentials.json', SCOPES, state=state)
    flow.redirect_uri = "https://alamo-agenda-assistant.onrender.com/oauth2callback"
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    session['credentials'] = creds_to_dict(creds)
    return "✅ Connexion Google Agenda réussie ! L'assistant peut maintenant gérer vos rendez-vous."

@app.route('/assistant', methods=['POST'])
def assistant():
    if 'credentials' not in session:
        return jsonify({"error": "Non connecté à Google Calendar. Visitez /authorize d'abord."}), 401

    user_input = request.json.get("message", "")
    if not user_input:
        return jsonify({"error": "Message vide"}), 400

    # Demander à GPT d'analyser la commande
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui traduit les commandes humaines en instructions pour Google Calendar. Réponds en JSON avec action (add, delete, list), summary, start, end, date etc."},
            {"role": "user", "content": user_input}
        ]
    )

    result = response.choices[0].message.content
    print("GPT a compris :", result)

    creds = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=creds)

    try:
        import json
        data = json.loads(result)
        action = data.get("action")

        if action == "add":
            event = {
                'summary': data.get('summary', 'Événement Álamo'),
                'start': {'dateTime': data['start'], 'timeZone': 'Europe/Paris'},
                'end': {'dateTime': data['end'], 'timeZone': 'Europe/Paris'},
            }
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            return jsonify({"status": "success", "message": f"Événement ajouté : {created_event['summary']}"})

        elif action == "delete":
            query = data.get("summary", "")
            date = data.get("date")
            if not date:
                return jsonify({"error": "Date manquante pour suppression."}), 400

            time_min = f"{date}T00:00:00Z"
            time_max = f"{date}T23:59:59Z"
            events = service.events().list(calendarId='primary', q=query, timeMin=time_min, timeMax=time_max).execute()
            for event in events.get('items', []):
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
            return jsonify({"status": "success", "message": f"Événements contenant '{query}' le {date} supprimés."})

        elif action == "list":
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = service.events().list(calendarId='primary', timeMin=now, maxResults=5, singleEvents=True, orderBy='startTime').execute()
            events = events_result.get('items', [])
            return jsonify({"events": events})

        else:
            return jsonify({"error": "Action non reconnue"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def creds_to_dict(creds):
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
