from flask import Flask, request, jsonify, redirect, session, render_template_string
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI
import os, datetime, json

app = Flask(__name__)
app.secret_key = "super_secret_key"

SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- INITIALISATION OPENAI ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- PAGE D’ACCUEIL ---
@app.route('/')
def home():
    if 'credentials' not in session:
        return '''
        <h2>Assistant Álamo Agenda</h2>
        <p>🔗 Vous devez d’abord connecter votre Google Agenda :</p>
        <a href="/authorize">Se connecter à Google</a>
        '''
    return '''
        <h2>Assistant Álamo Agenda</h2>
        <form method="post" action="/execute">
            <label>🗓️ Donnez une commande :</label><br>
            <input type="text" name="command" placeholder="Ex : Efface le rendez-vous Fnac le 10 octobre" style="width:400px;">
            <button type="submit">Envoyer</button>
        </form>
    '''

# --- AUTHENTIFICATION GOOGLE ---
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

    # Sauvegarde locale du token
    with open("token.json", "w") as token_file:
        json.dump(session['credentials'], token_file)

    return "✅ Connexion Google Agenda réussie ! L’assistant peut maintenant gérer vos rendez-vous."

# --- COMMANDE EN LANGAGE NATUREL ---
@app.route('/execute', methods=['POST'])
def execute():
    user_command = request.form['command']

    # Vérifier les credentials
    if 'credentials' not in session:
        return "❌ Non connecté à Google Calendar. Veuillez d’abord passer par /authorize."

    creds = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=creds)

    # --- INTERPRÉTATION AVEC GPT ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui gère Google Agenda. Identifie clairement si l'utilisateur veut ajouter, supprimer ou lister un événement, et les détails de date, heure, titre."},
            {"role": "user", "content": user_command}
        ]
    )
    interpretation = response.choices[0].message.content.lower()

    # --- SUPPRESSION D’UN ÉVÉNEMENT ---
    if "efface" in user_command.lower() or "supprime" in user_command.lower():
        events = service.events().list(calendarId='primary').execute().get('items', [])
        deleted = False
        for event in events:
            if any(keyword in event.get("summary", "").lower() for keyword in ["fnac", "rendez-vous", "rdv"]) \
               and ("octobre" in user_command.lower() or "10" in user_command.lower()):
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                deleted = True
        result = "✅ Rendez-vous supprimé !" if deleted else "❌ Aucun rendez-vous trouvé à supprimer."

    # --- AJOUT D’UN ÉVÉNEMENT ---
    elif "ajoute" in user_command.lower() or "crée" in user_command.lower():
        now = datetime.datetime.utcnow()
        event = {
            'summary': 'Nouveau rendez-vous',
            'start': {'dateTime': (now + datetime.timedelta(hours=1)).isoformat() + 'Z', 'timeZone': 'Europe/Paris'},
            'end': {'dateTime': (now + datetime.timedelta(hours=2)).isoformat() + 'Z', 'timeZone': 'Europe/Paris'},
        }
        service.events().insert(calendarId='primary', body=event).execute()
        result = "✅ Événement ajouté avec succès !"

    else:
        result = f"🧠 Commande comprise mais non actionnable : {interpretation}"

    return render_template_string(f'''
        <h2>Assistant Álamo Agenda</h2>
        <p>Commande : <b>{user_command}</b></p>
        <p><b>Résultat :</b> {result}</p>
        <a href="/">↩ Retour</a>
    ''')

# --- FONCTION UTILITAIRE ---
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
    app.run(host='0.0.0.0', port=10000)
