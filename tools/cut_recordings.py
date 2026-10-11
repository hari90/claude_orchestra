"""Cuts the recorded sound packs out of their source recordings.

The recordings are not kept in the repository. Download each one from the
link below, then pass its path:

  python3 tools/cut_recordings.py --typewriter ~/Downloads/typewriter.wav
  python3 tools/cut_recordings.py --laptop "~/Downloads/busy dev.wav"
  python3 tools/cut_recordings.py --mechanical keyboard.wav
  python3 tools/cut_recordings.py --piano ~/Downloads/piano.wav
  python3 tools/cut_recordings.py --orchestra ~/Downloads/orchestra.wav

WAV only, any sample width, mono or stereo. Convert a FLAC first; on macOS:
  afconvert -f WAVE -d LEI16 "mechanical keyboard.flac" keyboard.wav

Stdlib only and deterministic: the same recording always gives the same clips.
Times below are seconds into each recording.
"""
import argparse, array, math, os, wave

OUT = os.path.join(os.path.dirname(__file__), "..", "sounds")
# Every clip's peak is set by its event's level, then scaled by MASTER.
MASTER = 0.25
LEVEL = {"type": 0.7, "think": 0.4, "tool": 0.8, "done": 0.5}

# Olivetti Lettra 22 manual typewriter, recorded by keithpeter.
# https://freesound.org/people/keithpeter/sounds/123344/  (CC0 1.0)
TYPEWRITER = {
    # A second and a bit of real typing, each with no end-of-line bell in it.
    "type": [(23.165, 24.365), (36.245, 37.445), (81.26, 82.46), (96.645, 97.845)],
    # Hunt and peck: two isolated strikes, the second about half a second later.
    # Strikes whose tails die away cleanly, with nothing else in the mechanism after them.
    "think": [((43.285, 0.22), (62.635, 0.22), 0.5), ((40.14, 0.22), (66.775, 0.22), 0.6), ((12.85, 0.22), (65.925, 0.22), 0.45)],
    # A carriage return: the carriage sliding back, the stop, the line-feed
    # clicks. The slide is quiet in the room, so it is lifted to be heard.
    "tool": [(30.23, 31.45, 30.88), (76.23, 77.42, 76.98)],
    # The end-of-line bell, rung over a keystroke: kept by filtering for its
    # two partials (3070 Hz and 7667 Hz) and nothing else.
    "done": [(27.74, 28.6)],
}
BELL_PARTIALS = [(3070, 60, 1.0), (7667, 120, 0.45)]

# Apple MacBook Pro 2018 keyboard, recorded by khenshom, for the busy-dev pack.
# https://freesound.org/people/khenshom/sounds/565645/  (CC0 1.0)
LAPTOP = {
    "type": [(5.03, 6.23), (12.378, 13.578), (22.878, 24.078), (41.026, 42.226)],
    # Single keys taken from the typing, each with its own release and nothing after.
    "think": [((8.936, 0.15), (36.896, 0.15), 0.5), ((28.0, 0.15), (50.084, 0.15), 0.6), ((44.292, 0.15), (12.564, 0.15), 0.45)],
    "tool": [[(20.168, 0.22)], [(26.368, 0.17)]],  # Enter
    "done": [[(43.84, 0.3)]],  # the spacebar
}

# Piano loop by josefpres, for the lounge pack.
# https://freesound.org/people/josefpres/sounds/871796/  (CC0 1.0)
# It repeats every 16 s, so every cut comes from one cycle (16-32 s), and the
# pack ends on the piece's own last bars.
PIANO = {
    "type": [(20.85, 22.4), (22.4, 23.95), (28.85, 30.4), (30.4, 31.95)],  # flowing passages
    # Single chords, 0.75 s apart: each clip stops before the next chord, so it
    # fades within that.
    "think": [(16.99, 17.73), (18.24, 18.97), (24.99, 25.73)],  # played soft
    "tool": [(16.25, 16.98), (27.0, 27.73)],  # played full
    "done": [(126.45, 128.75)],  # the ending
}


# An amateur orchestra playing Mozart, recorded by kevp888, for the vienna pack.
# https://freesound.org/people/kevp888/sounds/848762/  (CC BY 4.0: credited in sounds/CREDITS.md)
# The music ends at 391 s; applause follows and is left out.
ORCHESTRA = {
    "type": [(51.75, 53.3), (70.0, 71.55), (306.75, 308.3), (379.5, 381.05)],  # lively, many attacks
    "think": [(95.5, 97.5), (271.25, 273.25), (313.5, 315.5)],  # soft, sustained
    "tool": [(62.23, 63.5), (331.9, 333.2)],  # sudden tutti accents
    "done": [(388.5, 391.5)],  # the last two chords, ringing out before the applause
}


