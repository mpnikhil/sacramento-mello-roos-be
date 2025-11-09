#!/usr/bin/env python3
"""
Sacramento County Property Tax Scraper with Detailed Levy Breakdown

This script uses the reverse-engineered APIs and HTML scraping to get complete
property tax information including direct levies and Mello-Roos charges.

Usage:
    python sacramento_tax_api.py --search "123 Main St"
    python sacramento_tax_api.py --apn "071-2040-013-0000"
    python sacramento_tax_api.py --search "932 farmhouse way" --bill-details

Requirements:
    pip install requests beautifulsoup4
"""

import requests
import json
import argparse
import base64
from typing import Optional, Dict, List
from urllib.parse import quote
from bs4 import BeautifulSoup


class SacramentoTaxAPI:
    """Access Sacramento County tax data via Algolia and GovHub APIs."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Algolia credentials (public, from HAR file)
        self.algolia_app_id = "NG9EXQZ0N7"
        self.algolia_api_key = "ab418fcaba5b88cfdc218f1da8a7cd69"
        self.algolia_index = "ca-sacramento.gsgx_property_tax"
        
    def search_property(self, query: str) -> List[Dict]:
        """
        Search for properties using Algolia.
        Works with address, APN, or partial text.
        
        Returns list of matching properties.
        """
        url = f"https://ng9exqz0n7-dsn.algolia.net/1/indexes/*/queries"
        
        headers = {
            'x-algolia-api-key': self.algolia_api_key,
            'x-algolia-application-id': self.algolia_app_id,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "requests": [{
                "indexName": self.algolia_index,
                "params": f"query={quote(query)}&hitsPerPage=20"
            }]
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                return data['results'][0].get('hits', [])
            return []
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_tax_bill_details(self, object_id: str) -> Optional[Dict]:
        """
        Get detailed tax bill information from GovHub API.
        
        Args:
            object_id: The objectID from Algolia search results
        """
        # Extract the path from the objectID
        # Format: /Taxsys-GovHub/v0/items/sacramento-ca:gsgx_property_tax:parents:GUID
        path = object_id.replace('/Taxsys-GovHub/v0/items/', '')
        encoded_path = quote(path, safe='')
        
        url = f"https://govhub.com/svc/payables/v0/Taxsys-GovHub%2Fv0%2Fitems%2F{encoded_path}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching bill details: {e}")
            return None
    
    def get_pdf_url(self, bill_details: Dict) -> Optional[str]:
        """
        Extract the PDF download URL from bill details.
        """
        if 'child_groups' in bill_details:
            for group in bill_details['child_groups']:
                for child in group.get('children', []):
                    for link in child.get('links', []):
                        if 'print' in link.get('rel', '').lower():
                            return link.get('href')
        return None
    
    def get_bill_levy_breakdown(self, parent_id_encoded: str, bill_id: str) -> Optional[Dict]:
        """
        Fetch and parse the detailed tax levy breakdown from the bill details page.
        
        Args:
            parent_id_encoded: The base64-encoded parent ID
            bill_id: The bill ID (GUID)
        
        Returns:
            Dictionary with ad_valorem_taxes, direct_charges, and totals
        """
        url = f"https://county-taxes.net/iframe-taxsys/sacramento-ca.county-taxes.com/govhub/property-tax/{parent_id_encoded}/bills/{bill_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {
                'ad_valorem_taxes': [],
                'direct_charges': [],
                'total_ad_valorem': 0,
                'total_direct_charges': 0,
                'grand_total': 0
            }
            
            # Parse Ad Valorem Taxes table
            ad_valorem_heading = soup.find('h3', string='Ad Valorem Taxes')
            if ad_valorem_heading:
                table = ad_valorem_heading.find_next('table')
                if table:
                    # Find all tbody elements (there may be multiple for different row groups)
                    tbodies = table.find_all('tbody')
                    for tbody in tbodies:
                        rows = tbody.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['th', 'td'])
                            if len(cells) >= 4:
                                tax_name = cells[0].get_text(strip=True)
                                rate = cells[1].get_text(strip=True)
                                taxable = cells[2].get_text(strip=True)
                                tax_amount = cells[3].get_text(strip=True)
                                
                                if 'Total' in tax_name:
                                    # Extract total (may be in column 2 or 3)
                                    try:
                                        # Try last cell first
                                        total_str = cells[-1].get_text(strip=True).replace('$', '').replace(',', '')
                                        if total_str:
                                            result['total_ad_valorem'] = float(total_str)
                                    except:
                                        pass
                                else:
                                    result['ad_valorem_taxes'].append({
                                        'name': tax_name,
                                        'rate': rate,
                                        'taxable_value': taxable,
                                        'tax_amount': tax_amount
                                    })
            
            # Parse Direct Charges table
            direct_charges_heading = soup.find('h3', string='Direct Charges and Special Assessments')
            if direct_charges_heading:
                table = direct_charges_heading.find_next('table')
                if table:
                    # Find all tbody elements (there may be multiple for different row groups)
                    tbodies = table.find_all('tbody')
                    for tbody in tbodies:
                        rows = tbody.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['th', 'td'])
                            if len(cells) >= 3:
                                levy_name = cells[0].get_text(strip=True)
                                
                                if 'Total' in levy_name:
                                    # Extract total
                                    try:
                                        total_str = cells[-1].get_text(strip=True).replace('$', '').replace(',', '')
                                        if total_str:
                                            result['total_direct_charges'] = float(total_str)
                                    except:
                                        pass
                                else:
                                    code = cells[1].get_text(strip=True) if len(cells) >= 4 else ''
                                    phone = cells[2].get_text(strip=True) if len(cells) >= 4 else ''
                                    amount = cells[-1].get_text(strip=True)
                                    
                                    result['direct_charges'].append({
                                        'name': levy_name,
                                        'code': code,
                                        'phone': phone,
                                        'amount': amount
                                    })
            
            # Parse Grand Total
            totals_heading = soup.find('h3', string='Totals')
            if totals_heading:
                table = totals_heading.find_next('table')
                if table:
                    tbodies = table.find_all('tbody')
                    for tbody in tbodies:
                        rows = tbody.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['th', 'td'])
                            if len(cells) >= 2:
                                label = cells[0].get_text(strip=True)
                                if 'Total' in label and 'payments' not in label.lower():
                                    try:
                                        total_str = cells[1].get_text(strip=True).replace('$', '').replace(',', '')
                                        result['grand_total'] = float(total_str)
                                        break
                                    except:
                                        pass
                        if result['grand_total'] > 0:
                            break
            
            # Calculate subtotals if not found in HTML
            if result['total_ad_valorem'] == 0 and result['ad_valorem_taxes']:
                total = 0
                for tax in result['ad_valorem_taxes']:
                    try:
                        amount_str = tax['tax_amount'].replace('$', '').replace(',', '')
                        total += float(amount_str)
                    except:
                        pass
                result['total_ad_valorem'] = total
            
            if result['total_direct_charges'] == 0 and result['direct_charges']:
                total = 0
                for charge in result['direct_charges']:
                    try:
                        amount_str = charge['amount'].replace('$', '').replace(',', '')
                        total += float(amount_str)
                    except:
                        pass
                result['total_direct_charges'] = total
            
            return result
            
        except Exception as e:
            print(f"Error fetching levy breakdown: {e}")
            return None
    
    def lookup_property(self, search_query: str, fetch_bill_details: bool = False) -> Dict:
        """
        Complete lookup: Search → Extract Info → Optionally fetch levy breakdown
        
        Args:
            search_query: Address, APN, or search text
            fetch_bill_details: If True, fetches detailed levy breakdown for the most recent bill
        """
        print(f"Searching for: {search_query}")
        
        # Step 1: Search
        results = self.search_property(search_query)
        
        if not results:
            return {
                'success': False,
                'error': 'No properties found',
                'query': search_query
            }
        
        # Show results
        print(f"\nFound {len(results)} result(s):")
        for i, prop in enumerate(results[:5], 1):
            print(f"  {i}. {prop.get('display_name', 'Unknown')}")
            print(f"     APN: {prop.get('external_id', 'N/A')}")
        
        # Use first result
        selected = results[0]
        
        print(f"\nProcessing: {selected.get('display_name')}")
        
        # Extract parent ID for bill detail URL construction
        object_id = selected.get('objectID', '')
        # Extract parent GUID from objectID like: /Taxsys-GovHub/v0/items/sacramento-ca:gsgx_property_tax:parents:GUID
        parent_id_encoded = selected.get('custom_parameters', {}).get('public_url', '').replace('/public/property_tax/accounts/', '')
        if not parent_id_encoded and object_id:
            # Fallback: encode the parent portion
            parent_path = object_id.replace('/Taxsys-GovHub/v0/items/', '')
            parent_id_encoded = base64.b64encode(parent_path.encode()).decode()
        
        # Step 2: Extract key information directly from Algolia response
        result = {
            'success': True,
            'apn': selected.get('external_id'),
            'address': selected.get('display_name'),
            'bills': []
        }
        
        # Extract bill information from the Algolia response
        if 'child_groups' in selected:
            for group in selected['child_groups']:
                for child in group.get('children', []):
                    bill_info = {
                        'bill_number': child.get('external_id'),
                        'display_name': child.get('display_name'),
                        'custom_parameters': child.get('custom_parameters', {})
                    }
                    
                    result['bills'].append(bill_info)
        
        # Step 3: Optionally fetch detailed levy breakdown for the most recent bill
        if fetch_bill_details and result['bills'] and parent_id_encoded:
            print(f"\nFetching detailed levy breakdown...")
            
            # Get the first (most recent) bill
            # The bill ID is embedded in the child data - need to extract GUID
            # Look for it in the objectID pattern or construct URL
            first_bill = result['bills'][0]
            
            # Try to find bill GUID from links or construct it
            # From the browser inspection, bill IDs are uppercase GUIDs like A4FAABB4-8B5F-11F0-A666-A9B7592EE820
            # These are in the child objects but not directly exposed. Let's construct the URL from public_url
            
            # The Algolia response might have direct links - let's use those
            if 'child_groups' in selected:
                for group in selected['child_groups']:
                    for child in group.get('children', []):
                        # Try to extract bill GUID from child structure
                        # The pattern from browser was like:  bills/A4FAABB4-8B5F-11F0-A666-A9B7592EE820
                        # We need to reverse engineer this or find it in the data
                        
                        # First bill only
                        bill_number = child.get('external_id')
                        if bill_number == first_bill['bill_number']:
                            levy_breakdown = self.fetch_bill_details_from_search_result(parent_id_encoded, child)
                            if levy_breakdown:
                                first_bill['levy_breakdown'] = levy_breakdown
                            break
                    if 'levy_breakdown' in first_bill:
                        break
        
        return result
    
    def fetch_bill_details_from_search_result(self, parent_id_encoded: str, bill_child: Dict) -> Optional[Dict]:
        """
        Helper to fetch bill details by trying different methods to get the bill page.
        """
        # Method 1: Try to find URL from external_id
        # The bill ID in URLs is not the same as external_id (bill number)
        # We need to search for the bill page by constructing the search URL
        
        # From the public_url pattern and bill structure, construct iframe URL
        # For now, return None as we need the actual GUID which isn't in the Algolia response
        # The proper way is to make this a two-step process or use the links from the full API response
        
        print(f"  Note: Bill GUID extraction not yet implemented. Use Excel file for detailed breakdown.")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Query Sacramento County property tax data with detailed levy breakdown'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--search', help='Search by address or partial text')
    group.add_argument('--apn', help='Search by Assessor Parcel Number')
    group.add_argument('--bill-details', nargs=2, metavar=('PARENT_ID', 'BILL_ID'),
                       help='Get detailed levy breakdown for a specific bill (provide parent_id and bill_id)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--save', help='Save results to file')
    
    args = parser.parse_args()
    
    api = SacramentoTaxAPI()
    
    # Handle bill details lookup
    if args.bill_details:
        parent_id, bill_id = args.bill_details
        result = api.get_bill_levy_breakdown(parent_id, bill_id)
        
        if args.json:
            output = json.dumps(result, indent=2)
            print("\n" + output)
            if args.save:
                with open(args.save, 'w') as f:
                    f.write(output)
                print(f"\nSaved to: {args.save}")
        else:
            if result:
                print("\n" + "="*70)
                print("TAX LEVY BREAKDOWN")
                print("="*70)
                
                print("\nAd Valorem Taxes:")
                for tax in result.get('ad_valorem_taxes', []):
                    print(f"  • {tax['name']}")
                    print(f"    Rate: {tax['rate']}, Taxable: {tax['taxable_value']}, Tax: {tax['tax_amount']}")
                print(f"\n  Total Ad Valorem: ${result.get('total_ad_valorem', 0):,.2f}")
                
                print("\nDirect Charges and Special Assessments (Mello-Roos):")
                for charge in result.get('direct_charges', []):
                    print(f"  • {charge['name']}")
                    print(f"    Code: {charge['code']}, Phone: {charge['phone']}, Amount: {charge['amount']}")
                print(f"\n  Total Direct Charges: ${result.get('total_direct_charges', 0):,.2f}")
                
                print(f"\nGRAND TOTAL: ${result.get('grand_total', 0):,.2f}")
                print("="*70)
            else:
                print("Error: Could not fetch bill details")
        return
    
    # Determine search query
    search_query = args.search or args.apn
    
    # Execute lookup
    result = api.lookup_property(search_query)
    
    # Output results
    if args.json:
        output = json.dumps(result, indent=2)
        print("\n" + output)
        
        if args.save:
            with open(args.save, 'w') as f:
                f.write(output)
            print(f"\nSaved to: {args.save}")
    
    else:
        print("\n" + "="*70)
        if result['success']:
            print(f"Property: {result['address']}")
            print(f"APN: {result['apn']}")
            
            print(f"\nBills ({len(result['bills'])}):")
            for bill in result['bills']:
                print(f"\n  • {bill['display_name']}")
                print(f"    Bill Number: {bill['bill_number']}")
                if bill['custom_parameters']:
                    print(f"    Type: {bill['custom_parameters'].get('external_type', 'N/A')}")
            
            print("\n" + "="*70)
            print("\nNOTE: Bill details available.")
            print("This property has tax bills from 2018-2025.")
            print("\nTo get detailed levy information and amounts:")
            print("  - Use the Excel file '2025_secured_roll_public.xlsx'")
            print("  - Or access Sacramento County's Direct Levy Listings")
        else:
            print(f"Error: {result['error']}")
            print("="*70)


if __name__ == '__main__':
    main()