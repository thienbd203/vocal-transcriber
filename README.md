# Vocal Transcriber

Dịch vụ chuyển đổi file MP3 thành lời hát sử dụng AI (Demucs + Whisper).

## Cấu trúc project

```
vocal-transcriber/
├── vocal_transcriber/          # Main package
│   ├── __init__.py
│   ├── __main__.py             # CLI entry point
│   ├── cli.py                  # CLI interface
│   ├── stt/                    # STT service module
│   │   ├── __init__.py
│   │   └── service.py          # Core STT functions
│   ├── api/                    # API module
│   │   ├── __init__.py
│   │   └── server.py           # FastAPI server
│   └── utils/                  # Utilities
│       ├── __init__.py
│       └── progress.py         # Progress tracking
├── static/                     # Frontend files
│   └── index.html
├── server.py                   # Server runner
├── requirements.txt
└── README.md
```

## Tính năng

- Tách vocal khỏi nhạc nền bằng Demucs
- Chuyển đổi giọng nói thành text bằng Whisper
- Trả về JSON với thời gian và lời hát từng đoạn
- Giao diện web dễ sử dụng

## Cài đặt

1. Cài đặt Python 3.8+
2. Cài đặt dependencies:

```bash
pip install -r requirements.txt
```

## Chạy ứng dụng

### 1. CLI Version:

```bash
python -m vocal_transcriber input.mp3 output_dir
```

Tuỳ chọn:

```bash
python -m vocal_transcriber input.mp3 output_dir \
  --language vi \
  --model-size medium \
  --device auto \
  --no-progress
```

### 2. Web API Version:

```bash
# Cách 1: Dùng server.py
python server.py

# Cách 2: Dùng uvicorn
python -m uvicorn vocal_transcriber.api.server:app --reload

# Cách 3: Dùng fastapi CLI (nếu đã cài)
fastapi dev vocal_transcriber.api.server
```

Server sẽ chạy tại http://localhost:8000

## Sử dụng API

### Upload và transcribe:

```bash
curl -X POST -F "file=@audio.mp3" http://localhost:8000/transcribe
```

### Response:

```json
{
  "language": "vi",
  "duration": 180.5,
  "segments": [
    {
      "start": 0.0,
      "end": 3.2,
      "text": "Lời hát đoạn 1"
    },
    {
      "start": 3.2,
      "end": 6.5,
      "text": "Lời hát đoạn 2"
    }
  ],
  "processing_stats": {
    "total_time": 45.2,
    "step_times": {
      "Tách vocal khỏi nhạc (Demucs)": 30.1,
      "Chuyển đổi giọng nói thành text (Whisper)": 14.3,
      "Định dạng lyrics chat JSON": 0.8
    }
  }
}
```

## Giao diện Web

Truy cập http://localhost:8000 để sử dụng giao diện web:

- Kéo thả hoặc chọn file MP3
- Xem progress xử lý
- Tải xuống kết quả JSON

## Lưu ý

- Cần GPU để xử lý nhanh hơn (tự động chọn `cuda`/`mps`/`cpu` nếu dùng `--device auto`)
- Model Whisper mặc định: `medium`
- Chỉ hỗ trợ file MP3