# Cherry MX Blue mechanical keyboard, recorded by SamsterBirdies, for the in-the-zone pack.
# https://freesound.org/people/SamsterBirdies/sounds/489424/  (CC0 1.0)
MECHANICAL = {
    "type": [(21.074, 22.274), (26.106, 27.306), (67.586, 68.786), (92.082, 93.282)],
    "think": [((2.128, 0.16), (10.892, 0.16), 0.5), ((5.316, 0.16), (82.916, 0.16), 0.6), ((57.804, 0.16), (17.584, 0.16), 0.45)],
    "tool": [[(88.4, 0.25)], [(77.372, 0.22)]],  # the spacebar's thock
    "done": [[(88.4, 0.25), (77.372, 0.22)]],  # two thocks
}


def read(path):
    """A WAV as mono floats in -1..1, whatever its sample width and channels."""
    with wave.open(path) as w:
        ch, width, sr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if width == 2:
        data = array.array("h", raw)
    elif width == 3:
        data = [int.from_bytes(raw[i:i + 3], "little", signed=True) << 8 for i in range(0, len(raw), 3)]
    elif width == 4:
        data = array.array("i", raw)
    else:
        raise SystemExit(f"{path}: {8 * width}-bit samples are not supported")
    full = float(1 << 31) if width > 2 else 32768.0
    mono = [sum(data[i:i + ch]) / ch for i in range(0, len(data), ch)]
    return [s / full for s in mono], sr


