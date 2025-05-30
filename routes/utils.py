import os
import shutil

def copy_filtered_directories(src, dest):
    """Copie uniquement les sous-dossiers contenant GSM ou UMTS dans leur nom (insensible à la casse)"""
    os.makedirs(dest, exist_ok=True)
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        if os.path.isdir(src_path):
            # Vérification insensible à la casse
            if any(keyword.lower() in item.lower() for keyword in ['GSM', 'UMTS']):
                shutil.copytree(
                    src_path,
                    os.path.join(dest, item),
                    dirs_exist_ok=True
                )

def verify_folder_structure(source_path, gouvernorat):
    errors = []
    stats_gouv_path = os.path.join(source_path, 'Statistiques Gouvernorat')
    
    if not os.path.exists(stats_gouv_path):
        errors.append("Le dossier 'Statistiques Gouvernorat' est manquant.")
    
    indicateurs_files = ['Autres Indicateurs.xls', 'Autres Indicateurs.xlsx',
                        'Autres indicateurs.xls', 'Autres indicateurs.xlsx']
    if not any(os.path.exists(os.path.join(stats_gouv_path, f)) for f in indicateurs_files):
        errors.append("Fichier Autres Indicateurs manquant")
    
    shp_gouv_src = os.path.join(stats_gouv_path, 'SHP GOUVERNORAT')
    if not os.path.exists(shp_gouv_src) or len(os.listdir(shp_gouv_src)) == 0:
        errors.append("SHP GOUVERNORAT vide")
    
    for item in os.listdir(source_path):
        item_path = os.path.join(source_path, item)
        if os.path.isdir(item_path) and item != 'Statistiques Gouvernorat':
            if not os.path.exists(os.path.join(item_path, 'SHP Délégations')):
                errors.append(f"SHP Délégations manquant pour {item}")
            if not os.path.exists(os.path.join(item_path, 'SHP Secteurs')):
                errors.append(f"SHP Secteurs manquant pour {item}")
    
    return "\n".join(errors) if errors else None

def copy_all_data(source_path, target_dir):
    # Copier Statistiques Gouvernorat
    stats_gouv_src = os.path.join(source_path, 'Statistiques Gouvernorat')
    shp_gouv_dest = os.path.join(target_dir, 'SHP GOUVERNORAT')
    copy_filtered_directories(os.path.join(stats_gouv_src, 'SHP GOUVERNORAT'), shp_gouv_dest)
    
    # Copier Autres Indicateurs
    for fname in ['Autres Indicateurs.xls', 'Autres Indicateurs.xlsx',
                 'Autres indicateurs.xls', 'Autres indicateurs.xlsx']:
        src = os.path.join(stats_gouv_src, fname)
        if os.path.exists(src):
            shutil.copy2(src, target_dir)
            break
    
    # Copier délégations
    for item in os.listdir(source_path):
        item_path = os.path.join(source_path, item)
        if os.path.isdir(item_path) and item != 'Statistiques Gouvernorat':
            delegation_dir = os.path.join(target_dir, item)
            os.makedirs(delegation_dir, exist_ok=True)
            
            shp_deleg_src = os.path.join(item_path, 'SHP Délégations')
            if os.path.exists(shp_deleg_src):
                copy_filtered_directories(shp_deleg_src, os.path.join(delegation_dir, 'SHP Délégations'))
            
            shp_secteurs_src = os.path.join(item_path, 'SHP Secteurs')
            if os.path.exists(shp_secteurs_src):
                copy_filtered_directories(shp_secteurs_src, os.path.join(delegation_dir, 'SHP Secteurs'))
