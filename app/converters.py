def srt_time(t: float) -> str:
    if t < 0: t = 0.0
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def vtt_time(t: float) -> str:
    if t < 0: t = 0.0
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    else:
        return f"{m:02d}:{s:02d}.{ms:03d}"

def to_srt(cues):
    lines = []
    for idx, c in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{srt_time(c['start'])} --> {srt_time(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)

def to_vtt(cues):
    lines = ["WEBVTT", ""]
    for c in cues:
        lines.append(f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)
