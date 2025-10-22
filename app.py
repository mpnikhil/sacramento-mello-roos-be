from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper import PropertyTaxScraper
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize the scraper (runs browser in headless mode by default)
scraper = PropertyTaxScraper(
    headless=os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true'
)

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "service": "Sacramento Mello Roos Tax API",
        "status": "running",
        "version": "1.0.0",
        "description": "Scrapes Sacramento County property tax data and returns Mello Roos information",
        "endpoints": {
            "/get-mello-roos": "GET - Get Mello Roos tax by address",
            "/health": "GET - Health check"
        },
        "example": "/get-mello-roos?street_number=932&street_name=farmhouse%20way&city=Folsom"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check for deployment platforms"""
    return jsonify({"status": "healthy"}), 200

@app.route('/get-mello-roos', methods=['GET'])
def get_mello_roos():
    """
    Get Mello Roos tax data for a property by address.
    
    Query Parameters:
        - street_number: Street number (e.g., "932")
        - street_name: Street name (e.g., "farmhouse way")
        - city: City name (default: "Folsom")
    
    Returns:
        JSON with property info and Mello Roos tax details
    """
    # Get parameters from the request
    street_number = request.args.get('street_number')
    street_name = request.args.get('street_name')
    city = request.args.get('city', 'Folsom')
    
    # Validation
    if not street_number or not street_name:
        return jsonify({
            "error": "Missing required parameters",
            "required": ["street_number", "street_name"],
            "optional": ["city (default: Folsom)"],
            "example": "/get-mello-roos?street_number=932&street_name=farmhouse%20way&city=Folsom"
        }), 400
    
    print(f"[API] Scraping: {street_number} {street_name}, {city}")
    
    try:
        # Scrape the data using Playwright
        result = scraper.scrape_property_data(
            street_number=street_number,
            street_name=street_name,
            city=city
        )
        
        # Check for errors
        if result.get('error'):
            return jsonify({
                "success": False,
                "error": result['error'],
                "timestamp": result['timestamp']
            }), 500
        
        if not result.get('property_info'):
            return jsonify({
                "success": False,
                "error": "No property found for the given address",
                "search_query": result['search_query']
            }), 404
        
        # Extract Mello Roos information
        mello_roos_data = extract_mello_roos(result)
        
        # Format response
        response_data = {
            "success": True,
            "property_info": {
                "address": result['property_info'].get('address'),
                "city": result['property_info'].get('city'),
                "zip": result['property_info'].get('zip'),
                "account_number": result['property_info'].get('account_number'),
                "parcel_number": result['property_info'].get('parcel_number')
            },
            "mello_roos": mello_roos_data,
            "scraped_at": result['timestamp']
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[API] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

def extract_mello_roos(scraped_data):
    """
    Extract Mello Roos tax information from scraped data.
    
    Args:
        scraped_data: Dictionary containing scraped property data
        
    Returns:
        dict: Mello Roos tax information
    """
    mello_roos_info = {
        "has_mello_roos": False,
        "annual_amount": 0,
        "details": [],
        "bills": []
    }
    
    tax_details = scraped_data.get('tax_details')
    if not tax_details:
        return mello_roos_info
    
    bills = tax_details.get('bills', [])
    
    for bill in bills:
        bill_info = {
            "year": bill.get('year'),
            "bill_number": bill.get('bill_number'),
            "total_amount": bill.get('total_amount'),
            "mello_roos_items": []
        }
        
        # Look for Mello Roos in line items
        line_items = bill.get('line_items', [])
        for item in line_items:
            description = item.get('description', '').lower()
            
            # Check if this is a Mello Roos item
            if 'mello' in description or 'roos' in description or 'cfd' in description:
                mello_roos_info['has_mello_roos'] = True
                
                mello_roos_item = {
                    "description": item.get('description'),
                    "amount": item.get('amount', 0),
                    "code": item.get('code')
                }
                
                bill_info['mello_roos_items'].append(mello_roos_item)
                mello_roos_info['annual_amount'] += item.get('amount', 0)
        
        if bill_info['mello_roos_items']:
            mello_roos_info['bills'].append(bill_info)
    
    # If we found Mello Roos items, add summary
    if mello_roos_info['has_mello_roos']:
        # Get unique descriptions
        all_items = []
        for bill in mello_roos_info['bills']:
            all_items.extend(bill['mello_roos_items'])
        
        # Group by description
        descriptions = {}
        for item in all_items:
            desc = item['description']
            if desc not in descriptions:
                descriptions[desc] = {
                    "description": desc,
                    "total_amount": 0,
                    "occurrences": 0
                }
            descriptions[desc]['total_amount'] += item['amount']
            descriptions[desc]['occurrences'] += 1
        
        mello_roos_info['details'] = list(descriptions.values())
    
    return mello_roos_info

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
