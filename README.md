# Coco Tree Talking UGC Video Generator

A Python project that turns a single product UGC avatar image into a **real talking promo video** (not a slideshow), with lip-sync animation via **D-ID API** and burned-in promo captions.

## What this project does
- Takes an avatar image (your blonde model holding the Flavita **The Coco Tree** carton).
- Uses a talking-avatar API (D-ID) to animate face/lips/head movement.
- Produces ~10-second MP4 promo video.
- Forces vertical social format (`9:16` or `4:5`).
- Burns captions into the video:
  - Refreshing
  - Fat free
  - High in potassium
  - The Coco Tree

## Project files
- `generate_video.py` – main script
- `requirements.txt` – Python deps
- `.env.example` – env template
- `output/` – generated video output folder

## Mac setup (exact steps)

1. **Install system tools (Homebrew + ffmpeg):**
   ```bash
   brew install ffmpeg
   ```

2. **Create and activate virtual env:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API key:**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set:
   ```env
   DID_API_KEY=your_real_d_id_api_key
   ```

5. **Run generation:**
   ```bash
   python generate_video.py \
     --image /mnt/data/ghostwriter_images/generated/a_bright_clean_indoor_kitchen_scene_with_a_smilin_1.png \
     --output output/coco_tree_talking_ugc.mp4 \
     --aspect-ratio 9:16
   ```

6. Final output:
   - `output/coco_tree_talking_ugc.mp4`

## Optional: provide your own voiceover
If you already have a voice file:
```bash
python generate_video.py \
  --image /path/to/avatar.png \
  --audio /path/to/voiceover.mp3 \
  --output output/coco_tree_talking_ugc.mp4
```

> Note: D-ID typically needs text or a hosted audio URL. In this starter project, custom local audio is accepted for fallback workflows and local SadTalker usage; D-ID request currently uses text mode for reliability.

## Fallback option (open-source)
If no D-ID API key is available, script attempts local **SadTalker** fallback (if installed in `SadTalker/`).

Expected fallback command:
```bash
python SadTalker/inference.py --driven_audio voiceover.mp3 --source_image avatar.png --result_dir output --still --preprocess full
```

## Troubleshooting
- **`No DID_API_KEY found`**: set `.env` correctly.
- **`ffmpeg not found`**: install with `brew install ffmpeg`.
- **Font errors on captions**: install Arial or change `font` in `generate_video.py`.
- **D-ID upload/auth errors**: verify API key and account limits.

## Realism tips for best UGC result
- Use a high-resolution portrait image with clear face visibility.
- Keep the product carton visible and not cropped out in source image.
- Keep script around 9–12 seconds for natural pacing.
- Use `9:16` for Reels/TikTok style outputs.
