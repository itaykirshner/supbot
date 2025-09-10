# debug_chromadb.py
# Run this script to debug ChromaDB connection issues

import chromadb
import requests
import json
import sys

def test_basic_http_connection(host, port):
    """Test basic HTTP connectivity to ChromaDB"""
    print(f"🔍 Testing basic HTTP connection to {host}:{port}")
    
    # Test different endpoints that ChromaDB typically exposes
    endpoints_to_test = [
        "/api/v1/heartbeat",
        "/api/v1/version", 
        "/api/v1/collections",
        "/heartbeat",
        "/version",
        "/"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            url = f"http://{host}:{port}{endpoint}"
            print(f"  Testing {endpoint}...")
            response = requests.get(url, timeout=10)
            print(f"    ✅ Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    content = response.json()
                    print(f"    📄 Response: {content}")
                except:
                    print(f"    📄 Response: {response.text[:100]}...")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
    print()

def test_chromadb_client_methods(host, port):
    """Test different ChromaDB client initialization methods"""
    print(f"🔍 Testing ChromaDB client initialization methods")
    
    # Method 1: Minimal client
    print("  Method 1: Minimal HttpClient")
    try:
        client = chromadb.HttpClient(host=host, port=port)
        print("    ✅ Client created successfully")
        
        # Try heartbeat
        try:
            heartbeat = client.heartbeat()
            print(f"    ✅ Heartbeat successful: {heartbeat}")
        except Exception as e:
            print(f"    ❌ Heartbeat failed: {e}")
        
        # Try list collections
        try:
            collections = client.list_collections()
            print(f"    ✅ List collections successful: {len(collections)} collections")
            for col in collections:
                print(f"      - {col.name}")
        except Exception as e:
            print(f"    ❌ List collections failed: {e}")
            
    except Exception as e:
        print(f"    ❌ Client creation failed: {e}")
    print()
    
    # Method 2: Client with settings
    print("  Method 2: HttpClient with settings")
    try:
        client = chromadb.HttpClient(
            host=host, 
            port=port,
            settings=chromadb.config.Settings(
                anonymized_telemetry=False
            )
        )
        print("    ✅ Client with settings created successfully")
        
        try:
            collections = client.list_collections()
            print(f"    ✅ List collections successful: {len(collections)} collections")
        except Exception as e:
            print(f"    ❌ List collections failed: {e}")
            
    except Exception as e:
        print(f"    ❌ Client with settings failed: {e}")
    print()

def test_collection_operations(host, port):
    """Test collection operations"""
    print("🔍 Testing collection operations")
    
    try:
        client = chromadb.HttpClient(host=host, port=port)
        
        # Try to get or create a test collection
        collection_name = "test_connection"
        print(f"  Testing collection: {collection_name}")
        
        try:
            collection = client.get_or_create_collection(name=collection_name)
            print(f"    ✅ Collection '{collection_name}' accessed successfully")
            
            # Test count
            count = collection.count()
            print(f"    📊 Collection count: {count}")
            
            # Clean up test collection
            try:
                client.delete_collection(name=collection_name)
                print(f"    🧹 Test collection deleted successfully")
            except Exception as e:
                print(f"    ⚠️  Could not delete test collection: {e}")
                
        except Exception as e:
            print(f"    ❌ Collection operations failed: {e}")
            
    except Exception as e:
        print(f"    ❌ Could not create client for collection test: {e}")
    print()

def main():
    # Configuration
    host = "chromadb-service.bot-infra.svc.cluster.local"
    port = 8000
    
    print("🚀 ChromaDB Connection Diagnostics")
    print("=" * 50)
    print(f"Target: {host}:{port}")
    print()
    
    # Test 1: Basic HTTP connectivity
    test_basic_http_connection(host, port)
    
    # Test 2: ChromaDB client methods
    test_chromadb_client_methods(host, port)
    
    # Test 3: Collection operations
    test_collection_operations(host, port)
    
    print("🏁 Diagnostics complete!")
    print()
    print("💡 Tips based on results:")
    print("- If basic HTTP fails: Check if ChromaDB pod is running and service exists")
    print("- If heartbeat fails but collections work: Use list_collections for health checks")
    print("- If all tests fail: Check network policies and DNS resolution")

if __name__ == "__main__":
    main()
