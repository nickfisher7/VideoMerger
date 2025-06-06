import os
import re
import subprocess
from datetime import datetime
from collections import defaultdict

# --- CONFIG ---
INPUT_FOLDER = "./converted"
HIGHLIGHT_FOLDER = "./highlights_new_gen"

os.makedirs(HIGHLIGHT_FOLDER, exist_ok=True)

def parse_time_range(name: str):
    match = re.match(r'[AP](\d{6})_(\d{6})', name)
    if match:
        try:
            start = datetime.strptime(match.group(1), "%H%M%S")
            end = datetime.strptime(match.group(2), "%H%M%S")
            return start, end
        except ValueError:
            return None, None
    return None, None

def extract_timestamp(file_path):
    basename = os.path.basename(file_path)
    match = re.match(r'(\d{8})_([AP]\d{6})_(\d{6})\.mp4', basename)
    if match:
        return datetime.strptime(match.group(2)[1:], "%H%M%S")
    return datetime.min


# Group converted files by date
date_buckets = defaultdict(list)

for file in os.listdir(INPUT_FOLDER):
    if file.endswith(".mp4"):
        match = re.match(r'(\d{8})_([AP]\d{6}_\d{6})_\d{6}\.mp4', file)
        if match:
            date = match.group(1)
            name = match.group(2)
            path = os.path.join(INPUT_FOLDER, file)
            date_buckets[date].append((name, path))

# Generate highlight videos
for date, files in date_buckets.items():
    A_clips = [x for x in files if x[0].startswith("A")]
    P_clips = [x for x in files if x[0].startswith("P")]
    timeline = sorted(files, key=lambda x: extract_timestamp(x[1]))

    highlight_segments = []

    for a_name, a_path in A_clips:
        a_start, a_end = parse_time_range(a_name)
        if not a_start or not a_end:
            continue

        prev_p = None
        next_p = None

        for p_name, p_path in P_clips:
            p_start, p_end = parse_time_range(p_name)
            if not p_start or not p_end:
                continue
            if p_end <= a_start:
                prev_p = (p_name, p_path)
            elif not next_p and p_start >= a_end:
                next_p = (p_name, p_path)
                break

        if prev_p:
            prev_seg = os.path.join(HIGHLIGHT_FOLDER, f"{date}_{a_name}_before.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-sseof", "-5", "-i", prev_p[1], "-t", "5",
                "-filter:v", "fps=25", "-c:v", "libx264", "-preset", "veryfast", prev_seg
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            highlight_segments.append(prev_seg)

        a_normalized = os.path.join(HIGHLIGHT_FOLDER, f"{date}_{a_name}_normalized.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", a_path, "-filter:v", "fps=25", "-c:v", "libx264",
            "-preset", "veryfast", a_normalized
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        highlight_segments.append(a_normalized)

        if next_p:
            next_seg = os.path.join(HIGHLIGHT_FOLDER, f"{date}_{a_name}_after.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", next_p[1], "-t", "5",
                "-filter:v", "fps=25", "-c:v", "libx264", "-preset", "veryfast", next_seg
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            highlight_segments.append(next_seg)

    if highlight_segments:
        highlight_list = os.path.join(HIGHLIGHT_FOLDER, f"{date}_highlight_list.txt")
        with open(highlight_list, "w") as f:
            for seg in highlight_segments:
                f.write(f"file '{os.path.abspath(seg)}'\n")

        highlight_output = os.path.join(HIGHLIGHT_FOLDER, f"{date}_highlight.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
            highlight_list, "-c", "copy", highlight_output
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
