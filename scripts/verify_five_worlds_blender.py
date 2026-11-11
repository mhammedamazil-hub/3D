#!/usr/bin/env python3
"""Independent local verification of the Blender-rendered Five Worlds MP4s."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS = 30
FRAMES = 300
DURATION = 10.0
WIDTH, HEIGHT = 1920, 1080
SMALL_W, SMALL_H = 64, 36


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    local = ROOT / "web/node_modules/@ffmpeg-installer/linux-x64/ffmpeg"
    if local.is_file():
        return str(local)
    raise RuntimeError("ffmpeg not found")


def info(path: Path) -> dict:
    proc = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)],
                          cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    text = proc.stderr
    dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    line = re.search(r"Video:\s*h264[^\n]*", text)
    dims = re.search(r",\s*(\d{3,5})x(\d{3,5})", line.group(0)) if line else None
    fps = re.search(r",\s*(\d+(?:\.\d+)?)\s+fps", line.group(0)) if line else None
    return {
        "duration": (int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))) if dur else 0.0,
        "width": int(dims.group(1)) if dims else 0,
        "height": int(dims.group(2)) if dims else 0,
        "fps": float(fps.group(1)) if fps else 0.0,
        "h264": bool(line),
        "yuv420p": "yuv420p" in (line.group(0) if line else ""),
    }


def decode(path: Path, frames: int) -> dict:
    frame_size = SMALL_W * SMALL_H
    proc = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(path), "-vf", f"scale={SMALL_W}:{SMALL_H}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    data = proc.stdout
    out = {
        "rc": proc.returncode,
        "frames": len(data) // frame_size,
        "exact": len(data) == frame_size * frames,
        "stderr": proc.stderr.decode("utf-8", "replace").strip(),
        "metrics": {},
    }
    if proc.returncode != 0 or not out["exact"]:
        return out
    means, uniques, adjacent, prev = [], set(), [], None
    for i in range(frames):
        fr = data[i * frame_size:(i + 1) * frame_size]
        means.append(sum(fr) / frame_size)
        uniques.add(hashlib.blake2b(fr, digest_size=4).digest())
        if prev is not None:
            adjacent.append(sum(abs(a - b) for a, b in zip(prev, fr)) / frame_size)
        prev = fr
    out["metrics"] = {
        "unique_frames": len(uniques),
        "min_frame_mean": round(min(means), 3),
        "max_frame_mean": round(max(means), 3),
        "mean_adjacent_diff": round(sum(adjacent) / len(adjacent), 4),
        "max_adjacent_diff": round(max(adjacent), 4),
    }
    return out


def main() -> int:
    receipt = json.loads((ROOT / "docs/FIVE_WORLDS_BLENDER_RECEIPT.json").read_text())
    ci_validation = json.loads((ROOT / "docs/FIVE_WORLDS_BLENDER_VALIDATION.json").read_text())
    manifest = json.loads((ROOT / "docs/FIVE_WORLDS_BLENDER_MANIFEST.json").read_text())
    errors = []
    checks = {
        "receipt_revision": receipt.get("revision") == "five-worlds-blender-v2-cycles",
        "ci_validation_pass": ci_validation.get("pass") is True and not ci_validation.get("errors"),
        "manifest_scene_count": len(manifest.get("scenes", [])) == 5,
        "contact_sheet_exists": (ROOT / receipt["contact_sheet"]).is_file(),
        "blend_builder_exists": (ROOT / "scripts/build_five_worlds_blender.py").is_file(),
        "renderer_exists": (ROOT / "scripts/render_five_worlds_blender.py").is_file(),
        "workflow_exists": (ROOT / ".github/workflows/render-five-worlds-blender.yml").is_file(),
    }
    for k, v in checks.items():
        if not v:
            errors.append(f"global check failed: {k}")
    scenes = []
    for entry in receipt["scenes"]:
        mp4 = ROOT / entry["mp4"]
        blend = ROOT / entry["blend"]
        ref = ROOT / entry["reference"]
        inf = info(mp4) if mp4.is_file() else {}
        dec = decode(mp4, FRAMES) if mp4.is_file() else {"rc": -1, "frames": 0, "exact": False, "stderr": "missing", "metrics": {}}
        m = dec["metrics"]
        c = {
            "mp4_exists": mp4.is_file(),
            "bytes": mp4.is_file() and mp4.stat().st_size == entry["bytes"],
            "sha256": mp4.is_file() and sha256(mp4) == entry["sha256"],
            "blend_exists": blend.is_file(),
            "blend_sha256": blend.is_file() and sha256(blend) == entry["blend_sha256"],
            "reference_exists": ref.is_file(),
            "reference_sha256": ref.is_file() and sha256(ref) == entry["reference_sha256"],
            "duration_10s": abs(inf.get("duration", 0) - DURATION) < 0.02,
            "resolution_1080p": inf.get("width") == WIDTH and inf.get("height") == HEIGHT,
            "fps_30": abs(inf.get("fps", 0) - FPS) < 0.01,
            "h264": inf.get("h264", False),
            "yuv420p": inf.get("yuv420p", False),
            "full_decode_rc0": dec["rc"] == 0,
            "decoded_300_frames": dec["frames"] == FRAMES and dec["exact"],
            "decode_stderr_empty": not dec["stderr"],
        }
        if m:
            c.update({
                "no_black_or_white_frames": m["min_frame_mean"] > 3.0 and m["max_frame_mean"] < 252.0,
                "frames_are_distinct": m["unique_frames"] >= 290,
                "visible_motion": m["mean_adjacent_diff"] > 0.03,
                "no_huge_jump": m["max_adjacent_diff"] < 80.0,
            })
        for k, v in c.items():
            if not v:
                errors.append(f"scene {entry['index']} check failed: {k}")
        scenes.append({"index": entry["index"], "name": entry["name"], "checks": c, "metrics": m})
    combined_path = ROOT / receipt["combined_mp4"]
    cinf = info(combined_path) if combined_path.is_file() else {}
    cdec = decode(combined_path, 1500) if combined_path.is_file() else {"rc": -1, "frames": 0, "exact": False, "stderr": "missing"}
    combined = {
        "exists": combined_path.is_file(),
        "bytes": combined_path.is_file() and combined_path.stat().st_size == receipt["combined_bytes"],
        "sha256": combined_path.is_file() and sha256(combined_path) == receipt["combined_sha256"],
        "duration_50s": abs(cinf.get("duration", 0) - 50.0) < 0.03,
        "resolution_1080p": cinf.get("width") == WIDTH and cinf.get("height") == HEIGHT,
        "fps_30": abs(cinf.get("fps", 0) - FPS) < 0.01,
        "h264": cinf.get("h264", False),
        "full_decode_rc0": cdec["rc"] == 0,
        "decoded_1500_frames": cdec["frames"] == 1500 and cdec["exact"],
        "decode_stderr_empty": not cdec["stderr"],
    }
    for k, v in combined.items():
        if not v:
            errors.append(f"combined check failed: {k}")
    result = {
        "revision": receipt["revision"],
        "validated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": not errors,
        "checks": checks,
        "scenes": scenes,
        "combined": combined,
        "errors": errors,
    }
    out = ROOT / "review/five_worlds_blender/local_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": result["pass"], "errors": errors, "report": str(out.relative_to(ROOT))}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
