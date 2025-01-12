import requests
from flask import Flask, request, jsonify
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
# Allow only the frontend URL for CORS
CORS(app, resources={r"/*": {"origins": "https://sacramento-mello-roos.vercel.app"}})

@app.route('/get-tax-details', methods=['GET'])
def get_tax_details():
    # Get parameters from the request
    street_number = request.args.get('street_number')
    street_name = request.args.get('street_name')
    city = request.args.get('city')

    print(f"Street Number: {street_number}, Street Name: {street_name}, City: {city}")  # Debugging line

    # ArcGIS API to get parcel number
    parcel_api_url = "https://services1.arcgis.com/5NARefyPVtAeuJPU/arcgis/rest/services/Parcels/FeatureServer/0/query"
    where_clause = f"STREET_NBR='{street_number}' AND STREET_NAM='{street_name}' AND CITY='{city}'"
    params = {
        'where': where_clause,
        'outFields': '*',
        'f': 'json'
    }

    # Fetch parcel data
    parcel_response = requests.get(parcel_api_url, params=params)
    if parcel_response.status_code != 200:
        return jsonify({"error": f"Parcel API request failed with status code {parcel_response.status_code}, response: {parcel_response.text}"}), 400

    parcel_data = parcel_response.json()

    # Ensure parcel data is valid
    if 'features' not in parcel_data or len(parcel_data['features']) == 0:
        return jsonify({"error": "No parcel data found"}), 400

    parcel_number = parcel_data['features'][0]['attributes'].get('APN')
    if not parcel_number:
        return jsonify({"error": "Parcel number not found"}), 400

    # Fetch bill details using the parcel number
    bill_summary_url = f"https://eproptax.saccounty.net/servicev2/eproptax.svc/rest/BillSummary?parcel={parcel_number}"
    bill_response = requests.get(bill_summary_url)
    if bill_response.status_code != 200:
        return jsonify({"error": f"Bill API request failed with status code {bill_response.status_code}, response: {bill_response.text}"}), 400

    bill_data = bill_response.json()

    # Ensure bill data is valid
    if not bill_data.get('Success'):
        return jsonify({"error": "Failed to retrieve bill data"}), 400

    # Get the bill number and roll date
    bill_number = bill_data['Bills'][0]['BillNumber']
    roll_date = bill_data['Bills'][0]['RollDate']

    # Fetch levy details using the bill number and current year
    levy_url = f"https://eproptax.saccounty.net/servicev2/eproptax.svc/rest/DirectLevy?rollYear={roll_date}&billNumber={bill_number}"
    levy_response = requests.get(levy_url)
    if levy_response.status_code != 200:
        return jsonify({"error": f"Levy API request failed with status code {levy_response.status_code}, response: {levy_response.text}"}), 400

    levy_data = levy_response.json()

    # Ensure levy data is valid
    if not levy_data.get('Success'):
        return jsonify({"error": "Failed to retrieve levy data"}), 400

    # Prepare the response
    response_data = {
        "total_amount": levy_data['BillAmount'],
        "levy_total": levy_data['LevyTotal'],
        "levies": levy_data['Levies']
    }

    return jsonify(response_data)
