#!/usr/bin/env python3
"""Assemble Blender-rendered frame shards into five 10-second MP4s.

Runs in the GitHub Actions assemble job after all 15 Cycles shards finish.
Verifies frames and shard receipts, encodes H.264, builds a 50s montage and a
contact sheet, then writes the receipt and validation JSON.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FPS = 30
FRAMES_PER_SCENE = 300
DURATION = 10.0
WIDTH, HEIGHT = 1920, 1080
SMALL_W, SMALL_H = 64, 36
REVISION = "five-worlds-blender-v2-cycles"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffmpeg_exe() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    local = ROOT / "web/node_modules/@ffmpeg-installer/linux-x64/ffmpeg"
    if local.is_file():
        return str(local)
    raise RuntimeError("ffmpeg not found on PATH or in web/node_modules")


def ffprobe_exe() -> str | None:
    return shutil.which("ffprobe")


def run(cmd, *, capture=True):
    return subprocess.run(cmd, cwd=ROOT, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def probe_video(path: Path) -> dict:
    probe = ffprobe_exe()
    if probe:
        proc = run([probe, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration,codec_name,pix_fmt",
                    "-of", "json", str(path)])
        data = json.loads(proc.stdout)["streams"][0]
        return {
            "width": int(data.get("width", 0)),
            "height": int(data.get("height", 0)),
            "fps": data.get("r_frame_rate"),
            "duration": float(data.get("duration", 0)),
            "nb_frames": int(data.get("nb_frames", 0)) if data.get("nb_frames") else None,
            "codec_name": data.get("codec_name"),
            "pix_fmt": data.get("pix_fmt"),
            "raw": data,
        }
    proc = run([ffmpeg_exe(), "-hide_banner", "-i", str(path)])
    text = proc.stderr
    dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    line = re.search(r"Video:\s*h264[^\n]*", text)
    dims = re.search(r",\s*(\d{3,5})x(\d{3,5})", line.group(0)) if line else None
    fps = re.search(r",\s*(\d+(?:\.\d+)?)\s+fps", line.group(0)) if line else None
    return {
        "width": int(dims.group(1)) if dims else 0,
        "height": int(dims.group(2)) if dims else 0,
        "fps": fps.group(1) if fps else None,
        "duration": (int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))) if dur else 0.0,
        "nb_frames": None,
        "raw": text[-2000:],
    }


def decode_metrics(path: Path, expected_frames: int) -> dict:
    ff = ffmpeg_exe()
    proc = subprocess.run(
        [ff, "-v", "error", "-i", str(path), "-vf", f"scale={SMALL_W}:{SMALL_H}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    data = proc.stdout
    frame_size = SMALL_W * SMALL_H
    result = {
        "returncode": proc.returncode,
        "decoded_frame_count": len(data) // frame_size,
        "exact_byte_count": len(data) == frame_size * expected_frames,
        "stderr": proc.stderr.decode("utf-8", "replace").strip(),
    }
    if proc.returncode != 0 or len(data) != frame_size * expected_frames:
        result["metrics"] = {}
        return result
    means, uniques, adjacent, previous = [], set(), [], None
    for i in range(expected_frames):
        frame = data[i * frame_size:(i + 1) * frame_size]
        means.append(sum(frame) / frame_size)
        uniques.add(hashlib.blake2b(frame, digest_size=4).digest())
        if previous is not None:
            adjacent.append(sum(abs(a - b) for a, b in zip(previous, frame)) / frame_size)
        previous = frame
    result["metrics"] = {
        "frame_count": expected_frames,
        "unique_frames": len(uniques),
        "min_frame_mean": round(min(means), 3),
        "max_frame_mean": round(max(means), 3),
        "first_frame_mean": round(means[0], 3),
        "last_frame_mean": round(means[-1], 3),
        "mean_adjacent_diff": round(sum(adjacent) / len(adjacent), 4),
        "max_adjacent_diff": round(max(adjacent), 4),
        "first_last_abs_diff": round(abs(means[0] - means[-1]), 4),
    }
    return result


def verify_frames(frames_root: Path, scenes: list[dict]) -> dict:
    errors = []
    checks = {"frames_root_exists": frames_root.is_dir()}
    scene_checks = []
    for e in scenes:
        idx = e["index"]
        d = frames_root / f"scene_{idx:02d}"
        expected = [f"frame_{f:04d}.png" for f in range(1, FRAMES_PER_SCENE + 1)]
        actual = sorted(p.name for p in d.glob("frame_*.png")) if d.is_dir() else []
        c = {
            "scene_dir_exists": d.is_dir(),
            "exact_300_frames": actual == expected,
            "all_frames_nonempty": all((d / n).stat().st_size > 10000 for n in expected) if actual == expected else False,
        }
        for k, v in c.items():
            if not v:
                errors.append(f"scene {idx} frame check failed: {k}")
        scene_checks.append(c)
    receipts = sorted(frames_root.glob("receipt_scene_*.json"))
    checks["fifteen_shard_receipts"] = len(receipts) == 15
    if len(receipts) != 15:
        errors.append(f"expected 15 shard receipts, found {len(receipts)}")
    ranges = {}
    for rpath in receipts:
        r = json.loads(rpath.read_text())
        idx = r["scene"]
        ranges.setdefault(idx, []).append((r["start"], r["end"]))
        if r.get("revision") != REVISION:
            errors.append(f"{rpath.name}: revision mismatch")
        if r.get("engine") != "CYCLES" or r.get("device") != "CPU":
            errors.append(f"{rpath.name}: not Cycles CPU")
        if r.get("width") != WIDTH or r.get("height") != HEIGHT:
            errors.append(f"{rpath.name}: resolution mismatch")
        if not r.get("lighting_audit", {}).get("pass"):
            errors.append(f"{rpath.name}: lighting audit failed")
        if r.get("frames_rendered") != 100:
            errors.append(f"{rpath.name}: expected 100 frames")
        for name, digest in r.get("frame_sha256", {}).items():
            p = frames_root / f"scene_{idx:02d}" / name
            if not p.is_file() or sha256(p) != digest:
                errors.append(f"{rpath.name}: frame SHA mismatch {name}")
                break
    for idx in range(1, 6):
        expected_ranges = [(1, 100), (101, 200), (201, 300)]
        if sorted(ranges.get(idx, [])) != expected_ranges:
            errors.append(f"scene {idx}: shard ranges {ranges.get(idx)} != {expected_ranges}")
    checks["shard_ranges_cover_1_to_300"] = not any("shard ranges" in e for e in errors)
    return {"checks": checks, "scene_checks": scene_checks, "errors": errors,
            "receipt_count": len(receipts)}


def encode_scene(e: dict, frames_root: Path, output: Path) -> Path:
    scene_dir = frames_root / f"scene_{e['index']:02d}"
    out = output / f"FiveWorlds_Blender_{e['index']:02d}_{e['slug']}_1080p30_10s.mp4"
    cmd = [
        ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(FPS), "-start_number", "1",
        "-i", str(scene_dir / "frame_%04d.png"),
        "-frames:v", str(FRAMES_PER_SCENE), "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-movflags", "+faststart",
        "-metadata", f"title=Five Worlds Blender - {e['name']}",
        "-metadata", f"comment=Blender Cycles CPU render; reference {e['reference']}",
        str(out),
    ]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg encode {out.name} failed: {proc.stderr[-2000:]}")
    print(f"[encode] {out}")
    return out


def make_combined(files: list[Path], output: Path, review: Path) -> Path:
    out = output / "FiveWorlds_Blender_AllScenes_1080p30_50s.mp4"
    list_path = review / "blender_concat.txt"
    list_path.write_text("\n".join(f"file '{p.resolve()}'" for p in files) + "\n")
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", str(list_path),
           "-c", "copy", "-movflags", "+faststart", str(out)]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"concat failed: {proc.stderr[-2000:]}")
    print(f"[encode] {out}")
    return out


def make_contact(files: list[Path], scenes: list[dict], review: Path, contact: Path) -> None:
    review.mkdir(parents=True, exist_ok=True)
    contact.parent.mkdir(parents=True, exist_ok=True)
    cell_w, cell_h = 480, 270
    sheet = Image.new("RGB", (cell_w * 3, cell_h * 2), (15, 15, 15))
    for e, mp4 in zip(scenes, files):
        frame = review / f"blender_final_scene_{e['index']:02d}.jpg"
        proc = run([ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", "5", "-i", str(mp4), "-frames:v", "1", "-q:v", "2", str(frame)])
        if proc.returncode != 0:
            raise RuntimeError(f"contact extract failed: {proc.stderr[-1000:]}")
        im = Image.open(frame).convert("RGB").resize((cell_w, cell_h))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, cell_w, 32), fill=(0, 0, 0))
        d.text((12, 8), f"{e['index']:02d} {e['name']} | Blender Cycles", fill=(255, 255, 255))
        i = e["index"] - 1
        sheet.paste(im, ((i % 3) * cell_w, (i // 3) * cell_h))
    sheet.save(contact, quality=90)
    print(f"[contact] {contact}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="frames")
    ap.add_argument("--output", default="output")
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--manifest", default="docs/FIVE_WORLDS_BLENDER_MANIFEST.json")
    ap.add_argument("--contact", default="assets/references/v6/00_five_worlds_blender_contact.jpg")
    ap.add_argument("--skip-encode", action="store_true", help="Use existing MP4s; still verify and rewrite receipt/validation")
    args = ap.parse_args()
    frames_root = (ROOT / args.frames).resolve()
    output = (ROOT / args.output).resolve()
    docs = (ROOT / args.docs).resolve()
    contact = (ROOT / args.contact).resolve()
    review = ROOT / "review/five_worlds_blender/final"
    manifest_path = (ROOT / args.manifest).resolve()
    output.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    review.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text())
    scenes = manifest["scenes"]

    frame_report = verify_frames(frames_root, scenes)
    if frame_report["errors"]:
        raise RuntimeError("Frame verification failed:\n" + "\n".join(frame_report["errors"]))

    files = [output / f"FiveWorlds_Blender_{e['index']:02d}_{e['slug']}_1080p30_10s.mp4" for e in scenes]
    if not args.skip_encode:
        for e, out in zip(scenes, files):
            encode_scene(e, frames_root, output)
        combined = make_combined(files, output, review)
    else:
        combined = output / "FiveWorlds_Blender_AllScenes_1080p30_50s.mp4"
    make_contact(files, scenes, review, contact)

    scene_entries = []
    all_errors = list(frame_report["errors"])
    for e, mp4 in zip(scenes, files):
        blend = ROOT / e["blend"]
        ref = ROOT / e["reference"]
        info = probe_video(mp4)
        dec = decode_metrics(mp4, FRAMES_PER_SCENE)
        m = dec["metrics"]
        checks = {
            "mp4_exists": mp4.is_file(),
            "blend_exists": blend.is_file(),
            "reference_exists": ref.is_file(),
            "blend_sha256": blend.is_file() and sha256(blend) == e["blend_sha256"],
            "reference_sha256": ref.is_file() and sha256(ref) == e["reference_sha256"],
            "duration_10s": abs(info["duration"] - DURATION) < 0.02,
            "resolution_1080p": info["width"] == WIDTH and info["height"] == HEIGHT,
            "fps_30": info["fps"] in ("30/1", "30", 30, 30.0),
            "h264": info.get("codec_name") == "h264" or "h264" in str(info["raw"]).lower(),
            "yuv420p": info.get("pix_fmt") == "yuv420p" or "yuv420p" in str(info["raw"]).lower(),
            "full_decode_rc0": dec["returncode"] == 0,
            "decoded_300_frames": dec["decoded_frame_count"] == FRAMES_PER_SCENE and dec["exact_byte_count"],
            "decode_stderr_empty": not dec["stderr"],
        }
        if m:
            checks.update({
                "no_black_or_white_frames": m["min_frame_mean"] > 3.0 and m["max_frame_mean"] < 252.0,
                "frames_are_distinct": m["unique_frames"] >= 290,
                "visible_frame_to_frame_motion": m["mean_adjacent_diff"] > 0.03,
                "no_huge_single_frame_jump": m["max_adjacent_diff"] < 80.0,
            })
        for k, v in checks.items():
            if not v:
                all_errors.append(f"scene {e['index']} check failed: {k}")
        scene_entries.append({
            "index": e["index"], "name": e["name"], "slug": e["slug"],
            "reference": e["reference"], "reference_sha256": e["reference_sha256"],
            "blend": e["blend"], "blend_sha256": e["blend_sha256"],
            "motion": e["motion"],
            "mp4": str(mp4.relative_to(ROOT)),
            "bytes": mp4.stat().st_size,
            "sha256": sha256(mp4),
            "frames": FRAMES_PER_SCENE, "fps": FPS, "duration_seconds": DURATION,
            "probe": {"width": info["width"], "height": info["height"], "fps": info["fps"],
                      "duration": info["duration"], "nb_frames": info["nb_frames"],
                      "codec_name": info.get("codec_name"), "pix_fmt": info.get("pix_fmt")},
            "decode_metrics": m,
            "checks": checks,
        })

    combined_info = probe_video(combined)
    combined_dec = decode_metrics(combined, 1500)
    combined_checks = {
        "exists": combined.is_file(),
        "duration_50s": abs(combined_info["duration"] - 50.0) < 0.03,
        "resolution_1080p": combined_info["width"] == WIDTH and combined_info["height"] == HEIGHT,
        "fps_30": combined_info["fps"] in ("30/1", "30", 30, 30.0),
        "full_decode_rc0": combined_dec["returncode"] == 0,
        "decoded_1500_frames": combined_dec["decoded_frame_count"] == 1500 and combined_dec["exact_byte_count"],
        "decode_stderr_empty": not combined_dec["stderr"],
    }
    for k, v in combined_checks.items():
        if not v:
            all_errors.append(f"combined check failed: {k}")

    receipt = {
        "revision": REVISION,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "route": {
            "selected": "Blender Cycles CPU scenes + 15-shard GitHub Actions render + ffmpeg assembly",
            "why": "User corrected the earlier WebGL prototype: recreate in Blender and render video like the Kerala animation.",
            "engine": "CYCLES", "device": "CPU",
            "shards": 15, "shards_per_scene": 3, "frames_per_shard": 100,
            "samples": manifest["spec"]["samples"],
            "denoising": manifest["spec"]["denoising"],
        },
        "spec": {
            "width": WIDTH, "height": HEIGHT, "fps": FPS,
            "frames_per_scene": FRAMES_PER_SCENE, "duration_seconds": DURATION,
            "scenes": 5, "total_duration_seconds": 50.0,
            "codec": "H.264 / yuv420p", "encoder": "libx264 CRF 18",
            "view_transform": "AgX - Medium High Contrast",
        },
        "manifest": str(manifest_path.relative_to(ROOT)),
        "reference_usage": manifest["reference_usage"],
        "contact_sheet": str(contact.relative_to(ROOT)),
        "combined_mp4": str(combined.relative_to(ROOT)),
        "combined_bytes": combined.stat().st_size,
        "combined_sha256": sha256(combined),
        "scenes": scene_entries,
    }
    (docs / "FIVE_WORLDS_BLENDER_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")

    validation = {
        "revision": REVISION,
        "validated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": not all_errors,
        "frame_verification": frame_report,
        "scene_results": [{"index": e["index"], "name": e["name"], "checks": e["checks"], "metrics": e["decode_metrics"]} for e in scene_entries],
        "combined": {"mp4": str(combined.relative_to(ROOT)), "checks": combined_checks,
                     "decoded_frame_count": combined_dec["decoded_frame_count"]},
        "errors": all_errors,
    }
    (docs / "FIVE_WORLDS_BLENDER_VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps({
        "pass": validation["pass"], "scenes": 5,
        "receipt": "docs/FIVE_WORLDS_BLENDER_RECEIPT.json",
        "validation": "docs/FIVE_WORLDS_BLENDER_VALIDATION.json",
        "errors": all_errors,
    }, indent=2))
    if all_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
