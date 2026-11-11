#!/usr/bin/env python3
"""Validate the five reference-driven 10-second renders and their receipt."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FFMPEG = ROOT / "web/node_modules/@ffmpeg-installer/linux-x64/ffmpeg"
RECEIPT_PATH = ROOT / "docs/FIVE_WORLDS_RECEIPT.json"
SHOTS_PATH = ROOT / "web/shots.json"
VALIDATION_PATH = ROOT / "docs/FIVE_WORLDS_VALIDATION.json"
FPS = 30
FRAMES = 300
DURATION = 10.0
WIDTH, HEIGHT = 1280, 720
SMALL_W, SMALL_H = 64, 36


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffmpeg_info(path: Path) -> dict:
    proc = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    text = proc.stderr
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    video_line_match = re.search(r"Video:\s*h264[^\n]*", text)
    dims_match = re.search(r",\s*(\d{3,5})x(\d{3,5})", video_line_match.group(0)) if video_line_match else None
    fps_match = re.search(r",\s*(\d+(?:\.\d+)?)\s+fps", video_line_match.group(0)) if video_line_match else None
    return {
        "duration": (
            int(duration_match.group(1)) * 3600
            + int(duration_match.group(2)) * 60
            + float(duration_match.group(3))
        ) if duration_match else None,
        "width": int(dims_match.group(1)) if dims_match else None,
        "height": int(dims_match.group(2)) if dims_match else None,
        "fps": float(fps_match.group(1)) if fps_match else None,
        "h264": bool(video_line_match),
        "yuv420p": "yuv420p" in (video_line_match.group(0) if video_line_match else ""),
        "raw": text,
    }


def decode_scaled(path: Path, width: int, height: int, expected_frames: int) -> dict:
    frame_size = width * height
    proc = subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(path),
         "-vf", f"scale={width}:{height}", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    data = proc.stdout
    checks = {
        "decode_returncode": proc.returncode,
        "decoded_frame_count": len(data) // frame_size if frame_size else 0,
        "exact_byte_count": len(data) == frame_size * expected_frames,
        "stderr": proc.stderr.decode("utf-8", "replace").strip(),
    }
    if proc.returncode != 0 or len(data) != frame_size * expected_frames:
        return {**checks, "metrics": {}}
    frame_means = []
    unique = set()
    adjacent = []
    previous = None
    for i in range(expected_frames):
        frame = data[i * frame_size:(i + 1) * frame_size]
        frame_means.append(sum(frame) / frame_size)
        unique.add(hashlib.blake2b(frame, digest_size=4).digest())
        if previous is not None:
            adjacent.append(sum(abs(a - b) for a, b in zip(previous, frame)) / frame_size)
        previous = frame
    metrics = {
        "frame_count": expected_frames,
        "unique_frames": len(unique),
        "min_frame_mean": round(min(frame_means), 3),
        "max_frame_mean": round(max(frame_means), 3),
        "first_frame_mean": round(frame_means[0], 3),
        "last_frame_mean": round(frame_means[-1], 3),
        "mean_adjacent_diff": round(sum(adjacent) / len(adjacent), 4),
        "max_adjacent_diff": round(max(adjacent), 4),
        "first_last_abs_diff": round(abs(frame_means[0] - frame_means[-1]), 4),
    }
    return {**checks, "metrics": metrics}


def main() -> int:
    errors: list[str] = []
    checks: dict = {}
    receipt = json.loads(RECEIPT_PATH.read_text())
    shots = json.loads(SHOTS_PATH.read_text())
    scene_code = (ROOT / "web/scene.js").read_text()
    checks["ffmpeg_binary_exists"] = FFMPEG.is_file() and os.access(FFMPEG, os.X_OK)
    checks["receipt_exists"] = RECEIPT_PATH.is_file()
    checks["five_scene_manifest"] = len(shots) == 5
    checks["receipt_revision"] = receipt.get("revision") == "five-worlds-v1-reference-driven-webgl"
    checks["scene_code_uses_all_references"] = all(s["reference"] in scene_code for s in shots)
    checks["scene_code_has_backplate_shader"] = "uMap" in scene_code and "makeReflectionPlane" in scene_code
    checks["deterministic_capture_hook"] = "window.setTime=" in scene_code and "renderer.getContext().finish()" in scene_code
    checks["capture_script_exists"] = (ROOT / "web/capture.cjs").is_file()
    checks["render_script_exists"] = (ROOT / "web/render.cjs").is_file()
    checks["contact_sheet_exists"] = (ROOT / receipt["contact_sheet"]).is_file()
    checks["contact_sheet_size"] = (ROOT / receipt["contact_sheet"]).stat().st_size > 20000 if checks["contact_sheet_exists"] else False
    for key, ok in list(checks.items()):
        if not ok:
            errors.append(f"global check failed: {key}")

    scene_results = []
    for shot, recorded in zip(shots, receipt["scenes"]):
        mp4 = ROOT / shot["mp4"]
        ref = ROOT / shot["reference"]
        ref_orig = ROOT / shot["reference_original"]
        entry = {"index": shot["index"], "name": shot["name"], "mp4": shot["mp4"], "checks": {}, "metrics": {}}
        entry["checks"]["mp4_exists"] = mp4.is_file()
        entry["checks"]["reference_exists"] = ref.is_file()
        entry["checks"]["reference_original_exists"] = ref_orig.is_file()
        entry["checks"]["reference_sha256"] = ref.is_file() and sha256(ref) == recorded["reference_sha256"]
        entry["checks"]["receipt_bytes"] = mp4.is_file() and mp4.stat().st_size == recorded["bytes"]
        entry["checks"]["receipt_sha256"] = mp4.is_file() and sha256(mp4) == recorded["sha256"]
        entry["checks"]["receipt_duration"] = recorded["duration_seconds"] == DURATION
        entry["checks"]["receipt_frames"] = recorded["frames"] == FRAMES
        entry["checks"]["receipt_fps"] = recorded["fps"] == FPS
        if not mp4.is_file():
            errors.append(f"scene {shot['index']}: MP4 missing")
            scene_results.append(entry)
            continue
        info = ffmpeg_info(mp4)
        entry["checks"].update({
            "duration_10s": info["duration"] is not None and abs(info["duration"] - DURATION) < 0.02,
            "resolution_1280x720": info["width"] == WIDTH and info["height"] == HEIGHT,
            "fps_30": info["fps"] is not None and abs(info["fps"] - FPS) < 0.01,
            "h264": info["h264"],
            "yuv420p": info["yuv420p"],
        })
        decoded = decode_scaled(mp4, SMALL_W, SMALL_H, FRAMES)
        entry["metrics"] = decoded["metrics"]
        entry["checks"].update({
            "full_decode_rc0": decoded["decode_returncode"] == 0,
            "decoded_300_frames": decoded["decoded_frame_count"] == FRAMES and decoded["exact_byte_count"],
            "decode_stderr_empty": not decoded["stderr"],
        })
        m = decoded["metrics"]
        if m:
            entry["checks"].update({
                "no_black_or_white_frames": m["min_frame_mean"] > 3.0 and m["max_frame_mean"] < 252.0,
                "frames_are_distinct": m["unique_frames"] >= 290,
                "visible_frame_to_frame_motion": m["mean_adjacent_diff"] > 0.05,
                "first_last_change": m["first_last_abs_diff"] > 0.01,
                "no_huge_single_frame_jump": m["max_adjacent_diff"] < 80.0,
            })
        for key, ok in entry["checks"].items():
            if not ok:
                errors.append(f"scene {shot['index']} check failed: {key}")
        scene_results.append(entry)

    combined_path = ROOT / receipt["combined_mp4"]
    combined = {"mp4": receipt["combined_mp4"], "checks": {}, "metrics": {}}
    combined["checks"]["exists"] = combined_path.is_file()
    combined["checks"]["receipt_bytes"] = combined_path.is_file() and combined_path.stat().st_size == receipt["combined_bytes"]
    combined["checks"]["receipt_sha256"] = combined_path.is_file() and sha256(combined_path) == receipt["combined_sha256"]
    if combined_path.is_file():
        info = ffmpeg_info(combined_path)
        combined["checks"].update({
            "duration_50s": info["duration"] is not None and abs(info["duration"] - 50.0) < 0.03,
            "resolution_1280x720": info["width"] == WIDTH and info["height"] == HEIGHT,
            "fps_30": info["fps"] is not None and abs(info["fps"] - FPS) < 0.01,
            "h264": info["h264"],
        })
        decoded = decode_scaled(combined_path, 32, 18, 1500)
        combined["metrics"] = {"decoded_frame_count": decoded["decoded_frame_count"], "exact_byte_count": decoded["exact_byte_count"]}
        combined["checks"].update({
            "full_decode_rc0": decoded["decode_returncode"] == 0,
            "decoded_1500_frames": decoded["decoded_frame_count"] == 1500 and decoded["exact_byte_count"],
            "decode_stderr_empty": not decoded["stderr"],
        })
    for key, ok in combined["checks"].items():
        if not ok:
            errors.append(f"combined check failed: {key}")

    validation = {
        "revision": receipt["revision"],
        "validated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": not errors,
        "checks": checks,
        "scenes": scene_results,
        "combined": combined,
        "errors": errors,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps({
        "pass": validation["pass"],
        "scenes": len(scene_results),
        "validation": str(VALIDATION_PATH.relative_to(ROOT)),
        "errors": errors,
    }, indent=2))
    return 0 if validation["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
