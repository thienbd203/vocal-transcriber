# Vocal Transcriber

Dịch vụ chuyển đổi file MP3 thành lời hát sử dụng AI (Demucs + Whisper).

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

### Chạy API server:

```bash
python api_server.py
```

Server sẽ chạy tại http://localhost:8000

### Hoặc chạy CLI:

```bash
python main.py input.mp3 output_dir
```

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

- Cần GPU để xử lý nhanh hơn
- Model Whisper mặc định: medium (có thể thay đổi trong code)
- Chỉ hỗ trợ file MP3
