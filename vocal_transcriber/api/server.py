#!/usr/bin/env python3
"""
FastAPI Server for MP3 to Lyrics Transcription.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..stt.service import TranscriptionConfig, transcribe_mp3
from ..utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Vocal Transcriber API",
    description="Upload MP3 file to extract vocals and transcribe to lyrics",
    version="1.0.0"
)

# Mount static files
static_dir = Path(__file__).parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Serve frontend"""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api")
async def api_root():
    """API health check"""
    return {"message": "Vocal Transcriber API is running"}


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload MP3 file and get transcription with lyrics
    
    Args:
        file: MP3 file to transcribe
        
    Returns:
        JSON with transcription segments and metadata
    """
    # Validate file type
    if not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only MP3 files are allowed")

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        input_path = temp_dir / file.filename
        output_dir = temp_dir / "output"

        try:
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            progress = ProgressTracker(enabled=False)
            config = TranscriptionConfig()

            lyrics_chat = transcribe_mp3(
                input_mp3=input_path,
                output_dir=output_dir,
                config=config,
                progress=progress,
            )

            lyrics_chat["processing_stats"] = {
                "total_time": round(progress.get_total_elapsed(), 2),
                "step_times": progress.step_times,
            }

            return lyrics_chat

        except Exception as e:
            logger.exception("Processing failed")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "Vocal Transcriber API",
        "version": "1.0.0"
    }


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Run the API server"""
    uvicorn.run(
        "vocal_transcriber.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
