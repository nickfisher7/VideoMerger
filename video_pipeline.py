import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

SD_ROOT = Path('sd_cards')  # root directory containing date folders
CONVERTED_DIR = Path('converted')
HIGHLIGHT_DIR = Path('highlights_new_gen')
TMP_DIR = Path('tmp_segments')

CONVERTED_DIR.mkdir(exist_ok=True)
HIGHLIGHT_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)

FILE_RE = re.compile(r'(?P<date>\d{8})_(?P<type>[AP])(?P<start>\d{6})_(?P<end>\d{6})\.mp4$')


def run(cmd: List[str]):
    print('Running', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def convert_h265_files():
    """Convert .265 files found under SD_ROOT to mp4 in CONVERTED_DIR."""
    for h265 in SD_ROOT.rglob('*.265'):
        m = re.search(r'(\d{8})', str(h265))
        if not m:
            continue
        date = m.group(1)
        name = f"{date}_{h265.stem}.mp4"
        out = CONVERTED_DIR / name
        if out.exists():
            continue
        out_tmp = out.with_suffix('.tmp.mp4')
        out_tmp.parent.mkdir(parents=True, exist_ok=True)
        run(['ffmpeg', '-y', '-i', str(h265), '-c', 'copy', str(out_tmp)])
        out_tmp.rename(out)


def parse_info(path: Path):
    m = FILE_RE.match(path.name)
    if not m:
        return None
    info = m.groupdict()
    info['path'] = path
    return info


def group_by_date() -> dict:
    groups = {}
    for mp4 in CONVERTED_DIR.glob('*.mp4'):
        info = parse_info(mp4)
        if not info:
            continue
        date = info['date']
        groups.setdefault(date, []).append(info)
    for date, files in groups.items():
        files.sort(key=lambda x: x['start'])
    return groups


def extract_clip(src: Path, start: Optional[str], duration: float, dest: Path):
    """Extract clip using ffmpeg with fps=25."""
    cmd = ['ffmpeg', '-y']
    if start:
        cmd += ['-ss', start]
    cmd += ['-i', str(src), '-t', str(duration),
            '-vf', 'fps=25', '-af', 'aresample=async=1',
            '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(dest)]
    run(cmd)


def get_duration(file: Path) -> float:
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(file)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def build_highlights(groups: dict):
    for date, files in groups.items():
        segments = []
        for i, info in enumerate(files):
            if info['type'] != 'A':
                continue
            before = next((f for f in reversed(files[:i]) if f['type'] == 'P'), None)
            after = next((f for f in files[i+1:] if f['type'] == 'P'), None)

            seq_parts = []
            if before:
                dur = get_duration(before['path'])
                start = max(dur - 5, 0)
                seg = TMP_DIR / f"{date}_before_{i}.mp4"
                extract_clip(before['path'], str(start), 5, seg)
                seq_parts.append(seg)
            seg_a = TMP_DIR / f"{date}_alarm_{i}.mp4"
            extract_clip(info['path'], None, get_duration(info['path']), seg_a)
            seq_parts.append(seg_a)
            if after:
                seg = TMP_DIR / f"{date}_after_{i}.mp4"
                extract_clip(after['path'], '0', 5, seg)
                seq_parts.append(seg)
            # create concat list
            list_file = TMP_DIR / f"{date}_list_{i}.txt"
            with list_file.open('w') as f:
                for part in seq_parts:
                    f.write(f"file '{part.resolve()}'\n")
            merged = TMP_DIR / f"{date}_merged_{i}.mp4"
            run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
                 '-c', 'copy', str(merged)])
            segments.append(merged)

        if not segments:
            continue
        list_file = TMP_DIR / f"{date}_all.txt"
        with list_file.open('w') as f:
            for seg in segments:
                f.write(f"file '{seg.resolve()}'\n")
        out = HIGHLIGHT_DIR / f"{date}_highlight.mp4"
        run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
             '-c', 'copy', str(out)])


if __name__ == '__main__':
    convert_h265_files()
    groups = group_by_date()
    build_highlights(groups)
