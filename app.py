from flask import Flask, request, jsonify, redirect, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import datetime

# ======================================================
# ⚙️ Initialisation de l’application Flask
# ======================================================
app = Flask(__name__)
app.secret_key = "super_secret_key"  # clé secrète (à changer pour ta version prod)

SCOPES = ['https://www.googleapis.com/auth/calendar']

# ======================================================
# ✅ Accueil
# ======================================================
@app.route('/')
def home():
    return "✅ Assistant Álamo Agenda en ligne et connecté."

# ======================================================
# 🔐 Autorisation Google
# ======================================================
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
    return "✅ Connexion Google Agenda réussie ! Vous pouvez maintenant ajouter ou supprimer des événements."

# ======================================================
# 📅 Ajouter un événement
# ======================================================
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

# ======================================================
# 🧠 Nouvelle route : /command
# ======================================================
@app.route('/command', methods=['POST'])
def command():
    """
    Cette route reçoit des instructions textuelles comme :
    "efface le rendez-vous fnac le 10 octobre"
    et agit automatiquement sur Google Agenda.
    """
    if 'credentials' not in session:
        return jsonify({"error": "Non connecté à Google Calendar. Visitez /authorize d'abord."}), 401

    creds = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=creds)
    data = request.get_json()
    user_text = data.get("text", "").lower()

    # 🗑️ Suppression d’un événement
    if "efface" in user_text or "supprime" in user_text:
        try:
            query = user_text.replace("efface", "").replace("supprime", "").strip()
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            deleted = []
            for event in events:
                if query.split("le")[0].strip() in event.get("summary", "").lower():
                    service.events().delete(calendarId='primary', eventId=event['id']).execute()
                    deleted.append(event['summary'])

            if deleted:
                return jsonify({"status": "success", "message": f"Événements supprimés : {deleted}"})
            else:
                return jsonify({"status": "not_found", "message": "Aucun événement correspondant trouvé."})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "ok", "message": f"Commande reçue : {user_text}"})

# ======================================================
# 🔧 Fonction utilitaire
# ======================================================
def creds_to_dict(creds):
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

# ======================================================
# 🚀 Lancement de l’application
# ======================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
