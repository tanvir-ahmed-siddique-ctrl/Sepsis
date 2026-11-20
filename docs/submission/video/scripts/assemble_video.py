"""
Assemble the ~180s Congress pitch from VO + frames + live screenshots.
Fits portal limit (<=181s) by slight VO tempo adjust.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
FRAMES = ROOT / "frames"
SCREENS = ROOT / "screens"
EXPORT = ROOT / "export"
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:8]), "...")
    subprocess.run(cmd, check=True)


def still_clip(img: Path, seconds: float, out: Path, zoom: bool = False) -> None:
    """Ken Burns mild zoom optional."""
    frames = max(1, int(seconds * FPS))
    if zoom:
        # scale from 1.0 to 1.12 over the clip
        vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"zoompan=z='min(1.12,1+0.0008*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
            f"format=yuv420p"
        )
        run([
            FF, "-y", "-loop", "1", "-i", str(img),
            "-vf", vf, "-t", f"{seconds:.2f}", "-r", str(FPS),
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
            str(out),
        ])
    else:
        run([
            FF, "-y", "-loop", "1", "-i", str(img),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuv420p",
            "-t", f"{seconds:.2f}", "-r", str(FPS),
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
            str(out),
        ])


def concat(clips: list[Path], out: Path) -> None:
    lst = EXPORT / "concat.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def tempo_audio(src: Path, dest: Path, atempo: float) -> None:
    # chain atempo if needed (ffmpeg atempo range 0.5-2.0)
    filters = []
    rem = atempo
    while rem > 2.0:
        filters.append("atempo=2.0")
        rem /= 2.0
    while rem < 0.5:
        filters.append("atempo=0.5")
        rem /= 0.5
    filters.append(f"atempo={rem:.4f}")
    run([FF, "-y", "-i", str(src), "-filter:a", ",".join(filters), str(dest)])


def probe_duration(path: Path) -> float:
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration" in line:
            # Duration: HH:MM:SS.xx
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def pick(*names: str) -> Path:
    for n in names:
        p = SCREENS / n
        if p.exists() and p.stat().st_size > 40_000:
            return p
        p2 = FRAMES / n
        if p2.exists():
            return p2
    # fallback branded frame
    return FRAMES / "seg_demo.png"


def main() -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    work = EXPORT / "clips"
    work.mkdir(exist_ok=True)

    # Target segment lengths (seconds) — sum ~178
    # Problem 30, Solution 30, Demo 58, AI 20, Business 40 = 178
    targets = {
        "01_problem": 30.0,
        "02_solution": 30.0,
        "03_demo": 58.0,
        "04_ai": 20.0,
        "05_business": 40.0,
    }

    # Prepare tempo-adjusted VO per segment
    vo_parts = []
    for key, target in targets.items():
        src = AUDIO / f"{key}.wav"
        raw = probe_duration(src)
        atempo = max(0.85, min(1.35, raw / target)) if raw > 0 else 1.0
        dest = EXPORT / f"vo_{key}.wav"
        tempo_audio(src, dest, atempo)
        actual = probe_duration(dest)
        print(f"{key}: raw={raw:.1f}s -> {actual:.1f}s (atempo={atempo:.3f})")
        vo_parts.append((key, dest, actual))

    # Build visual timeline matching VO durations
    visual_clips: list[Path] = []

    # --- PROBLEM ---
    d = vo_parts[0][2]
    still_clip(FRAMES / "seg_problem.png", 2.0, work / "p0.mp4")
    still_clip(FRAMES / "01_problem.png", max(1.0, d - 2.0), work / "p1.mp4")
    visual_clips += [work / "p0.mp4", work / "p1.mp4"]

    # --- SOLUTION ---
    d = vo_parts[1][2]
    each = d / 4
    still_clip(FRAMES / "seg_solution.png", min(2.0, each), work / "s0.mp4")
    still_clip(FRAMES / "02_solution_clinical.png", each, work / "s1.mp4")
    still_clip(FRAMES / "02_solution_integration.png", each, work / "s2.mp4")
    rem = max(1.0, d - min(2.0, each) - 2 * each)
    still_clip(FRAMES / "02_solution_enable.png", rem, work / "s3.mp4")
    visual_clips += [work / "s0.mp4", work / "s1.mp4", work / "s2.mp4", work / "s3.mp4"]

    # --- DEMO (~58s) shot list ---
    d = vo_parts[2][2]
    demo_plan = [
        (pick("s00_splash.png"), 3.5, True),
        (pick("s00b_hero.png", "s00_splash.png"), 3.5, True),
        (pick("s01_signin.png"), 4.5, False),
        (FRAMES / "03_onprem.png", 4.0, False),
        (pick("s02_icu.png"), 5.0, True),
        (pick("s03_patient.png"), 3.5, True),
        (pick("s03b_drivers.png"), 3.5, True),
        (FRAMES / "03_trustgate.png", 6.5, False),
        (pick("s04_alerts.png"), 2.5, False),
        (pick("s05_handoff.png"), 2.0, False),
        (pick("s06_ward.png"), 2.5, False),
        (pick("s07_chart.png", "s03_patient.png"), 3.5, False),
        (pick("s07_chart.png", "s02_icu.png"), 3.5, False),  # admin/staff journey in product
        (FRAMES / "03_bangla_map.png", 6.0, False),
        (pick("s10_platform.png", "s09_contact.png"), 2.5, False),
        (pick("s09_contact.png"), max(2.0, d - 56.0), True),
    ]
    # normalize demo_plan durations to exact VO length
    planned = sum(t for _, t, _ in demo_plan)
    scale = d / planned if planned else 1.0
    for i, (img, secs, zoom) in enumerate(demo_plan):
        out = work / f"d{i:02d}.mp4"
        still_clip(img, max(0.8, secs * scale), out, zoom=zoom)
        visual_clips.append(out)

    # --- AI ---
    d = vo_parts[3][2]
    still_clip(FRAMES / "seg_ai.png", 2.0, work / "a0.mp4")
    still_clip(FRAMES / "04_ai_flow.png", max(1.0, d - 2.0), work / "a1.mp4")
    visual_clips += [work / "a0.mp4", work / "a1.mp4"]

    # --- BUSINESS ---
    d = vo_parts[4][2]
    biz = [
        (FRAMES / "seg_business.png", 2.0),
        (FRAMES / "05_packages.png", 6.0),
        (FRAMES / "05_fde_road.png", 7.0),
        (FRAMES / "05_tracks.png", 6.0),
        (FRAMES / "05_governance.png", 5.5),
        (FRAMES / "05_kpis.png", 6.0),
        (FRAMES / "06_endcard.png", 7.5),
    ]
    planned = sum(t for _, t in biz)
    scale = d / planned
    for i, (img, secs) in enumerate(biz):
        out = work / f"b{i:02d}.mp4"
        still_clip(img, max(0.8, secs * scale), out)
        visual_clips.append(out)

    video_only = EXPORT / "video_only.mp4"
    concat(visual_clips, video_only)

    # Concat VO
    vo_list = EXPORT / "vo_concat.txt"
    vo_wavs = []
    for key, path, _ in vo_parts:
        vo_wavs.append(path)
    vo_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in vo_wavs), encoding="utf-8")
    vo_all = EXPORT / "vo_all.wav"
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", str(vo_list), "-c", "copy", str(vo_all)])

    # Soft ambient bed (generated sine pad, very low)
    pad = EXPORT / "pad.wav"
    run([
        FF, "-y", "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.015:duration=200",
        "-t", "200", str(pad),
    ])

    final = EXPORT / "Auralis_180s_Congress_Pitch.mp4"
    # Mix: VO primary, pad ducked
    run([
        FF, "-y",
        "-i", str(video_only),
        "-i", str(vo_all),
        "-i", str(pad),
        "-filter_complex",
        "[1:a]volume=1.0[vo];[2:a]volume=0.12[pad];[vo][pad]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(final),
    ])

    dur = probe_duration(final)
    print(f"\nFINAL: {final}")
    print(f"DURATION: {dur:.2f}s")
    if dur > 181:
        print("WARNING: over 181s — trim further")
    else:
        print("OK: within portal limit")


if __name__ == "__main__":
    main()
