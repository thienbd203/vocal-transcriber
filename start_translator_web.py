#!/usr/bin/env python3
"""
Script khởi động web interface cho JSON Translator
"""

import sys
import os
from pathlib import Path

# Thêm đường dẫn đến module
sys.path.insert(0, str(Path(__file__).parent / 'translate_json'))

from translate_json.web_server import app

if __name__ == '__main__':
    print("=" * 50)
    print("🌐 JSON TRANSLATOR WEB INTERFACE")
    print("=" * 50)
    print("\nĐang khởi động server...")
    print("📍 Truy cập: http://localhost:5001")
    print("⏹️  Dừng: Nhấn Ctrl+C")
    print("\n" + "=" * 50)
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n\n👋 Đã dừng server!")
