#!/usr/bin/env python3
"""
Test script for Vocal Transcriber API
"""

import json
import requests
import sys
from pathlib import Path

def test_api():
    """Test the API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Vocal Transcriber API...")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/api")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("\n💡 Make sure the server is running:")
        print("   python server.py")
        print("   hoặc")
        print("   python -m uvicorn vocal_transcriber.api.server:app --reload")
        return False
    
    # Test 2: File upload (requires actual MP3 file)
    print("\n2. Testing file upload...")
    test_file = Path("test.mp3")
    
    if not test_file.exists():
        print("⚠️  No test.mp3 file found")
        print("   To test file upload, place an MP3 file named 'test.mp3' in the root directory")
        return True
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{base_url}/transcribe", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ File upload and processing successful")
            print(f"   Language: {result.get('language')}")
            print(f"   Duration: {result.get('duration')}s")
            print(f"   Segments: {len(result.get('segments', []))}")
            
            # Save result
            with open("test_result.json", "w", encoding="utf-8") as out:
                json.dump(result, out, ensure_ascii=False, indent=2)
            print("   Result saved to: test_result.json")
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    return True

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
