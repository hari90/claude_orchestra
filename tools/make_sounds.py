"""Synthesizes the mod's sounds into sounds/ as 16-bit mono WAVs.

Run from the repository root: python3 tools/make_sounds.py (stdlib only).
"""
import math, os, random, struct, wave

SR = 22050
OUT = os.path.join(os.path.dirname(__file__), "..", "sounds")
MASTER = 0.25  # the same master volume as tools/cut_recordings.py


def write(name, samples):
    path = os.path.join(OUT, name + ".wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scale = MASTER * 0.85 / max(1e-9, max(abs(s) for s in samples))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(s * scale * 32767)) for s in samples))


def tick(dur=0.035, pitch=2400):
    """A dry wooden tick: a short, bright noise burst over a damped tone."""
    rng, lp, out = random.Random(1), 0.0, []
    for i in range(int(dur * SR)):
        t = i / SR
        lp += 0.6 * (rng.uniform(-1, 1) - lp)
        out.append(lp * math.exp(-t * 250) + 0.6 * math.sin(2 * math.pi * pitch * t) * math.exp(-t * 120))
    return out


write("tick", tick())
print("sounds written to", os.path.abspath(OUT))
