from flask import render_template, jsonify, request, send_from_directory
from app import app, db 
from gouvernorats_data import charger_structure
from models import Gouvernorat
import traceback
import os


@app.route('/')
def index():
    fichier_excel = fichier_excel = os.path.join(app.static_folder, 'Mesures.xlsx')
    data = charger_structure(fichier_excel)
    return render_template('index.html', data=data)

@app.route('/generate_graphs', methods=['POST'])
def generate_graphs():
    try:
        data = request.get_json()
        gouvernorat = data.get('gouvernorat')
        operateurs = data.get('operateurs')
        delegation = data.get('delegation')
        secteur = data.get('secteur')
        selected_year = data.get('year')
        selected_month = data.get('month')

        
        
        if not gouvernorat or not operateurs:
            return jsonify({"error": "Paramètres manquants"}), 400

        # Convert French month name to number
        month_number = None
        if selected_month:
            months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                         'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            try:
                month_number = months_fr.index(selected_month.lower()) + 1
            except ValueError:
                return jsonify({"error": "Mois invalide"}), 400

        query = Gouvernorat.query.filter(
        db.func.upper(Gouvernorat.gouvernorat) == gouvernorat.strip().upper(),
        Gouvernorat.visible == True).order_by(Gouvernorat.date_upload.desc())

        gouv_record = query.first()


        if selected_year:
            query = query.filter(db.extract('year', Gouvernorat.date_upload) == selected_year)
            if month_number:
                query = query.filter(db.extract('month', Gouvernorat.date_upload) == month_number)


        

        if not gouv_record:
            error_msg = f"Les données ne sont pas disponibles encore pour {gouvernorat}"
            if selected_year:
                error_msg += f" pour l'année {selected_year}"
                if selected_month:
                    error_msg += f" et le mois {selected_month}"
            return jsonify({"error": error_msg}), 404

        file_path = os.path.join(gouv_record.dossier_copie, "Autres Indicateurs.xlsx")
        # Afficher le chemin du dossier dans la console
        print(f"\n--- Chemin du dossier utilisé ---\n{gouv_record.dossier_copie}\n------------------------------")
        print(f"mois sélectionné : {selected_month}")
        print(f"année sélectionnée : {selected_year}")

        if not os.path.exists(file_path):
            return jsonify({
                "html": '<div class="alert alert-warning mt-4">Données non disponibles</div>'
            })

        # Generate appropriate graphs based on hierarchy level
        if secteur:
            from graphes_secteurs import generate_interactive_graphs_secteur
            html_content = generate_interactive_graphs_secteur(
                file_path, 
                operateurs,
                delegation,
                secteur
            )
        elif delegation:
            from graphes_délégation import generate_interactive_graphs_délégation
            html_content = generate_interactive_graphs_délégation(
                file_path, 
                operateurs,
                delegation
            )
        else:
            from graphes import generate_interactive_graphs
            html_content = generate_interactive_graphs(file_path, operateurs)

        return jsonify({"html": html_content})
        
        

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500