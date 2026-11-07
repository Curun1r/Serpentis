"""Procedural music for Serpentis — two tracks, numpy-powered.

  menu   — slow ambient A-minor pad + sparse arpeggio (menus / loading)
  battle — faster energetic track with punchy bass and rapid arpeggio

Usage:
    player = MusicPlayer()
    player.play_menu()
    player.play_battle()
    player.set_volume(0.4)
    player.pause() / player.resume()
"""
import threading
import math
import numpy as np
import pygame

_SR = 44100


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------

def _sine(freq, t, phase=0.0):
    return np.sin(2.0 * math.pi * freq * t + phase)


def _build_menu(loop_sec: float = 12.0) -> pygame.mixer.Sound:
    N = int(_SR * loop_sec)
    t = np.linspace(0.0, loop_sec, N, endpoint=False)

    # Bass drone
    env_b = 0.40 + 0.60 * (0.5 + 0.5 * _sine(1.0 / loop_sec, t))
    bass  = (0.55 * _sine(55,  t) +
             0.25 * _sine(110, t) +
             0.10 * _sine(165, t)) * env_b * 0.26

    # Pad (Am chord — A2 / C3 / E3 / G3 / A3)
    env_p = 0.35 + 0.65 * (0.5 + 0.5 * _sine(2.0 / loop_sec, t, math.pi * 0.6))
    pad   = (0.22 * _sine(110.0, t) + 0.18 * _sine(130.8, t) +
             0.16 * _sine(164.8, t) + 0.12 * _sine(196.0, t) +
             0.10 * _sine(220.0, t) + 0.06 * _sine(220.5, t)) * env_p * 0.28

    # Sparse arpeggio
    pitches  = [440.0, 523.3, 659.3, 880.0, 784.0, 659.3, 523.3, 440.0]
    note_dur = loop_sec / len(pitches)
    arp      = np.zeros(N)
    for i, f in enumerate(pitches):
        s = int(i * note_dur * _SR); e = min(s + int(note_dur * _SR), N)
        tn = np.arange(e - s) / _SR
        env = np.exp(-5.5 * tn / note_dur) * np.minimum(tn / 0.008, 1.0)
        arp[s:e] += (0.18 * np.sin(2*math.pi*f*tn) +
                     0.07 * np.sin(2*math.pi*f*2*tn)) * env
    arp *= 0.50

    return _finalise(bass + pad + arp)


def _build_battle(loop_sec: float = 8.0) -> pygame.mixer.Sound:
    """Energetic A-minor action track — clean harmonics, driving rhythm."""
    N = int(_SR * loop_sec)
    t = np.linspace(0.0, loop_sec, N, endpoint=False)

    # ── Driving bass — 4 pulses per loop, hard attack soft release ───
    beats    = 4
    bass_env = np.zeros(N)
    beat_len = N // beats
    for b in range(beats):
        s = b * beat_len
        tn = np.arange(min(beat_len, N - s)) / _SR
        bass_env[s:s + len(tn)] = np.exp(-4.5 * tn / (beat_len / _SR))
    bass = (0.65 * _sine(55,  t) +
            0.28 * _sine(110, t) +
            0.10 * _sine(165, t)) * bass_env * 0.55

    # ── Clean power-chord pad (A5 power: A + E, no thirds) ───────────
    env_p = 0.45 + 0.55 * np.abs(_sine(2.0 / loop_sec, t))
    pad   = (0.25 * _sine(110.0, t) +   # A2
             0.20 * _sine(164.8, t) +   # E3  (pure fifth — no dissonance)
             0.15 * _sine(220.0, t) +   # A3
             0.10 * _sine(329.6, t)) * env_p * 0.26  # E4

    # ── Melodic arpeggio — Am pentatonic, 12 notes ───────────────────
    # A4 C5 E5 G5 A5 G5 E5 C5  A4 C5 E5 A5
    pitches  = [440, 523, 659, 784, 880, 784, 659, 523,
                440, 523, 659, 880]
    note_dur = loop_sec / len(pitches)
    arp      = np.zeros(N)
    for i, f in enumerate(pitches):
        s  = int(i * note_dur * _SR)
        e  = min(s + int(note_dur * _SR * 0.65), N)
        tn = np.arange(e - s) / _SR
        env = np.exp(-6.0 * tn / note_dur) * np.minimum(tn / 0.006, 1.0)
        arp[s:e] += (0.20 * np.sin(2*math.pi * f       * tn) +
                     0.06 * np.sin(2*math.pi * f * 2.0  * tn)) * env
    arp *= 0.60

    # ── Sub-kick on beats 1 and 3 ─────────────────────────────────────
    kick_beats = [0, 2]
    for b in kick_beats:
        s = int(b * (loop_sec / 4) * _SR)
        e = min(s + int(0.15 * _SR), N)
        tn = np.arange(e - s) / _SR
        kick = np.exp(-30 * tn) * np.sin(2*math.pi * (90 - 55*tn/0.15) * tn)
        arp[s:e] += kick * 0.60

    # ── Hi-hat accent on every beat ───────────────────────────────────
    for b in range(8):
        s = int(b * (loop_sec / 8) * _SR)
        e = min(s + int(0.04 * _SR), N)
        tn = np.arange(e - s) / _SR
        noise = np.random.RandomState(b).uniform(-1, 1, len(tn))
        hat   = noise * np.exp(-80 * tn) * 0.12
        arp[s:e] += hat

    return _finalise(bass + pad + arp)


