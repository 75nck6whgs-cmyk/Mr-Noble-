#!/usr/bin/env python3
import argparse
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from gtts import gTTS
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

DEFAULT_SCRIPT = (
    "This is The Coco Tree coconut water. It's refreshing, fat free, and high in "
    "potassium. Perfect after a workout, on a busy day, or whenever you need a clean "
    "tropical boost."
)

CAPTIONS = [
    ("Refreshing", 0.8, 2.2),
    ("Fat free", 2.3, 3.7),
    ("High in potassium", 3.8, 5.8),
    ("The Coco Tree", 6.0, 8.8),
]


def log(msg: str) -> None:
    print(f"[coco-tree] {msg}")


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def generate_tts(script: str, out_path: Path) -> Path:
    log("Generating voiceover with gTTS...")
    tts = gTTS(text=script, lang="en")
    tts.save(str(out_path))
    log(f"Voiceover saved: {out_path}")
    return out_path


def did_upload_image(api_key: str, image_path: Path) -> str:
    url = "https://api.d-id.com/images"
    headers = {"Authorization": f"Basic {api_key}"}
    with image_path.open("rb") as f:
        files = {"image": (image_path.name, f, "image/png")}
        r = requests.post(url, headers=headers, files=files, timeout=90)
    r.raise_for_status()
    data = r.json()
    image_url = data.get("url")
    if not image_url:
        raise RuntimeError(f"D-ID image upload did not return url: {data}")
    return image_url


def did_create_talk(api_key: str, image_url: str, script: str, audio_path: Optional[Path]) -> str:
    url = "https://api.d-id.com/talks"
    headers = {"Authorization": f"Basic {api_key}", "Content-Type": "application/json"}

    if audio_path and audio_path.exists():
        # For file-based audio, host locally isn't possible for D-ID; use text-driven fallback.
        log("Custom audio detected; using text-to-speech mode in D-ID unless hosted URL is provided.")

    payload = {
        "source_url": image_url,
        "script": {
            "type": "text",
            "input": script,
            "provider": {"type": "microsoft", "voice_id": "en-US-JennyNeural"},
        },
        "config": {
            "stitch": True,
            "result_format": "mp4",
            "fluent": True,
            "pad_audio": 0,
            "driver_expressions": {
                "expressions": [
                    {"expression": "happy", "start_frame": 0, "intensity": 0.5}
                ]
            },
        },
    }

    r = requests.post(url, headers=headers, json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    talk_id = data.get("id")
    if not talk_id:
        raise RuntimeError(f"D-ID talk creation failed: {data}")
    return talk_id


def did_wait_and_download(api_key: str, talk_id: str, out_path: Path, timeout_s: int = 300) -> Path:
    headers = {"Authorization": f"Basic {api_key}"}
    status_url = f"https://api.d-id.com/talks/{talk_id}"
    start = time.time()
    while True:
        r = requests.get(status_url, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        log(f"D-ID status: {status}")
        if status == "done":
            result_url = data.get("result_url")
            if not result_url:
                raise RuntimeError("D-ID finished but no result_url present")
            rv = requests.get(result_url, timeout=180)
            rv.raise_for_status()
            out_path.write_bytes(rv.content)
            log(f"Downloaded avatar video: {out_path}")
            return out_path
        if status in {"error", "rejected"}:
            raise RuntimeError(f"D-ID processing failed: {data}")
        if time.time() - start > timeout_s:
            raise TimeoutError("Timed out waiting for D-ID result")
        time.sleep(5)


def add_burned_captions(in_video: Path, out_video: Path, aspect_ratio: str) -> Path:
    log("Burning promo captions into video...")
    clip = VideoFileClip(str(in_video))

    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1080, 1350)
    base = clip.resize(height=target_h)
    if base.w < target_w:
        base = base.resize(width=target_w)
    base = base.crop(x_center=base.w / 2, y_center=base.h / 2, width=target_w, height=target_h)

    text_clips = []
    for txt, start_t, end_t in CAPTIONS:
        tc = (
            TextClip(txt, fontsize=68, color="white", font="Arial-Bold", stroke_color="black", stroke_width=2)
            .set_start(start_t)
            .set_end(min(end_t, base.duration))
            .set_position(("center", int(target_h * 0.82)))
        )
        text_clips.append(tc)

    final = CompositeVideoClip([base] + text_clips)
    final.write_videofile(str(out_video), codec="libx264", audio_codec="aac", fps=24, threads=4)

    clip.close()
    base.close()
    final.close()
    return out_video


def run_sadtalker_fallback(image_path: Path, audio_path: Path, out_path: Path) -> bool:
    """Attempt local SadTalker CLI if installed. Returns True on success."""
    cmd = [
        "python",
        "SadTalker/inference.py",
        "--driven_audio", str(audio_path),
        "--source_image", str(image_path),
        "--result_dir", str(out_path.parent),
        "--still",
        "--preprocess", "full",
    ]
    log("Trying SadTalker fallback (local install required)...")
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        log(f"SadTalker fallback unavailable or failed: {e}")
        return False


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate realistic talking UGC promo from one avatar image")
    parser.add_argument("--image", required=True, help="Path to avatar image")
    parser.add_argument("--script", default=DEFAULT_SCRIPT, help="Promo script")
    parser.add_argument("--audio", default=os.getenv("VOICEOVER_PATH", ""), help="Optional voiceover audio path")
    parser.add_argument("--output", default=os.getenv("OUTPUT_PATH", "output/coco_tree_talking_ugc.mp4"))
    parser.add_argument("--aspect-ratio", default=os.getenv("ASPECT_RATIO", "9:16"), choices=["9:16", "4:5"])
    args = parser.parse_args()

    image_path = Path(args.image).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    tmp_raw = output_path.with_name(output_path.stem + "_raw.mp4")
    ensure_output_dir(output_path)

    if not image_path.exists():
        log(f"ERROR: image not found: {image_path}")
        return 1

    audio_path = Path(args.audio).expanduser().resolve() if args.audio else output_path.with_name("voiceover.mp3")
    if not args.audio:
        try:
            generate_tts(args.script, audio_path)
        except Exception as e:
            log(f"ERROR generating TTS: {e}")
            return 1

    did_key = os.getenv("DID_API_KEY", "").strip()
    if not did_key:
        log("No DID_API_KEY found. Setup required:")
        log("1) cp .env.example .env")
        log("2) Put your D-ID API key in DID_API_KEY")
        log("3) Re-run this script")
        log("Optional local fallback: install SadTalker and run again.")
        if run_sadtalker_fallback(image_path, audio_path, output_path):
            log("SadTalker fallback completed.")
            return 0
        return 2

    try:
        log("Uploading avatar image to D-ID...")
        image_url = did_upload_image(did_key, image_path)
        log(f"Image URL: {image_url}")

        talk_id = did_create_talk(did_key, image_url, args.script, audio_path)
        log(f"Talk created: {talk_id}")

        did_wait_and_download(did_key, talk_id, tmp_raw)
        add_burned_captions(tmp_raw, output_path, args.aspect_ratio)
        log(f"Success! Final video: {output_path}")
    except Exception as e:
        log(f"ERROR during generation: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
