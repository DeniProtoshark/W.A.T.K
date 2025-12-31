import os
import re
import tkinter as tk
from tkinter import filedialog

from mutagen import File
from mutagen.id3 import TPE1, TIT2, TCON, TBPM, TXXX


# ================= PARSER =================

MIX_KEYWORDS = [
    "VIP", "REMIX", "EDIT", "BOOTLEG", "REWORK",
    "FLIP", "EXTENDED", "CLUB MIX", "RADIO EDIT", "MASHUP"
]

GENRES = [
    "DRUM & BASS", "DNB", "NEUROFUNK", "NEURO",
    "LIQUID", "JUMP UP", "HARDSTYLE",
    "TECHNO", "HOUSE", "TRANCE", "DUBSTEP"
]

def normalize(text):
    return re.sub(r"\s+", " ", text.replace("_", " ")).strip()

def extract_bpm(text):
    m = re.search(r"\b(\d{2,3})\s*BPM\b", text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def extract_genre(text):
    up = text.upper()
    for g in GENRES:
        if g in up:
            return g
    return None

def extract_mix(text):
    mixes = set()

    for m in re.findall(r"[\(\[]([^\)\]]+)[\)\]]", text):
        u = m.upper()
        for k in MIX_KEYWORDS:
            if k in u:
                mixes.add(u)
                break

    for k in MIX_KEYWORDS:
        if re.search(rf"\b{re.escape(k)}\b", text, re.IGNORECASE):
            mixes.add(k)

    return " / ".join(sorted(mixes)) if mixes else None

def strip_extra(text):
    text = re.sub(r"\|.*$", "", text)
    text = re.sub(r"\b\d{2,3}\s*BPM\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[\(\[].*?[\)\]]", "", text)
    return normalize(text)

def split_artist_title(text):
    for sep in [" - ", " – ", " | "]:
        if sep in text:
            a, t = text.split(sep, 1)
            return normalize(a), normalize(t)
    return None, normalize(text)

def parse_track_metadata(name):
    raw = name
    w = normalize(name)

    bpm = extract_bpm(w)
    genre = extract_genre(w)
    mix = extract_mix(w)

    w = strip_extra(w)
    artist, title = split_artist_title(w)

    clean = normalize(" - ".join(x for x in [artist, title, mix] if x))

    return {
        "raw": raw,
        "artist": artist,
        "title": title,
        "mix": mix,
        "bpm": bpm,
        "genre": genre,
        "clean": clean
    }

# ================= BATCH TAGGER =================

SUPPORTED = (".mp3", ".flac", ".ogg", ".opus", ".wav")

def choose_folder():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title="Select folder with audio files")

def tag_file(path):
    name = os.path.splitext(os.path.basename(path))[0]
    meta = parse_track_metadata(name)

    audio = File(path, easy=False)
    if audio is None:
        print(f"❌ Unsupported: {path}")
        return

    try:
        if path.lower().endswith(".mp3"):
            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(TPE1(encoding=3, text=meta["artist"] or ""))
            audio.tags.add(TIT2(encoding=3, text=meta["title"] or ""))

            if meta["genre"]:
                audio.tags.add(TCON(encoding=3, text=meta["genre"]))
            if meta["bpm"]:
                audio.tags.add(TBPM(encoding=3, text=str(meta["bpm"])))
            if meta["mix"]:
                audio.tags.add(TXXX(encoding=3, desc="Mix", text=meta["mix"]))

        else:
            audio["artist"] = meta["artist"] or ""
            audio["title"] = meta["title"] or ""
            if meta["genre"]:
                audio["genre"] = meta["genre"]
            if meta["bpm"]:
                audio["bpm"] = str(meta["bpm"])
            if meta["mix"]:
                audio["mix"] = meta["mix"]

        audio.save()
        print(f"✅ {os.path.basename(path)}")

    except Exception as e:
        print(f"❌ ERROR {path}: {e}")

def process_folder(folder):
    count = 0
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(SUPPORTED):
                tag_file(os.path.join(root, f))
                count += 1
    print(f"\n🎧 Done. Files processed: {count}")

# ================= MAIN =================

if __name__ == "__main__":
    try:
        folder = choose_folder()
        if not folder:
            print("Folder not selected.")
        else:
            process_folder(folder)
    except Exception as e:
        print("FATAL:", e)
        input("Press Enter...")
