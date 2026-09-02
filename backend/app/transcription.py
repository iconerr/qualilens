# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Audio/video transcription via OpenAI's speech-to-text API.

Video files have their audio track extracted with ffmpeg. Files over the
API's ~25MB limit are split into time-based chunks (also via ffmpeg) and
the transcripts concatenated. Whisper does not diarize; the transcript is
a single stream of speech, which the UI discloses to the user.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

MAX_UPLOAD_BYTES = 24 * 1024 * 1024
CHUNK_SECONDS = 600  # 10-minute chunks when splitting
TRANSCRIBE_MODEL = "whisper-1"
# containers the transcription API does not accept as-is; ffmpeg re-encodes
# them to mp3 first (the uploader accepts them so a phone recording is not
# refused at the door)
NEEDS_TRANSCODE = {".aac"}


class TranscriptionError(Exception):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def transcribe(path: Path, kind: str, openai_key: str,
               progress_cb=None) -> str:
    """Transcribe an audio or video file. Returns plain-text transcript."""
    if not openai_key:
        raise TranscriptionError(
            "Audio/video transcription requires an OpenAI API key (used for Whisper). "
            "Add one in Settings."
        )
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if kind == "video":
            if not ffmpeg_available():
                raise TranscriptionError("ffmpeg is required to extract audio from video files.")
            audio_path = tmp / "audio.mp3"
            _run_ffmpeg(["-i", str(path), "-vn", "-acodec", "libmp3lame",
                         "-b:a", "64k", str(audio_path)])
        elif path.suffix.lower() in NEEDS_TRANSCODE:
            if not ffmpeg_available():
                raise TranscriptionError(
                    f"The transcription service does not accept {path.suffix} files and "
                    "ffmpeg is not available to convert it. Install ffmpeg, or convert the "
                    "recording to .mp3 or .m4a and upload that.")
            audio_path = tmp / "audio.mp3"
            _run_ffmpeg(["-i", str(path), "-vn", "-acodec", "libmp3lame",
                         "-b:a", "64k", str(audio_path)])
        else:
            audio_path = path

        if audio_path.stat().st_size <= MAX_UPLOAD_BYTES:
            chunks = [audio_path]
        else:
            if not ffmpeg_available():
                raise TranscriptionError(
                    "This audio file exceeds the transcription API's size limit and "
                    "ffmpeg is not available to split it."
                )
            chunks = _split_audio(audio_path, tmp)

        texts = []
        for i, chunk in enumerate(chunks):
            if progress_cb:
                progress_cb(i, len(chunks))
            texts.append(_transcribe_one(chunk, openai_key))
        if progress_cb:
            progress_cb(len(chunks), len(chunks))
        # NOTE: chunks are split on a hard time boundary, so a word spanning
        # a seam may be garbled; seams occur every CHUNK_SECONDS on files
        # above the upload size limit.
        return "\n".join(t.strip() for t in texts if t.strip())


def _split_audio(audio_path: Path, tmp: Path) -> list:
    out_pattern = tmp / "chunk_%03d.mp3"
    _run_ffmpeg(["-i", str(audio_path), "-vn", "-acodec", "libmp3lame", "-b:a", "64k",
                 "-f", "segment", "-segment_time", str(CHUNK_SECONDS), str(out_pattern)])
    chunks = sorted(tmp.glob("chunk_*.mp3"))
    if not chunks:
        raise TranscriptionError("ffmpeg produced no audio chunks.")
    return chunks


def _run_ffmpeg(args: list) -> None:
    proc = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise TranscriptionError(f"ffmpeg failed: {proc.stderr[:400]}")


def _transcribe_one(path: Path, openai_key: str, retries: int = 3) -> str:
    """Transcribe one chunk, retrying transient failures so a single blip does
    not discard the transcripts of every chunk already completed."""
    import time
    last_err = ""
    for attempt in range(retries + 1):
        try:
            with open(path, "rb") as f:
                files = {"file": (path.name, f, "application/octet-stream")}
                data = {"model": TRANSCRIBE_MODEL, "response_format": "text"}
                with httpx.Client(timeout=httpx.Timeout(600.0, connect=15.0)) as client:
                    resp = client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        data=data, files=files,
                    )
            if resp.status_code == 200:
                return resp.text
            last_err = f"API error {resp.status_code}: {resp.text[:400]}"
            if resp.status_code not in (408, 429, 500, 502, 503, 504):
                break  # permanent error — retrying will not help
        except httpx.HTTPError as e:
            last_err = f"network error: {e}"
        if attempt < retries:
            time.sleep(min(2 ** attempt * 3, 30))
    raise TranscriptionError(f"Transcription failed for {path.name}: {last_err}")
