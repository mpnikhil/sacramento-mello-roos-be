"""
Orchestrator module that coordinates scraping and caching.
This is the main entry point for getting property tax data.
"""

from scraper import PropertyTaxScraper
from database import PropertyTaxDB
from datetime import datetime
import os


class PropertyTaxOrchestrator:
    """
    Orchestrates the flow of property tax data retrieval:
    1. Check cache first
    2. If cache miss or stale, scrape with Playwright
    3. Save to cache
    4. Return data
    """
    
    def __init__(self, cache_max_age_days=30, headless=True):
        """
        Initialize orchestrator.
        
        Args:
            cache_max_age_days: Maximum age of cache before re-scraping (default: 30)
            headless: Run browser in headless mode (default: True)
        """
        self.db = PropertyTaxDB()
        self.scraper = PropertyTaxScraper(headless=headless)
        self.cache_max_age_days = cache_max_age_days
    
    def get_property_tax_data(self, street_number, street_name, city, force_refresh=False):
        """
        Get property tax data with intelligent caching.
        
        Args:
            street_number: Street number (e.g., "932")
            street_name: Street name (e.g., "farmhouse way")
            city: City name (e.g., "Folsom")
            force_refresh: Force a fresh scrape even if cache exists (default: False)
            
        Returns:
            dict: Property tax data with metadata about cache status
        """
        print(f"\n[ORCHESTRATOR] Request for: {street_number} {street_name}, {city}")
        
        # Step 1: Check cache (unless force refresh requested)
        if not force_refresh:
            cached_data = self.db.get_cached_property(
                street_number, 
                street_name, 
                city, 
                max_age_days=self.cache_max_age_days
            )
            
            if cached_data:
                print(f"[ORCHESTRATOR] Returning cached data")
                return {
                    'success': True,
                    'source': 'cache',
                    'cache_age_days': cached_data['cache_age_days'],
                    'cached_at': cached_data['cached_at'],
                    'property_info': cached_data['property_info'],
                    'tax_details': cached_data['tax_details']
                }
        
        # Step 2: Scrape fresh data
        print(f"[ORCHESTRATOR] Cache miss or force refresh - initiating scrape")
        scraped_data = self.scraper.scrape_property_data(
            street_number, 
            street_name, 
            city
        )
        
        # Step 3: Check for errors
        if scraped_data.get('error'):
            print(f"[ORCHESTRATOR] Scraping failed: {scraped_data['error']}")
            return {
                'success': False,
                'source': 'scraper',
                'error': scraped_data['error'],
                'timestamp': scraped_data['timestamp']
            }
        
        if not scraped_data.get('property_info'):
            print(f"[ORCHESTRATOR] No property found")
            return {
                'success': False,
                'source': 'scraper',
                'error': 'No property found for the given address',
                'search_query': scraped_data['search_query']
            }
        
        # Step 4: Save to cache
        print(f"[ORCHESTRATOR] Saving to cache")
        self.db.save_scraped_data(
            street_number,
            street_name,
            city,
            scraped_data
        )
        
        # Step 5: Return formatted response
        print(f"[ORCHESTRATOR] Returning fresh data")
        return {
            'success': True,
            'source': 'scraper',
            'scraped_at': scraped_data['timestamp'],
            'property_info': scraped_data['property_info'],
            'tax_details': scraped_data['tax_details']
        }
    
    def get_cache_stats(self):
        """Get cache statistics"""
        return self.db.get_cache_stats()
    
    def clear_old_cache(self, days_old=90):
        """Clear old cache entries"""
        return self.db.clear_old_cache(days_old)


def test_orchestrator():
    """Test the orchestrator"""
    import json
    
    orchestrator = PropertyTaxOrchestrator(headless=False)
    
    # First call - should scrape
    print("\n" + "="*80)
    print("TEST 1: First call (should scrape)")
    print("="*80)
    result1 = orchestrator.get_property_tax_data("932", "farmhouse way", "Folsom")
    print(json.dumps(result1, indent=2))
    
    # Second call - should use cache
    print("\n" + "="*80)
    print("TEST 2: Second call (should use cache)")
    print("="*80)
    result2 = orchestrator.get_property_tax_data("932", "farmhouse way", "Folsom")
    print(json.dumps(result2, indent=2))
    
    # Third call - force refresh
    print("\n" + "="*80)
    print("TEST 3: Force refresh (should scrape)")
    print("="*80)
    result3 = orchestrator.get_property_tax_data("932", "farmhouse way", "Folsom", force_refresh=True)
    print(json.dumps(result3, indent=2))
    
    # Get stats
    print("\n" + "="*80)
    print("CACHE STATS")
    print("="*80)
    stats = orchestrator.get_cache_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    test_orchestrator()

