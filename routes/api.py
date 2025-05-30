from flask import jsonify, request, send_from_directory
import geopandas as gpd
from app import app,db
from models import Gouvernorat
import os
import json




@app.route('/geojson/<layer_name>')
def serve_geojson(layer_name):
    return send_from_directory(
        os.path.join(app.static_folder, 'geojson'),
        f"{layer_name}.geojson"
    )
@app.route('/get-coverage-layer', methods=['POST'])
def get_coverage_layer():
    data = request.get_json()
    gouvernorat = data.get('gouvernorat')
    delegation = data.get('delegation')
    operator = data.get('operator')
    coverage_type = data.get('coverage_type')
    secteur = data.get('secteur')
    selected_year = data.get('year')
    selected_month = data.get('month')

    # Validate required parameters
    if not all([gouvernorat, operator, coverage_type]):
        return jsonify({'error': 'Missing parameters'}), 400

    # Correct operator name using mapping
    operator_mapping = {
        "Tunisie Telecom": "Telecom TN",
        "Ooredoo TN": "Ooredoo TN",
        "Orange TN": "Orange TN"
    }
    operator = operator_mapping.get(operator, operator)

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

    # Get most recent entry matching filters
    gouv_record = query.order_by(Gouvernorat.date_upload.desc()).first()

    if not gouv_record:
        error_msg = f"Aucune donnée trouvée pour {gouvernorat}"
        if selected_year:
            error_msg += f" en {selected_year}"
            if selected_month:
                error_msg += f"-{selected_month}"
        return jsonify({'error': error_msg}), 404

    dossier_path = gouv_record.dossier_copie

    # Determine the base path and target folder based on the level (secteur, delegation, governorate)
    base_path = None
    target_folder = None

    if secteur and delegation:
        # Sector level
        base_path = os.path.join(dossier_path, delegation, "SHP Secteurs")
        target_folder = f"{secteur} {operator}_{coverage_type}"
    elif delegation:
        # Delegation level
        base_path = os.path.join(dossier_path, delegation, "SHP Délégations")
        target_folder = f"{delegation} {operator}_{coverage_type}"
    else:
        # Governorate level
        base_path = os.path.join(dossier_path, "SHP GOUVERNORAT")
        target_folder = f"{gouvernorat} {operator}_{coverage_type}"

    shp_folder = os.path.join(base_path, target_folder)
    
    # Check if the SHP folder exists
    if not os.path.exists(shp_folder):
        return jsonify({
            'error': f'Folder not found: {target_folder}',
            'searched_path': shp_folder
        }), 404

    # Find the SHP file
    shp_files = [f for f in os.listdir(shp_folder) if f.endswith('.shp')]
    if not shp_files:
        return jsonify({'error': 'No SHP file found'}), 404

    # Convert SHP to GeoJSON if not already done
    shp_path = os.path.join(shp_folder, shp_files[0])
    geojson_path = os.path.splitext(shp_path)[0] + '.geojson'
    
    if not os.path.exists(geojson_path):
        try:
            gdf = gpd.read_file(shp_path)
            gdf.to_file(geojson_path, driver='GeoJSON')
        except Exception as e:
            return jsonify({'error': f'Conversion error: {str(e)}'}), 500

    # Return the GeoJSON data
    with open(geojson_path, 'r') as f:
        geojson_data = json.load(f)

    return jsonify({'geojson': geojson_data})

@app.route('/get-dates', methods=['POST'])
def get_dates():
    data = request.get_json()
    gouvernorat = data.get('gouvernorat')
    selected_year = data.get('year')

    if not gouvernorat:
        return jsonify({'error': 'Gouvernorat manquant'}), 400

    query = Gouvernorat.query.filter(
        Gouvernorat.gouvernorat.ilike(gouvernorat),
        Gouvernorat.visible == 1
    )

    if selected_year:
        query = query.filter(db.extract('year', Gouvernorat.date_upload) == selected_year)

    entries = query.all()
    dates = [entry.date_upload for entry in entries if entry.date_upload]

    if selected_year:
        months = sorted({date.month for date in dates})
        months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
        months_names = [months_fr[month - 1] for month in months]
        return jsonify({'months': months_names})
    else:
        years = sorted({date.year for date in dates}, reverse=True)
        return jsonify({'years': years})
