import numpy as np
import pandas as pd
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
import os
from models import db, Gouvernorat, Admin


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'votre_cle_secrete_complexe_ici'  # Ajouter une clé secrète
app.config['SESSION_TYPE'] = 'filesystem'  # Type de stockage des sessions
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration email (à adapter)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mayssa.moussa565@gmail.com'
app.config['MAIL_PASSWORD'] = 'ilaw qkio acpf jdxm'
app.config['SECURITY_PASSWORD_SALT'] = 'e4b1c9d6f23a4e56b6f2d2a5e9c3a1b2'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


# Initialisation de la base de données
db.init_app(app)
with app.app_context():
    db.create_all()

# Import des routes
from routes import main, auth, admin, api





def generer_carte_html():
    return """
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <div id="map" style="height: 80vh; width: 100%;"></div>
    <div id="layer-control" style="position: absolute; top: 20px; right: 20px; z-index: 1000; background: white; padding: 15px; border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h5>Couches cartographiques</h5>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="gouvernorats">
            <label class="form-check-label" for="gouvernorats">Gouvernorats</label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="delegations">
            <label class="form-check-label" for="delegations">Délégations</label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="secteurs">
            <label class="form-check-label" for="secteurs">Secteurs</label>
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Initialisation de la carte
        const map = L.map('map').setView([34.0, 9.0], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // Stockage des couches
        const layers = {
            gouvernorats_TN: null,
            delegations_TN: null,
            secteurs_TN: null
        };

        // Style commun
        const baseStyle = {
            weight: 2,
            opacity: 1,
            fillOpacity: 0.2
        };

        // Chargement des couches
        async function loadLayer(layerName) {
            const response = await fetch(/geojson/${layerName});
            const data = await response.json();
            
            layers[layerName] = L.geoJSON(data, {
                style: {
                    ...baseStyle,
                    color: layerName === 'gouvernorats_TN' ? '#ff0000' :
                           layerName === 'delegations_TN' ? '#0000ff' : '#00ff00'
                },
                onEachFeature: (feature, layer) => {
                    layer.bindPopup(feature.properties.name_fr || 'Nom inconnu');
                }
            }).addTo(map);
        }

        // Gestion des checkboxes
        document.getElementById('gouvernorats').addEventListener('change', (e) => {
            if(e.target.checked) {
                loadLayer('gouvernorats_TN');
            } else {
                if(layers.gouvernorats_TN) map.removeLayer(layers.gouvernorats_TN);
            }
        });

        document.getElementById('delegations').addEventListener('change', (e) => {
            if(e.target.checked) {
                loadLayer('delegations_TN');
            } else {
                if(layers.delegations_TN) map.removeLayer(layers.delegations_TN);
            }
        });

        document.getElementById('secteurs').addEventListener('change', (e) => {
            if(e.target.checked) {
                loadLayer('secteurs_TN');
            } else {
                if(layers.secteurs_TN) map.removeLayer(layers.secteurs_TN);
            }
        });
    </script>
    """

""" @app.route('/get_indicators', methods=['POST'])
def get_indicators():
    data = request.get_json()
    gouvernorat = data.get('gouvernorat')
    operators = data.get('operators')
    niveau = data.get('niveau')
    selected_year = data.get('year')
    selected_month = data.get('month')

    if not gouvernorat or not operators:
        return jsonify({"error": "Paramètres manquants"}), 400

    try:
        # Convert French month name to number
        month_number = None
        if selected_month:
            months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                         'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            try:
                month_number = months_fr.index(selected_month.lower()) + 1
            except ValueError:
                return jsonify({"error": "Mois invalide"}), 400

        # Build the query with date filters
        query = Gouvernorat.query.filter(
            Gouvernorat.gouvernorat.ilike(gouvernorat),
            Gouvernorat.visible == True
        )

        if selected_year:
            query = query.filter(db.extract('year', Gouvernorat.date_upload) == selected_year)
            if month_number:
                query = query.filter(db.extract('month', Gouvernorat.date_upload) == month_number)

        # Always order by date to get the most recent entry matching the filters
        query = query.order_by(Gouvernorat.date_upload.desc())
        gouv_record = query.first()

        if not gouv_record:
            error_msg = f"Les données ne sont pas disponibles encore pour {gouvernorat}"
            if selected_year:
                error_msg += f" pour l'année {selected_year}"
                if selected_month:
                    error_msg += f" et le mois {selected_month}"
            return jsonify({"error": error_msg}), 404
        
        
        dossier_path = gouv_record.dossier
        file_path = os.path.join(dossier_path, "Autres Indicateurs.xlsx")

        if not os.path.exists(file_path):
            return jsonify({"error": "Fichier non trouvé"}), 404

        html = generate_textual_report(file_path, operators)
        return jsonify({
            "html": html,
            "nom": gouvernorat
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500 """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
