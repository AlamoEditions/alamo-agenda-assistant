from flask import Flask, request, jsonify
import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

@app.route('/')
def home():
    return "✅ Assistant Álamo Agenda en ligne et connecté."

@app.route('/add_event', methods=['POST'])
def add_event():
    data = request.json
    summary = data.get('summary', 'Événement Álamo')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'Europe/Paris'},
        'end': {'dateTime': end_time, 'timeZone': 'Europe/Paris'},
    }

    service.events().insert(calendarId='primary', body=event).execute()
    return jsonify({'status': 'success', 'message': 'Événement ajouté.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
