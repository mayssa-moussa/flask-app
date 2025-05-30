from flask import render_template, jsonify, request, session, make_response
from .auth import login_required
from app import app, db
from models import Gouvernorat
from gouvernorats_data import charger_structure
from .utils import copy_filtered_directories, verify_folder_structure, copy_all_data
import os
import shutil
import traceback
from datetime import datetime



@app.route('/admin/upload', methods=['GET','POST'])
@login_required
def admin_page():
    
    # Charger les données depuis le fichier Excel
    fichier_excel = fichier_excel = os.path.join(app.static_folder, 'Mesures.xlsx')
    data = charger_structure(fichier_excel)
    
    # Récupérer les gouvernorats depuis la base de données
    gouvernorats = Gouvernorat.query.order_by(Gouvernorat.date_upload.desc()).all()
    
    # Passer les données au template
    response = make_response(render_template(
        'admin.html', 
        data=data,
        gouvernorats=gouvernorats  # Ajout des données de la base de données
    ))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/admin/handle_upload', methods=['POST'])
@login_required
def handle_upload():
    try:
        data = request.get_json()
        gouvernorat = data.get('gouvernorat')
        source_path = data.get('gouvFolderPath')

        if not gouvernorat or not source_path:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Vérification du nom du dossier
        path_parts = [p for p in os.path.normpath(source_path).split(os.sep) if p]
        last_folder = path_parts[-1].upper() if path_parts else ''
        if last_folder != gouvernorat.upper():
            return jsonify({
                'success': False,
                'message': f"Le dernier dossier du chemin doit être '{gouvernorat}'. Vous avez entré: '{last_folder}'"
            }), 400

        # Vérifications des prérequis
        stats_gouv_path = os.path.join(source_path, 'Statistiques Gouvernorat')
        if not os.path.exists(stats_gouv_path):
            return jsonify({'success': False, 'message': "Le dossier 'Statistiques Gouvernorat' est manquant."}), 400

        errors = []

        # Vérification du fichier Autres Indicateurs
        indicateurs_files = [
            'Autres Indicateurs.xls',
            'Autres Indicateurs.xlsx',
            'Autres indicateurs.xls',
            'Autres indicateurs.xlsx'
        ]
        indicateurs_found = any(os.path.exists(os.path.join(stats_gouv_path, f)) for f in indicateurs_files)
        if not indicateurs_found:
            errors.append("manque Autres Indicateurs")

        # Vérification du dossier SHP GOUVERNORAT
        shp_gouv_src = os.path.join(stats_gouv_path, 'SHP GOUVERNORAT')
        if not os.path.exists(shp_gouv_src) or len(os.listdir(shp_gouv_src)) == 0:
            errors.append("le dossier SHP GOUVERNORAT est vide")

        # Vérification des délégations
        for item in os.listdir(source_path):
            item_path = os.path.join(source_path, item)
            if os.path.isdir(item_path) and item != 'Statistiques Gouvernorat':
                # Vérification SHP Délégations
                shp_deleg_src = os.path.join(item_path, 'SHP Délégations')
                if not os.path.exists(shp_deleg_src) or len(os.listdir(shp_deleg_src)) == 0:
                    errors.append(f"le dossier SHP Délégations pour {item} est vide")
                # Vérification SHP Secteurs
                shp_secteurs_src = os.path.join(item_path, 'SHP Secteurs')
                if not os.path.exists(shp_secteurs_src) or len(os.listdir(shp_secteurs_src)) == 0:
                    errors.append(f"le dossier SHP Secteurs pour {item} est vide")

        if errors:
            error_message = "Le traitement pour ce gouvernorat n'est pas terminé :\n* " + "\n* ".join(errors)
            return jsonify({'success': False, 'message': error_message}), 400

        # Création du dossier cible
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        uploads_dir = os.path.join(desktop_path, 'Uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)

        now = datetime.now()
        folder_name = f"{gouvernorat}_{now.strftime('%Y-%m-%d')}"
        target_dir = os.path.join(uploads_dir, folder_name)
        os.makedirs(target_dir)

        # Chemin vers le dossier Statistiques Gouvernorat
        stats_gouv_path = os.path.join(source_path, 'Statistiques Gouvernorat')
        
        # 1. Copier le dossier SHP GOUVERNORAT
        shp_gouv_src = os.path.join(stats_gouv_path, 'SHP GOUVERNORAT')
        shp_gouv_dest = os.path.join(target_dir, 'SHP GOUVERNORAT')
        if os.path.exists(shp_gouv_src):
            copy_filtered_directories(shp_gouv_src, shp_gouv_dest)

        # 2. Copier le fichier Autres Indicateurs.xls (avec différentes extensions possibles)
        indicateurs_files = [
            'Autres Indicateurs.xls',
            'Autres Indicateurs.xlsx',
            'Autres indicateurs.xls',
            'Autres indicateurs.xlsx'
        ]
        
        indicateurs_copie = False
        for filename in indicateurs_files:
            indicateurs_src = os.path.join(stats_gouv_path, filename)
            if os.path.exists(indicateurs_src):
                shutil.copy2(indicateurs_src, os.path.join(target_dir, filename))
                indicateurs_copie = True
                break
        
        if not indicateurs_copie:
            return jsonify({
                'success': False, 
                'message': 'Fichier Autres Indicateurs non trouvé dans le dossier source'
            }), 400

        # 3. Parcourir les sous-dossiers (délégations) sauf Statistiques Gouvernorat
        for item in os.listdir(source_path):
            item_path = os.path.join(source_path, item)
            if os.path.isdir(item_path) and item != 'Statistiques Gouvernorat':
                # Créer un sous-dossier pour la délégation
                delegation_dir = os.path.join(target_dir, item)
                os.makedirs(delegation_dir, exist_ok=True)
                
                # Copier SHP Délégations
                shp_deleg_src = os.path.join(item_path, 'SHP Délégations')
                shp_deleg_dest = os.path.join(delegation_dir, 'SHP Délégations')
                if os.path.exists(shp_deleg_src):
                    copy_filtered_directories(shp_deleg_src, shp_deleg_dest)
                
                # Copier SHP Secteurs
                shp_secteurs_src = os.path.join(item_path, 'SHP Secteurs')
                shp_secteurs_dest = os.path.join(delegation_dir, 'SHP Secteurs')
                if os.path.exists(shp_secteurs_src):
                    copy_filtered_directories(shp_secteurs_src, shp_secteurs_dest)

        # Enregistrement en base de données
        new_gouv = Gouvernorat(
        gouvernorat=gouvernorat,
        date_upload=now,
        dossier_copie=target_dir,  # Champ renommé
        dossier_origine=source_path  # Nouveau champ
    )
        db.session.add(new_gouv)
        db.session.commit()

        return jsonify({
        'success': True, 
        'message': 'Dossier créé avec succès!',
        'dossier': target_dir,
        'dossier_origine': source_path,  # Ajouter cette ligne
        'gouvernorat': new_gouv.gouvernorat,
        'date_upload': new_gouv.date_upload.strftime('%Y-%m-%d'),
        'id': new_gouv.id,
        'visible': new_gouv.visible
    })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@app.route('/admin/toggle_visibility/<int:gouv_id>', methods=['POST'])
@login_required
def toggle_visibility(gouv_id):
    try:
        data = request.get_json()
        visible = data.get('visible', False)
        
        gouv = Gouvernorat.query.get_or_404(gouv_id)
        gouv.visible = visible
        db.session.commit()
        
        return jsonify({'success': True, 'visible': gouv.visible})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/update_visibility', methods=['POST'])
@login_required
def update_visibility():
    data = request.get_json()
    gouv_id = data['id']
    new_visibility = data['visible']
    
    try:
        gouv = Gouvernorat.query.get(gouv_id)
        if gouv:
            gouv.visible = new_visibility
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Gouvernorat non trouvé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/update_gouvernorat/<int:id>', methods=['POST'])
@login_required
def update_gouvernorat(id):
    try:
        data = request.get_json()
        gouvernorat = Gouvernorat.query.get_or_404(id)
        new_source_path = data.get('gouvFolderPath')
        new_date_str = data.get('date')

        # Validation de base
        if not new_source_path or not new_date_str:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        new_date = datetime.strptime(new_date_str, '%Y-%m-%d')
        needs_copy = False

        # Si le chemin source a changé
        if new_source_path != gouvernorat.dossier_origine:
            # Réutiliser la logique de vérification de handle_upload
            path_parts = [p for p in os.path.normpath(new_source_path).split(os.sep) if p]
            last_folder = path_parts[-1].upper() if path_parts else ''
            
            if last_folder != gouvernorat.gouvernorat.upper():
                return jsonify({
                    'success': False,
                    'message': f"Le dernier dossier doit être '{gouvernorat.gouvernorat}'. Actuel: '{last_folder}'"
                }), 400

            # Vérifier la structure du dossier
            errors = verify_folder_structure(new_source_path, gouvernorat.gouvernorat)
            if errors:
                return jsonify({'success': False, 'message': errors}), 400
            
            needs_copy = True

        # Si besoin de copie ou date modifiée
        if needs_copy or new_date.date() != gouvernorat.date_upload:
            # Créer nouveau dossier si nécessaire
            if needs_copy:
                desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                uploads_dir = os.path.join(desktop_path, 'Uploads')
                folder_name = f"{gouvernorat.gouvernorat}_{new_date.strftime('%Y-%m-%d')}"
                new_target_dir = os.path.join(uploads_dir, folder_name)
                
                if os.path.exists(new_target_dir):
                    shutil.rmtree(new_target_dir)
                
                os.makedirs(new_target_dir)
                copy_all_data(new_source_path, new_target_dir)
                
                # Supprimer ancien dossier si différent
                if gouvernorat.dossier_copie != new_target_dir and os.path.exists(gouvernorat.dossier_copie):
                    shutil.rmtree(gouvernorat.dossier_copie)
                
                gouvernorat.dossier_copie = new_target_dir
                gouvernorat.dossier_origine = new_source_path
            else:
                # Renommer le dossier existant si seule la date a changé
                desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                uploads_dir = os.path.join(desktop_path, 'Uploads')
                folder_name = f"{gouvernorat.gouvernorat}_{new_date.strftime('%Y-%m-%d')}"
                new_target_dir = os.path.join(uploads_dir, folder_name)

                if new_target_dir != gouvernorat.dossier_copie:
                    # S'assurer que le dossier Uploads existe
                    if not os.path.exists(uploads_dir):
                        os.makedirs(uploads_dir)
                    
                    # Supprimer le nouveau dossier s'il existe déjà
                    if os.path.exists(new_target_dir):
                        shutil.rmtree(new_target_dir)
                    
                    # Renommer l'ancien dossier
                    os.rename(gouvernorat.dossier_copie, new_target_dir)
                    
                    # Mettre à jour le chemin dans la base de données
                    gouvernorat.dossier_copie = new_target_dir
            
            # Mettre à jour la date dans tous les cas
            gouvernorat.date_upload = new_date

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Modifications enregistrées',
            'id': gouvernorat.id,
            'gouvernorat': gouvernorat.gouvernorat,
            'date_upload': gouvernorat.date_upload.strftime('%Y-%m-%d'),
            'dossier_origine': gouvernorat.dossier_origine
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@app.route('/delete_gouvernorat/<int:gouv_id>', methods=['DELETE'])
@login_required
def delete_gouvernorat(gouv_id):
    try:
        gouv = Gouvernorat.query.get_or_404(gouv_id)
        
        
        if os.path.exists(gouv.dossier_copie):
            shutil.rmtree(gouv.dossier_copie) 
            
        db.session.delete(gouv)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Gouvernorat supprimé avec succès'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500                

@app.route('/get_gouvernorat/<int:id>')
@login_required
def get_gouvernorat(id):
    gouv = Gouvernorat.query.get_or_404(id)
    return jsonify({
        'gouvernorat': gouv.gouvernorat,
        'date_upload': gouv.date_upload.strftime('%Y-%m-%d'),
        'dossier_origine': gouv.dossier_origine
    })