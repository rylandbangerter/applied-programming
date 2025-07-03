import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate(r"C:\Users\taylo\Downloads\moneyball-a1cab-firebase-adminsdk-fbsvc-250a320975.json")
firebase_admin.initialize_app(cred)

from firebase_admin import firestore
import csv
def add_csv_to_playerData(csv_file_path):
    db = firestore.client()
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            db.collection('playerData').add(dict(row))


def format_name_first_last(name):
    parts = name.strip().split()
    return '_'.join(parts)

def add_formatted_names_to_playerData(csv_file_path):
        db = firestore.client()
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    name = row[0].strip()
                    formatted_name = format_name_first_last(name)
                    parts = name.split()
                    firstname = parts[0] if len(parts) > 0 else ""
                    lastname = parts[1] if len(parts) > 1 else ""
                    doc_data = {
                        "first_name": firstname,
                        "last_name": lastname
                    }
                    db.collection('playerData').document(formatted_name).set(doc_data)

def extract_column_2(input_csv, output_csv):
    with open(input_csv, newline='', encoding='utf-8') as infile, \
         open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        for row in reader:
            if len(row) > 1:
                writer.writerow([row[1]])



# Example usage:
# extract_column_2('merged_baseball_stats.csv', 'column2_only.csv')
# add_formatted_names_to_playerData('column2_only.csv')
def count_playerData_documents():
    db = firestore.client()
    docs = db.collection('playerData').stream()
    count = sum(1 for _ in docs)
    print(f"Total documents in playerData: {count}")
    return count

# count_playerData_documents()


def delete_all_from_playerData():
    db = firestore.client()
    docs = db.collection('playerData').stream()
    for doc in docs:
        doc.reference.delete()


mlb_teams = [
    {
        "abbreviation": "ARI",
        "city": "Phoenix",
        "name": "Diamondbacks"
    },
    {
        "abbreviation": "ATL",
        "city": "Atlanta",
        "name": "Braves"
    },
    {
        "abbreviation": "BAL",
        "city": "Baltimore",
        "name": "Orioles"
    },
    {
        "abbreviation": "BOS",
        "city": "Boston",
        "name": "Red Sox"
    },
    {
        "abbreviation": "CHC",
        "city": "Chicago",
        "name": "Cubs"
    },
    {
        "abbreviation": "CHW",
        "city": "Chicago",
        "name": "White Sox"
    },
    {
        "abbreviation": "CIN",
        "city": "Cincinnati",
        "name": "Reds"
    },
    {
        "abbreviation": "CLE",
        "city": "Cleveland",
        "name": "Guardians"
    },
    {
        "abbreviation": "COL",
        "city": "Denver",
        "name": "Rockies"
    },
    {
        "abbreviation": "DET",
        "city": "Detroit",
        "name": "Tigers"
    },
    {
        "abbreviation": "HOU",
        "city": "Houston",
        "name": "Astros"
    },
    {
        "abbreviation": "KC",
        "city": "Kansas City",
        "name": "Royals"
    },
    {
        "abbreviation": "LAA",
        "city": "Los Angeles",
        "name": "Angels"
    },
    {
        "abbreviation": "LAD",
        "city": "Los Angeles",
        "name": "Dodgers"
    },
    {
        "abbreviation": "MIA",
        "city": "Miami",
        "name": "Marlins"
    },
    {
        "abbreviation": "MIL",
        "city": "Milwaukee",
        "name": "Brewers"
    },
    {
        "abbreviation": "MIN",
        "city": "Minneapolis",
        "name": "Twins"
    },
    {
        "abbreviation": "NYM",
        "city": "New York",
        "name": "Mets"
    },
    {
        "abbreviation": "NYY",
        "city": "New York",
        "name": "Yankees"
    },
    {
        "abbreviation": "OAK",
        "city": "Oakland",
        "name": "Athletics"
    },
    {
        "abbreviation": "PHI",
        "city": "Philadelphia",
        "name": "Phillies"
    },
    {
        "abbreviation": "PIT",
        "city": "Pittsburgh",
        "name": "Pirates"
    },
    {
        "abbreviation": "SD",
        "city": "San Diego",
        "name": "Padres"
    },
    {
        "abbreviation": "SF",
        "city": "San Francisco",
        "name": "Giants"
    },
    {
        "abbreviation": "SEA",
        "city": "Seattle",
        "name": "Mariners"
    },
    {
        "abbreviation": "STL",
        "city": "St. Louis",
        "name": "Cardinals"
    },
    {
        "abbreviation": "TB",
        "city": "St. Petersburg",
        "name": "Rays"
    },
    {
        "abbreviation": "TEX",
        "city": "Arlington",
        "name": "Rangers"
    },
    {
        "abbreviation": "TOR",
        "city": "Toronto",
        "name": "Blue Jays"
    },
    {
        "abbreviation": "WSH",
        "city": "Washington D.C.",
        "name": "Nationals"
    }
]

def add_teams_to_firestore():
    db = firestore.client()
    for team in mlb_teams:
        team_ref = db.collection('teams').document(team['abbreviation'])
        team_ref.set({
            'city': team['city'],
            'name': team['name']
        })

add_teams_to_firestore()

# Example usage:
# delete_all_from_playerData()