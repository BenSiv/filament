#!/usr/bin/env python3
"""
Test BC Data Source Scrapers

This script tests connectivity to real BC data sources and demonstrates
the data extraction pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from datetime import datetime


def test_bccs_gis():
    """Test BC Coroners Service ArcGIS REST API."""
    print("\n" + "=" * 60)
    print("Testing BC Coroners Service GIS API")
    print("=" * 60)
    
    # BC Government ArcGIS REST endpoint (example - needs actual endpoint)
    # This tests if the ArcGIS server is reachable
    base_url = "https://governmentofbc.maps.arcgis.com/arcgis/rest/services"
    
    try:
        response = requests.get(
            base_url,
            params={"f": "json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ArcGIS Server reachable")
            print(f"   Current Version: {data.get('currentVersion', 'Unknown')}")
            
            # List available folders
            folders = data.get('folders', [])
            if folders:
                print(f"   Available folders: {len(folders)}")
                for folder in folders[:5]:  # Show first 5
                    print(f"     - {folder}")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_ncmpur():
    """Test Canada's Missing website connectivity."""
    print("\n" + "=" * 60)
    print("Testing Canada's Missing (NCMPUR)")
    print("=" * 60)
    
    url = "https://www.canadasmissing.ca/index-eng.htm"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ NCMPUR website reachable")
            print(f"   Content length: {len(response.content)} bytes")
            
            # Check for key elements
            if "missing" in response.text.lower():
                print("   ✅ Contains expected content")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_canlii():
    """Test CanLII legal database connectivity."""
    print("\n" + "=" * 60)
    print("Testing CanLII Legal Database")
    print("=" * 60)
    
    # Search for BC court cases
    url = "https://www.canlii.org/en/bc/"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ CanLII BC portal reachable")
            print(f"   Content length: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_bc_data_catalogue():
    """Test BC Data Catalogue API."""
    print("\n" + "=" * 60)
    print("Testing BC Data Catalogue API")
    print("=" * 60)
    
    url = "https://catalogue.data.gov.bc.ca/api/3/action/package_search"
    
    try:
        # Search for coroner-related datasets
        response = requests.get(
            url,
            params={"q": "coroner", "rows": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results = data.get("result", {})
                count = results.get("count", 0)
                print(f"✅ BC Data Catalogue reachable")
                print(f"   Found {count} datasets matching 'coroner'")
                
                for pkg in results.get("results", [])[:3]:
                    print(f"   - {pkg.get('title', 'Unknown')}")
                return True
        
        print(f"❌ Unexpected response")
        return False
            
    except requests.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_ollama():
    """Test Ollama LLM server."""
    print("\n" + "=" * 60)
    print("Testing Ollama LLM Server")
    print("=" * 60)
    
    import os
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ Ollama server reachable at {ollama_host}")
            print(f"   Available models: {len(models)}")
            for model in models:
                print(f"     - {model.get('name', 'Unknown')}")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"⚠️  Ollama not available: {e}")
        print("   (This is expected if running outside container)")
        return False


def test_postgres():
    """Test PostgreSQL connection."""
    print("\n" + "=" * 60)
    print("Testing PostgreSQL + pgvector")
    print("=" * 60)
    
    import os
    
    try:
        import psycopg2
    except ImportError:
        print("⚠️  psycopg2 not installed, skipping database test")
        return False
    
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "filament"),
            user=os.getenv("POSTGRES_USER", "filament"),
            password=os.getenv("POSTGRES_PASSWORD", "filament_dev")
        )
        
        with conn.cursor() as cur:
            # Test basic connection
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"✅ PostgreSQL connected")
            print(f"   {version[:50]}")
            
            # Test pgvector
            cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            if cur.fetchone():
                print("   ✅ pgvector extension installed")
            else:
                print("   ❌ pgvector extension NOT installed")
            
            # Test tables
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]
            print(f"   Tables: {', '.join(tables) if tables else 'None'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        print("   (This is expected if running outside container)")
        return False


def main():
    """Run all data source tests."""
    print("=" * 60)
    print("FILAMENT - Data Source Connectivity Tests")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {
        "BC Coroners GIS": test_bccs_gis(),
        "NCMPUR": test_ncmpur(),
        "CanLII": test_canlii(),
        "BC Data Catalogue": test_bc_data_catalogue(),
        "Ollama": test_ollama(),
        "PostgreSQL": test_postgres(),
    }
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for source, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {source}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")
    
    return 0 if passed >= 4 else 1  # At least external sources should work


if __name__ == "__main__":
    sys.exit(main())
