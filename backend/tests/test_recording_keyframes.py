# -*- coding: utf-8 -*-
"""Mode-A recordings upload VIDEO, but the visual analysis reads frames/ — keyframes are now pulled out of the
video with ffmpeg (2026-11-15, owner plan item 12)."""
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def _webm(path: Path, seconds: int = 4) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=10:duration={seconds}",
                    "-c:v", "libvpx", "-b:v", "200k", str(path)], check=True, timeout=120)


def test_keyframes_are_extracted_from_video_chunks(tmp_path):
    from app.services.inspector_recording_processor import extract_keyframes_from_video

    s = SimpleNamespace(frames_dir=tmp_path / "frames", video_dir=tmp_path / "video_chunks")
    s.video_dir.mkdir()
    _webm(s.video_dir / "chunk_000000.webm")
    n = extract_keyframes_from_video(s, count=4)
    assert n >= 2
    assert not (s.video_dir / "_joined.webm").exists()
    # frames already present ⇒ untouched
    assert extract_keyframes_from_video(s, count=4) == 0


def test_no_video_no_frames(tmp_path):
    from app.services.inspector_recording_processor import extract_keyframes_from_video

    s = SimpleNamespace(frames_dir=tmp_path / "f", video_dir=tmp_path / "v")
    assert extract_keyframes_from_video(s) == 0


def test_webm_becomes_playable_mp4_parts(tmp_path):
    from app.services.inspector_recording_finalize import webm_to_mp4_parts

    src = tmp_path / "v.webm"
    _webm(src, seconds=6)
    parts = webm_to_mp4_parts(src.read_bytes(), max_mb=50, stem="rec")
    assert len(parts) == 1 and parts[0][1] == "rec.mp4" and parts[0][0][4:8] == b"ftyp"
    # a tiny limit ⇒ several TIME segments, each a valid mp4 of its own
    many = webm_to_mp4_parts(src.read_bytes(), max_mb=0, stem="rec")  # 0 MB ⇒ forces splitting
    assert all(p[0][4:8] == b"ftyp" for p in many)


def test_audio_to_m4a(tmp_path):
    from app.services.inspector_recording_finalize import webm_audio_to_m4a

    a = tmp_path / "a.webm"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-c:a", "libopus", str(a)], check=True, timeout=60)
    out = webm_audio_to_m4a(a.read_bytes())
    assert out and out[4:8] == b"ftyp"
