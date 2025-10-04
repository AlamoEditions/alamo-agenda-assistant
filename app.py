# =====================================
# 🔗 ROUTE /command : pour ChatGPT
# =====================================
from flask import request
import json
import datetime

@app.route('/command', methods=['POST'])
def command():
    """
    Cette route reçoit des instructions textuelles comme :
    "supprime le rendez-vous Fnac le 10 octobre"
    et agit automatiquement sur Google Agenda.
    """
    if 'credentials' not in session:
        return jsonify({"error": "Non connecté à Google Calendar. Visitez /authorize d'abord."}), 401

    creds = Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=creds)

    # Récupérer la commande texte envoyée par ChatGPT
    data = request.get_json()
    user_text = data.get("text", "").lower()

    # Supprimer un événement
    if "efface" in user_text or "supprime" in user_text:
        try:
            # Exemple : "efface le rdv fnac le 10 octobre"
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
