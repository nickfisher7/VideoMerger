# VideoMerger

This project provides a script to convert raw `.265` surveillance footage to `.mp4` and generate daily highlight videos.

## Usage

1. Place SD card contents under the `sd_cards/` directory. Each date should be in its own folder (e.g. `20250528`).
2. Run the pipeline:

```bash
python3 video_pipeline.py
```

Converted `.mp4` files appear in `converted/`. Highlights are written to `highlights_new_gen/`.
