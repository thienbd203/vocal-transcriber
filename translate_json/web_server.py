#!/usr/bin/env python3
"""
Flask web server for JSON translation interface
"""

from flask import Flask, request, jsonify, render_template, Response
import json
import sys
import os
from pathlib import Path

# Add parent directory to path to import translate_json module
sys.path.insert(0, str(Path(__file__).parent.parent))
from translate_json import JSONTranslator
from translate_json.config import DEFAULT_BACKEND

app = Flask(__name__)

@app.route('/')
def index():
    """Serve the main HTML interface"""
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    """Handle translation requests"""
    try:
        data = request.get_json()
        
        if not data or 'json_data' not in data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Parse JSON data with validation
        try:
            json_data = json.loads(data['json_data'])
            # Validate JSON structure
            if json_data is None:
                raise ValueError("Empty JSON data")
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Get language settings
        from_lang = data.get('from_lang', 'en')
        to_lang = data.get('to_lang', 'vi')
        
        # Create translator with multiple workers
        translator = JSONTranslator(source_lang=from_lang, target_lang=to_lang, backend=os.environ.get('TRANSLATOR_BACKEND', DEFAULT_BACKEND))
        
        def generate():
            """Generate streaming response with progress updates"""
            try:
                # Send initial status
                yield f"data: {json.dumps({'status': 'Đang chuẩn bị...', 'progress': 0})}\n\n"
                
                # Log JSON structure and size
                json_str = json.dumps(json_data)
                json_size = len(json_str.encode('utf-8'))
                yield f"data: {json.dumps({'log': f'JSON type: {type(json_data).__name__}, size: {json_size/1024:.1f}KB', 'progress': 2})}\n\n"
                
                # Check if JSON is too large
                if json_size > 50 * 1024 * 1024:  # 50MB limit
                    yield f"data: {json.dumps({'error': 'File quá lớn (>50MB). Vui lòng sử dụng file nhỏ hơn.'})}\n\n"
                    return
                
                # Ensure packages are installed
                yield f"data: {json.dumps({'log': 'Checking translation packages...', 'progress': 5})}\n\n"
                translator._ensure_packages()
                
                # Process JSON
                yield f"data: {json.dumps({'log': 'Processing JSON data...', 'progress': 10})}\n\n"
                
                # Check if it's the expected format
                if isinstance(json_data, list):
                    # Handle the specific format: [null, {id: 1, list: [...]}, {id: 2, list: [...]}]
                    items_to_process = []
                    
                    for item in json_data:
                        if item is None:
                            continue
                        if isinstance(item, dict) and 'list' in item and isinstance(item['list'], list):
                            # Add all items from the list
                            items_to_process.extend(item['list'])
                        elif isinstance(item, dict):
                            # Add the item itself if it has parameters
                            items_to_process.append(item)
                    
                    # Process items in batches with parallel processing
                    total_items = len(items_to_process)
                    processed_items = 0
                    translated_count = 0
                    batch_size = 50  # Process 50 items at a time
                    
                    yield f"data: {json.dumps({'log': f'Processing {total_items} items in batches of {batch_size}', 'progress': 15})}\n\n"
                    
                    for batch_start in range(0, total_items, batch_size):
                        batch_end = min(batch_start + batch_size, total_items)
                        batch = items_to_process[batch_start:batch_end]

                        # Process batch
                        for item in batch:
                            if isinstance(item, dict) and 'parameters' in item and isinstance(item['parameters'], list):
                                original_params = item['parameters']
                                item['parameters'] = translator.process_parameters(item['parameters'])
                                # Count translated items
                                for p in original_params:
                                    if isinstance(p, str) and should_translate(p):
                                        translated_count += 1
                             
                            processed_items += 1
                    
                        # Update progress
                        progress = 15 + (70 * processed_items / total_items)
                        if processed_items % 100 == 0 or processed_items == total_items:
                            samples = translator.pop_translation_samples()
                            payload = {'log': f'Processed {processed_items}/{total_items} items', 'progress': progress}
                            if samples:
                                payload['samples'] = samples
                            yield f"data: {json.dumps(payload)}\n\n"
                    
                    # Return the original structure with translations
                    final_result = json_data
                else:
                    # Handle other formats (single object, etc.)
                    yield f"data: {json.dumps({'error': 'Unsupported JSON format. Expected array format.'})}\n\n"
                    return
                
                # Final result
                yield f"data: {json.dumps({'log': f'Translated {translated_count} strings', 'progress': 95})}\n\n"
                yield f"data: {json.dumps({'log': 'Finalizing...', 'progress': 100})}\n\n"
                yield f"data: {json.dumps({'result': final_result, 'progress': 100, 'status': 'Hoàn tất!'})}\n\n"
                    
            except Exception as e:
                import traceback
                error_details = f"{str(e)}\n{traceback.format_exc()}"
                yield f"data: {json.dumps({'error': f'Lỗi xử lý: {str(e)}', 'details': error_details})}\n\n"
        
        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Monkey patch to access original should_translate function
import translate_json.filters
from translate_json.filters import should_translate

if __name__ == '__main__':
    print("▶ Starting JSON Translator Web Server...")
    print("  - Open http://localhost:5001 in your browser")
    print("  - Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=5001)