def write(path, samples, sr, level):
    full = os.path.join(OUT, path + ".wav")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    scale = MASTER * level / max(1e-9, max(abs(s) for s in samples))
    data = array.array("h", (int(max(-1.0, min(1.0, s * scale)) * 32767) for s in samples))
    with wave.open(full, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def limit(x, drive=2.5):
    """A soft limiter: rounds off the sharpest strike peaks so a run of real
    keystrokes is as loud overall as the synthesized packs."""
    peak = max(1e-9, max(abs(s) for s in x))
    return [math.tanh(drive * s / peak) / math.tanh(drive) for s in x]


def gate(x, sr, open_below=16, closed_db=-24, hold=0.05, release=0.06, lookahead=0.002):
    """A noise gate for a quiet recording: between keystrokes the room and the
    microphone's hiss are pulled down by `closed_db`; each key opens it at once
    (it looks `lookahead` seconds ahead) and its natural tail is kept."""
    n, ahead = len(x), int(lookahead * sr)
    env, follow = [0.0] * n, 0.0
    fall = math.exp(-1 / (0.02 * sr))
    for i in range(n):
        v = abs(x[min(n - 1, i + ahead)])
        follow = v if v > follow else follow * fall
        env[i] = follow
    threshold = sorted(env)[int(0.99 * (n - 1))] * 10 ** (-open_below / 20)
    closed = 10 ** (closed_db / 20)
    held, g, out = 0, closed, []
    up, down = 1 - math.exp(-1 / (0.0005 * sr)), 1 - math.exp(-1 / (release * sr))
    for i, s in enumerate(x):
        if env[i] > threshold:
            held = int(hold * sr)
        else:
            held = max(0, held - 1)
        target = 1.0 if held else closed
        g += (target - g) * (up if target > g else down)
        out.append(s * g)
    return out


def cut(x, sr, a, b):
    return x[int(a * sr):int(b * sr)]


def fade(x, sr, fade_in=0.003, fade_out=0.03, smooth=False):
    """Fades both ends: linear by default, or `smooth`, a raised cosine that
    lets music die away slowly instead of stopping."""
    n, i_n, o_n = len(x), max(1, int(fade_in * sr)), max(1, int(fade_out * sr))

    def tail(i):
        k = min(1.0, (n - 1 - i) / o_n)
        return 0.5 - 0.5 * math.cos(math.pi * k) if smooth else k

    return [s * min(1.0, i / i_n) * tail(i) for i, s in enumerate(x)]


def bandpass(x, sr, bank):
    """Keeps only narrow bands around each (freq, bandwidth Hz, gain)."""
    out = [0.0] * len(x)
    for f, bw, g in bank:
        r = math.exp(-math.pi * bw / sr)
        c, r2, norm = 2 * r * math.cos(2 * math.pi * f / sr), r * r, (1 - r) * g
        y1 = y2 = 0.0
        for i, s in enumerate(x):
            y = s * norm + c * y1 - r2 * y2
            y2, y1 = y1, y
            out[i] += y
    return out


def keys(x, sr, presses, gap=0.17):
    """Single keystrokes in a row, `gap` seconds apart: [(time, length)]."""
    out = [0.0] * int((gap * (len(presses) - 1) + max(d for _, d in presses) + 0.05) * sr)
    for k, (a, d) in enumerate(presses):
        for i, s in enumerate(fade(cut(x, sr, a - 0.005, a + d), sr)):
            out[int(k * gap * sr) + i] += s * (1.0 if k == 0 else 0.8)
    return out


def phrases(pack, path, cuts):
    """A recording of music: each clip is one passage, faded at both ends."""
    x, sr = read(path)
    # Music cut mid-phrase must die away, not stop: long, smooth fade-outs.
    for event, fade_in, fade_out in (("type", 0.02, 0.55), ("think", 0.15, 0.5), ("tool", 0.005, 0.5), ("done", 0.02, 0.9)):
        for v, (a, b) in enumerate(cuts[event]):
            write(f"{pack}/{event}{v}", fade(cut(x, sr, a, b), sr, fade_in, fade_out, smooth=True), sr, LEVEL[event])
    print("wrote", pack, "from", os.path.basename(path))


def keyboard(pack, path, cuts, clean=lambda x, sr: x, drive=2.5):
    x, sr = read(path)
    for v, (a, b) in enumerate(cuts["type"]):
        write(f"{pack}/type{v}", limit(fade(clean(cut(x, sr, a, b), sr), sr, fade_out=0.08), drive), sr, LEVEL["type"])
    for v, (p1, p2, gap) in enumerate(cuts["think"]):
        write(f"{pack}/think{v}", limit(clean(keys(x, sr, [p1, p2], gap), sr), drive), sr, LEVEL["think"])
    for event in ("tool", "done"):
        for v, presses in enumerate(cuts[event]):
            write(f"{pack}/{event}{v}", clean(keys(x, sr, presses), sr), sr, LEVEL[event])
    print("wrote", pack, "from", os.path.basename(path))


def typewriter(path):
    x, sr = read(path)
    for v, (a, b) in enumerate(TYPEWRITER["type"]):
        write(f"newsroom/type{v}", limit(fade(cut(x, sr, a, b), sr, fade_out=0.08)), sr, LEVEL["type"])
    for v, ((a1, d1), (a2, d2), gap) in enumerate(TYPEWRITER["think"]):
        out = [0.0] * int((gap + d2 + 0.05) * sr)
        for at, (a, d) in ((0.0, (a1, d1)), (gap, (a2, d2))):
            for i, s in enumerate(fade(cut(x, sr, a - 0.005, a + d), sr)):
                out[int(at * sr) + i] += s
        write(f"newsroom/think{v}", limit(out), sr, LEVEL["think"])
    for v, (a, b, stop) in enumerate(TYPEWRITER["tool"]):
        seg = cut(x, sr, a, b)
        lift = int((stop - a - 0.02) * sr)  # +10 dB on the slide, eased into the stop
        seg = [s * (3.2 if i < lift else 1 + 2.2 * max(0.0, 1 - (i - lift) / (0.02 * sr))) for i, s in enumerate(seg)]
        write(f"newsroom/tool{v}", fade(seg, sr, fade_in=0.02, fade_out=0.08), sr, LEVEL["tool"])
    for v, (a, b) in enumerate(TYPEWRITER["done"]):
        write(f"newsroom/done{v}", fade(bandpass(cut(x, sr, a, b), sr, BELL_PARTIALS), sr, fade_out=0.25), sr, LEVEL["done"])
    print("wrote newsroom from", os.path.basename(path))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--typewriter", help="the Olivetti Lettra 22 recording (Freesound 123344)")
    p.add_argument("--laptop", help="the laptop keyboard recording, for busy-dev")
    p.add_argument("--mechanical", help="the mechanical keyboard recording, for in-the-zone")
    p.add_argument("--piano", help="the solo piano recording, for lounge")
    p.add_argument("--orchestra", help="the orchestral recording, for vienna")
    args = p.parse_args()
    if not any(vars(args).values()):
        p.error("pass at least one recording")
    if args.typewriter:
        typewriter(os.path.expanduser(args.typewriter))
    if args.laptop:
        # A quiet recording with audible hiss: gated, and limited more gently.
        keyboard("busy-dev", os.path.expanduser(args.laptop), LAPTOP, clean=gate, drive=1.5)
    if args.mechanical:
        keyboard("in-the-zone", os.path.expanduser(args.mechanical), MECHANICAL)
    if args.piano:
        phrases("lounge", os.path.expanduser(args.piano), PIANO)
    if args.orchestra:
        phrases("vienna", os.path.expanduser(args.orchestra), ORCHESTRA)


main()
