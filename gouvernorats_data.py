import pandas as pd

def charger_structure(fichier_excel):
    data = {}
    xls = pd.ExcelFile(fichier_excel)
    feuilles = xls.sheet_names

    for feuille in feuilles:
        df = pd.read_excel(fichier_excel, sheet_name=feuille)
        df.columns = [col.strip() for col in df.columns]

        for _, row in df.iterrows():
            gouvernorat = feuille.strip()
            delegation = str(row['Délégation']).strip()
            secteur = str(row['Secteur']).strip()

            if gouvernorat not in data:
                data[gouvernorat] = {}

            if delegation not in data[gouvernorat]:
                data[gouvernorat][delegation] = []

            if secteur and secteur not in data[gouvernorat][delegation]:
                data[gouvernorat][delegation].append(secteur)

    return data
