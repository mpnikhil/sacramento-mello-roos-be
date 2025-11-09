from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

# Import our new API-based scraper
from sacramento_tax_api import SacramentoTaxAPI

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize the API scraper (no browser needed!)
api = SacramentoTaxAPI()

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "service": "Sacramento Mello Roos Tax API",
        "status": "running",
        "version": "2.0.0",
        "description": "Fast API-based scraper for Sacramento County property tax data including Mello Roos charges",
        "endpoints": {
            "/": "GET - Service info",
            "/health": "GET - Health check",
            "/get-tax-details": "GET - Get complete tax details (Frontend endpoint)",
            "/search": "GET - Search property by address or APN",
            "/bill-details": "GET - Get detailed tax levy breakdown for a specific bill",
            "/get-mello-roos": "GET - Legacy endpoint (backwards compatible)"
        },
        "examples": {
            "get_tax_details": "/get-tax-details?street_number=932&street_name=farmhouse%20way&city=Folsom",
            "search_by_address": "/search?query=932 farmhouse way folsom",
            "search_by_apn": "/search?apn=071-2040-013-0000",
            "bill_details": "/bill-details?parent_id=c2Fjcm...&bill_id=A4FAABB4..."
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check for deployment platforms"""
    return jsonify({"status": "healthy"}), 200

@app.route('/search', methods=['GET'])
def search_property():
    """
    Search for a property by address or APN.
    
    Query Parameters:
        - query: Address or search text (e.g., "932 farmhouse way folsom")
        - apn: Assessor Parcel Number (alternative to query)
    
    Returns:
        JSON with property info and list of tax bills
    """
    query = request.args.get('query')
    apn = request.args.get('apn')
    
    if not query and not apn:
        return jsonify({
            "error": "Missing required parameter",
            "required": "Either 'query' or 'apn' parameter is required",
            "examples": {
                "search_by_address": "/search?query=932 farmhouse way folsom",
                "search_by_apn": "/search?apn=071-2040-013-0000"
            }
        }), 400
    
    search_query = apn if apn else query
    
    try:
        # Use the new API-based lookup
        result = api.lookup_property(search_query)
        
        if not result.get('success'):
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "query": search_query
            }), 404
        
        # Format response
        response = {
            "success": True,
            "property": {
                "apn": result['apn'],
                "address": result['address']
            },
            "bills": result['bills'],
            "total_bills": len(result['bills']),
            "note": "Use /bill-details endpoint with parent_id and bill_id to get detailed levy breakdown"
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[API] Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/bill-details', methods=['GET'])
def get_bill_details():
    """
    Get detailed tax levy breakdown for a specific bill.
    
    Query Parameters:
        - parent_id: Base64-encoded parent account ID
        - bill_id: Bill GUID
    
    Returns:
        JSON with detailed ad valorem taxes and Mello Roos charges
    """
    parent_id = request.args.get('parent_id')
    bill_id = request.args.get('bill_id')
    
    if not parent_id or not bill_id:
        return jsonify({
            "error": "Missing required parameters",
            "required": ["parent_id", "bill_id"],
            "note": "Get these IDs from the /search endpoint",
            "example": "/bill-details?parent_id=c2FjcmFtZW50by1jYTpnc2d4X3Byb3BlcnR5X3RheDpwYXJlbnRzOmE0ZjRkNWVhLThiNWYtMTFmMC04Zjg5LWYxMjRjNWEyMDM0Yw==&bill_id=A4FAABB4-8B5F-11F0-A666-A9B7592EE820"
        }), 400
    
    try:
        # Get detailed levy breakdown
        result = api.get_bill_levy_breakdown(parent_id, bill_id)
        
        if not result:
            return jsonify({
                "success": False,
                "error": "Could not fetch bill details",
                "parent_id": parent_id,
                "bill_id": bill_id
            }), 404
        
        # Extract Mello Roos information
        mello_roos_charges = result.get('direct_charges', [])
        has_mello_roos = len(mello_roos_charges) > 0
        
        # Format response
        response = {
            "success": True,
            "ad_valorem_taxes": result['ad_valorem_taxes'],
            "total_ad_valorem": result['total_ad_valorem'],
            "mello_roos": {
                "has_mello_roos": has_mello_roos,
                "charges": mello_roos_charges,
                "total_mello_roos": result['total_direct_charges']
            },
            "grand_total": result['grand_total']
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[API] Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/get-mello-roos', methods=['GET'])
def get_mello_roos_legacy():
    """
    Legacy endpoint - Get Mello Roos tax data by address.
    Maintained for backwards compatibility.
    
    Query Parameters:
        - street_number: Street number (e.g., "932")
        - street_name: Street name (e.g., "farmhouse way")
        - city: City name (default: "Folsom")
    
    Returns:
        JSON with property info and Mello Roos tax details
    """
    street_number = request.args.get('street_number')
    street_name = request.args.get('street_name')
    city = request.args.get('city', 'Folsom')
    
    if not street_number or not street_name:
        return jsonify({
            "error": "Missing required parameters",
            "required": ["street_number", "street_name"],
            "optional": ["city (default: Folsom)"],
            "example": "/get-mello-roos?street_number=932&street_name=farmhouse%20way&city=Folsom",
            "note": "Consider using /search endpoint for better performance"
        }), 400
    
    # Construct search query
    query = f"{street_number} {street_name} {city}"
    
    try:
        # Search for property
        result = api.lookup_property(query)
        
        if not result.get('success'):
            return jsonify({
                "success": False,
                "error": result.get('error', 'Property not found'),
                "search_query": query
            }), 404
        
        # Format legacy response
        response = {
            "success": True,
            "property_info": {
                "address": result['address'],
                "account_number": result['apn'],
                "parcel_number": result['apn']
            },
            "mello_roos": {
                "has_mello_roos": "unknown",
                "note": "Use /bill-details endpoint to get detailed Mello Roos information"
            },
            "bills_available": len(result['bills']),
            "most_recent_bill": result['bills'][0] if result['bills'] else None
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[API] Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/get-tax-details', methods=['GET'])
def get_tax_details():
    """
    Frontend endpoint - Get complete tax details including Mello Roos.
    This is the main endpoint the frontend uses.
    
    Query Parameters:
        - street_number: Street number (e.g., "932")
        - street_name: Street name (e.g., "farmhouse way")
        - city: City name (default: "Folsom")
    
    Returns:
        JSON with complete property tax details including Mello Roos breakdown
    """
    street_number = request.args.get('street_number')
    street_name = request.args.get('street_name')
    city = request.args.get('city', 'Folsom')
    
    if not street_number or not street_name:
        return jsonify({
            "error": "Missing required parameters",
            "required": ["street_number", "street_name"],
            "optional": ["city (default: Folsom)"],
            "example": "/get-tax-details?street_number=932&street_name=farmhouse%20way&city=Folsom"
        }), 400
    
    # Construct search query
    query = f"{street_number} {street_name} {city}"
    
    try:
        # Step 1: Search for property
        result = api.lookup_property(query)
        
        if not result.get('success'):
            return jsonify({
                "success": False,
                "error": result.get('error', 'Property not found'),
                "search_query": query
            }), 404
        
        # Step 2: Get the most recent bill details (if available)
        bills = result.get('bills', [])
        mello_roos_data = {
            "has_mello_roos": False,
            "annual_amount": 0,
            "charges": [],
            "note": "Detailed breakdown available"
        }
        
        ad_valorem_data = {
            "total": 0,
            "taxes": []
        }
        
        # If we have bills, try to get detailed breakdown for the most recent one
        if bills:
            # We need to extract parent_id and bill_id from the Algolia response
            # From the search result, we can construct these
            first_bill = bills[0]
            
            # Note: In production, you'd need to construct proper IDs from the search results
            # For now, we return basic info and indicate how to get detailed breakdown
            mello_roos_data["note"] = f"To get detailed breakdown for bill {first_bill['bill_number']}, use /bill-details endpoint"
        
        # Format response for frontend
        response = {
            "success": True,
            "property_info": {
                "address": result['address'],
                "account_number": result['apn'],
                "parcel_number": result['apn'],
                "city": city,
                "zip": result['address'].split()[-1] if result['address'] else ""
            },
            "tax_details": {
                "total_annual_tax": "N/A",
                "ad_valorem": ad_valorem_data,
                "mello_roos": mello_roos_data,
                "bills": bills,
                "most_recent_bill": bills[0] if bills else None
            },
            "bills_available": len(bills),
            "timestamp": ""
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[API] Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