def _finalise(mix: np.ndarray) -> pygame.mixer.Sound:
    mix  = np.tanh(mix * 1.3) * 0.75
    peak = np.max(np.abs(mix))
    if peak > 1e-9:
        mix /= peak
    mix *= 0.88
    mono   = (mix * 32767).astype(np.int16)
    stereo = np.column_stack([mono, mono])
    return pygame.sndarray.make_sound(stereo)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class MusicPlayer:
    """Two-track music player with background synthesis."""

    def __init__(self):
        self._tracks:  dict[str, pygame.mixer.Sound | None] = {
            'menu': None, 'battle': None}
        self._ready:   dict[str, bool] = {'menu': False, 'battle': False}
        self._channel: pygame.mixer.Channel | None = None
        self._volume   = 0.35
        self._current  = ''
        self._pending  = ''   # track to start once ready

        # Build both tracks in background
        self._build_thread = threading.Thread(target=self._build_bg, daemon=True)
        self._build_thread.start()

    def _build_bg(self):
        self._tracks['menu']   = _build_menu()
        self._ready['menu']    = True
        self._tracks['battle'] = _build_battle()
        self._ready['battle']  = True
        if self._pending and self._ready.get(self._pending):
            self._switch(self._pending)

    # ------------------------------------------------------------------

    def _switch(self, name: str):
        if self._channel and self._channel.get_busy():
            self._channel.stop()
        snd = self._tracks.get(name)
        if snd is None:
            return
        self._current = name
        self._channel = snd.play(loops=-1)
        if self._channel:
            self._channel.set_volume(self._volume)

    def play_menu(self):
        if self._current == 'menu' and self._channel and self._channel.get_busy():
            return
        if self._ready['menu']:
            self._switch('menu')
        else:
            self._pending = 'menu'

    def play_battle(self):
        if self._current == 'battle' and self._channel and self._channel.get_busy():
            return
        if self._ready['battle']:
            self._switch('battle')
        else:
            self._pending = 'battle'

    def pause(self):
        if self._channel:
            self._channel.pause()

    def resume(self):
        if self._channel:
            self._channel.unpause()

    def stop(self):
        if self._channel:
            self._channel.stop()
        self._current = ''

    def close(self):
        """Finish background synthesis before the mixer is shut down."""
        self._build_thread.join()
        self.stop()

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))
        if self._channel:
            self._channel.set_volume(self._volume)
