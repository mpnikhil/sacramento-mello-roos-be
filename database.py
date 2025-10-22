"""
Database module for caching scraped property tax data.
Uses SQLite for simplicity and portability.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import os


class PropertyTaxDB:
    """Manages property tax data caching in SQLite"""
    
    def __init__(self, db_path=None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Use /tmp for serverless environments (Vercel, Railway, etc.)
            # or local directory for development
            if os.getenv('VERCEL'):
                db_path = '/tmp/property_tax_cache.db'
            else:
                db_path = 'property_tax_cache.db'
        
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Property cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS property_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_key TEXT UNIQUE NOT NULL,
                account_number TEXT,
                parcel_number TEXT,
                address TEXT,
                city TEXT,
                zip TEXT,
                object_id TEXT,
                property_data TEXT NOT NULL,
                tax_details TEXT,
                last_scraped_at TIMESTAMP NOT NULL,
                last_tax_bill_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_search_key 
            ON property_cache(search_key)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_account_number 
            ON property_cache(account_number)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_parcel_number 
            ON property_cache(parcel_number)
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"[DB] Database initialized at: {self.db_path}")
    
    def _generate_search_key(self, street_number, street_name, city):
        """Generate a normalized search key for caching"""
        parts = [str(street_number), str(street_name), str(city)]
        return " ".join(parts).lower().strip()
    
    def get_cached_property(self, street_number, street_name, city, max_age_days=30):
        """
        Get cached property data if it exists and is recent enough.
        
        Args:
            street_number: Street number
            street_name: Street name
            city: City name
            max_age_days: Maximum age of cache in days (default: 30)
            
        Returns:
            dict or None: Cached data if found and fresh, None otherwise
        """
        search_key = self._generate_search_key(street_number, street_name, city)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM property_cache 
            WHERE search_key = ?
            ORDER BY last_scraped_at DESC
            LIMIT 1
        ''', (search_key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print(f"[DB] No cache found for: {search_key}")
            return None
        
        # Check if cache is fresh enough
        last_scraped = datetime.fromisoformat(row['last_scraped_at'])
        age = datetime.utcnow() - last_scraped
        
        if age.days > max_age_days:
            print(f"[DB] Cache expired (age: {age.days} days): {search_key}")
            return None
        
        print(f"[DB] Cache hit (age: {age.days} days): {search_key}")
        
        # Reconstruct the data structure
        return {
            'property_info': json.loads(row['property_data']),
            'tax_details': json.loads(row['tax_details']) if row['tax_details'] else None,
            'cached_at': row['last_scraped_at'],
            'cache_age_days': age.days,
            'from_cache': True
        }
    
    def save_scraped_data(self, street_number, street_name, city, scraped_data):
        """
        Save or update scraped property data in cache.
        
        Args:
            street_number: Street number
            street_name: Street name
            city: City name
            scraped_data: Dictionary containing scraped property data
            
        Returns:
            bool: True if saved successfully
        """
        search_key = self._generate_search_key(street_number, street_name, city)
        
        property_info = scraped_data.get('property_info', {})
        tax_details = scraped_data.get('tax_details')
        
        # Extract latest tax bill year if available
        last_tax_bill_year = None
        if tax_details and tax_details.get('bills'):
            bills = tax_details['bills']
            if bills:
                last_tax_bill_year = bills[0].get('year')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO property_cache (
                    search_key, account_number, parcel_number, address, city, zip,
                    object_id, property_data, tax_details, last_scraped_at, last_tax_bill_year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(search_key) DO UPDATE SET
                    account_number = excluded.account_number,
                    parcel_number = excluded.parcel_number,
                    address = excluded.address,
                    city = excluded.city,
                    zip = excluded.zip,
                    object_id = excluded.object_id,
                    property_data = excluded.property_data,
                    tax_details = excluded.tax_details,
                    last_scraped_at = excluded.last_scraped_at,
                    last_tax_bill_year = excluded.last_tax_bill_year,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                search_key,
                property_info.get('account_number'),
                property_info.get('parcel_number'),
                property_info.get('address'),
                property_info.get('city'),
                property_info.get('zip'),
                property_info.get('objectID'),
                json.dumps(property_info),
                json.dumps(tax_details) if tax_details else None,
                datetime.utcnow().isoformat(),
                last_tax_bill_year
            ))
            
            conn.commit()
            print(f"[DB] Saved/updated cache for: {search_key}")
            return True
            
        except Exception as e:
            print(f"[DB] Error saving data: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def get_cache_stats(self):
        """Get statistics about the cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM property_cache')
        total = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) as fresh 
            FROM property_cache 
            WHERE datetime(last_scraped_at) > datetime('now', '-30 days')
        ''')
        fresh = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_cached_properties': total,
            'fresh_cache_count': fresh,
            'stale_cache_count': total - fresh
        }
    
    def clear_old_cache(self, days_old=90):
        """
        Clear cache entries older than specified days.
        
        Args:
            days_old: Delete entries older than this many days
            
        Returns:
            int: Number of entries deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        
        cursor.execute('''
            DELETE FROM property_cache 
            WHERE last_scraped_at < ?
        ''', (cutoff_date,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"[DB] Deleted {deleted} cache entries older than {days_old} days")
        return deleted


def test_database():
    """Test database operations"""
    db = PropertyTaxDB('test_cache.db')
    
    # Test data
    test_data = {
        'property_info': {
            'objectID': 'test-123',
            'account_number': '123-456-789',
            'address': '932 Farmhouse Way',
            'city': 'Folsom',
            'zip': '95630',
            'parcel_number': '123-456-789'
        },
        'tax_details': {
            'bills': [
                {'year': 2024, 'amount': 5000}
            ]
        }
    }
    
    # Save
    db.save_scraped_data('932', 'farmhouse way', 'folsom', test_data)
    
    # Retrieve
    cached = db.get_cached_property('932', 'farmhouse way', 'folsom')
    print("\nCached data:")
    print(json.dumps(cached, indent=2))
    
    # Stats
    stats = db.get_cache_stats()
    print("\nCache stats:")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    test_database()

