from flask import Flask, request, jsonify, redirect, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"  # n'importe quelle clé secrète

SCOPES = ['https://www.googleapis.com/auth/calendar']

@app.route('/')
def home():
    return "✅ Assistant Álamo Agenda en ligne et connecté."

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
    return "✅ Connexion Google Agenda réussie ! Vous pouvez maintenant ajouter des événements."

@app.route('/add_event', methods=['POST'])
def add_event():
    if 'credentials' not in session:
        return jsonify({"error": "Non connecté à Google Calendar. Visitez /authorize d'abord."}), 401

    creds = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=creds)

    data = request.json
    event = {
        'summary': data.get('summary', 'Événement Álamo'),
        'start': {'dateTime': data['start'], 'timeZone': 'Europe/Paris'},
        'end': {'dateTime': data['end'], 'timeZone': 'Europe/Paris'},
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return jsonify({"status": "success", "event": created_event})

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
