"""
Playwright-based scraper for Sacramento property tax data.
This scraper uses a real browser to bypass API restrictions.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json
from datetime import datetime
import time


class PropertyTaxScraper:
    """Scrapes property tax data using Playwright browser automation"""
    
    def __init__(self, headless=True, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        
    def scrape_property_data(self, street_number, street_name, city="Folsom"):
        """
        Scrape property tax data for a given address.
        
        Args:
            street_number: Street number (e.g., "932")
            street_name: Street name (e.g., "farmhouse way")
            city: City name (default: "Folsom")
            
        Returns:
            dict: Property tax data including bills and payment history
        """
        address = f"{street_number} {street_name} {city}".strip()
        
        print(f"[SCRAPER] Starting scrape for: {address}")
        
        captured_data = {
            'search_query': address,
            'timestamp': datetime.utcnow().isoformat(),
            'property_info': None,
            'tax_details': None,
            'error': None
        }
        
        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Track API responses
                api_responses = {
                    'algolia': None,
                    'govhub': None
                }
                
                # Intercept API calls
                def handle_response(response):
                    url = response.url
                    
                    # Capture Algolia search response
                    if 'algolia.net' in url and response.status == 200:
                        try:
                            data = response.json()
                            api_responses['algolia'] = data
                            print(f"[SCRAPER] Captured Algolia response")
                        except:
                            pass
                    
                    # Capture GovHub tax details response
                    if 'govhub.com' in url and response.status == 200:
                        try:
                            data = response.json()
                            api_responses['govhub'] = data
                            print(f"[SCRAPER] Captured GovHub response")
                        except:
                            pass
                
                page.on("response", handle_response)
                
                # Navigate to the property tax search page
                print(f"[SCRAPER] Loading property tax page...")
                page.goto("https://county-taxes.net/sacramento/property-tax", 
                         wait_until="networkidle", 
                         timeout=self.timeout)
                
                # Find the search input (try multiple selectors)
                print(f"[SCRAPER] Finding search input...")
                search_input = None
                selectors = [
                    'input[placeholder*="Parcel"]',
                    'input[placeholder*="Search"]',
                    'input[type="search"]',
                    '.search-input',
                    '#search-box'
                ]
                
                for selector in selectors:
                    try:
                        search_input = page.wait_for_selector(selector, timeout=5000)
                        if search_input:
                            print(f"[SCRAPER] Found input with selector: {selector}")
                            break
                    except:
                        continue
                
                if not search_input:
                    raise Exception("Could not find search input on page")
                
                # Type the address
                print(f"[SCRAPER] Typing address: {address}")
                search_input.fill(address)
                
                # Wait for autocomplete/search results
                print(f"[SCRAPER] Waiting for API responses...")
                time.sleep(3)  # Give time for Algolia to respond
                
                # Try to click first result if available
                try:
                    # Look for autocomplete dropdown or results
                    result_selectors = [
                        '.autocomplete-result:first-child',
                        '.search-result:first-child',
                        '[role="option"]:first-child',
                        '.aa-Item:first-child'
                    ]
                    
                    for selector in result_selectors:
                        try:
                            result = page.wait_for_selector(selector, timeout=3000)
                            if result:
                                print(f"[SCRAPER] Clicking first result...")
                                result.click()
                                time.sleep(2)  # Wait for details page to load
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"[SCRAPER] No clickable results, that's ok: {e}")
                
                # Wait a bit more for GovHub API to be called
                time.sleep(2)
                
                # Extract data from captured API responses
                if api_responses['algolia']:
                    algolia_data = api_responses['algolia']
                    if algolia_data.get('results') and algolia_data['results'][0].get('hits'):
                        first_hit = algolia_data['results'][0]['hits'][0]
                        captured_data['property_info'] = {
                            'objectID': first_hit.get('objectID'),
                            'account_number': first_hit.get('account_number'),
                            'address': first_hit.get('address'),
                            'city': first_hit.get('city'),
                            'zip': first_hit.get('zip'),
                            'parcel_number': first_hit.get('parcel_number'),
                        }
                        print(f"[SCRAPER] Found property: {first_hit.get('address')}")
                
                if api_responses['govhub']:
                    captured_data['tax_details'] = api_responses['govhub']
                    print(f"[SCRAPER] Captured tax details")
                
                # Close browser
                browser.close()
                
                # Validate we got data
                if not captured_data['property_info']:
                    captured_data['error'] = "No property found for the given address"
                    
                print(f"[SCRAPER] Scrape completed successfully")
                return captured_data
                
        except PlaywrightTimeout as e:
            print(f"[SCRAPER] Timeout error: {e}")
            captured_data['error'] = f"Timeout: {str(e)}"
            return captured_data
            
        except Exception as e:
            print(f"[SCRAPER] Error during scraping: {e}")
            captured_data['error'] = str(e)
            return captured_data
    
    def get_property_by_apn(self, apn):
        """
        Get property data by Assessor Parcel Number (APN)
        
        Args:
            apn: Assessor Parcel Number
            
        Returns:
            dict: Property tax data
        """
        # Similar to scrape_property_data but search by APN
        # Implementation would be similar but searching by parcel number
        pass


def test_scraper():
    """Test the scraper with a sample address"""
    scraper = PropertyTaxScraper(headless=False)  # Set to False to see browser
    result = scraper.scrape_property_data("932", "farmhouse way", "Folsom")
    
    print("\n" + "="*80)
    print("SCRAPER TEST RESULTS")
    print("="*80)
    print(json.dumps(result, indent=2))
    
    return result


if __name__ == "__main__":
    test_scraper()

