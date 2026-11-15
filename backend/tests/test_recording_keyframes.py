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
