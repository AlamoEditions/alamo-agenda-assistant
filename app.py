from flask import Flask, request, jsonify, redirect, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

# ---- Import OpenAI correctement ----
import openai

app = Flask(__name__)
app.secret_key = "super_secret_key"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ---- Initialisation OpenAI avec clé d'environnement ----
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def home():
    return "✅ Assistant Álamo Agenda en ligne et connecté."

# --- Étape 1 : Connexion à Google ---
@app.route("/authorize")
def authorize():
    flow = InstalledAppFlow.from_client_secrets_file(
        "/etc/secrets/credentials.json", SCOPES
    )
    flow.redirect_uri = "https://alamo-agenda-assistant.onrender.com/oauth2callback"

    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session["state"]
    flow = InstalledAppFlow.from_client_secrets_file(
        "/etc/secrets/credentials.json", SCOPES, state=state
    )
    flow.redirect_uri = "https://alamo-agenda-assistant.onrender.com/oauth2callback"

    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session["credentials"] = creds_to_dict(creds)

    return "✅ Connexion Google Agenda réussie ! Vous pouvez maintenant parler à votre assistant."


# --- Étape 2 : Traitement des commandes en langage naturel ---
@app.route("/command", methods=["POST"])
def handle_command():
    if "credentials" not in session:
        return jsonify({"error": "Non connecté à Google Calendar. Visitez /authorize."}), 401

    creds = Credentials(**session["credentials"])
    service = build("calendar", "v3", credentials=creds)

    user_command = request.json.get("command")

    # GPT analyse la commande
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un assistant connecté à Google Agenda. "
                    "Quand on te dit une phrase comme 'efface le rdv Fnac le 10 octobre', "
                    "tu dois répondre uniquement en JSON clair : "
                    "{'action': 'delete_event', 'summary': 'Fnac', 'date': '2025-10-10'} "
                    "ou {'action': 'add_event', 'summary': 'Réunion', 'start': '2025-10-10T10:00:00', 'end': '2025-10-10T11:00:00'}"
                ),
            },
            {"role": "user", "content": user_command},
        ],
    )

    try:
        instruction = eval(response.choices[0].message["content"])
    except Exception as e:
        return jsonify({"error": f"Impossible d’analyser la réponse GPT: {str(e)}"}), 400

    # Exécution
    if instruction["action"] == "delete_event":
        return delete_event(service, instruction)
    elif instruction["action"] == "add_event":
        return add_event(service, instruction)
    else:
        return jsonify({"error": "Action non reconnue"}), 400


def delete_event(service, instruction):
    date = instruction["date"]
    summary = instruction["summary"].lower()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=f"{date}T00:00:00Z",
        timeMax=f"{date}T23:59:59Z",
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    for event in events:
        if summary in event["summary"].lower():
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            return jsonify({"status": "success", "message": f"Événement '{event['summary']}' supprimé."})

    return jsonify({"status": "not_found", "message": "Aucun événement correspondant trouvé."})


def add_event(service, instruction):
    event = {
        "summary": instruction["summary"],
        "start": {"dateTime": instruction["start"], "timeZone": "Europe/Paris"},
        "end": {"dateTime": instruction["end"], "timeZone": "Europe/Paris"},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return jsonify({"status": "success", "event": created})


def creds_to_dict(creds):
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
