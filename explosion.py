import pygame
from pygame.sprite import Sprite

FRAME_COUNT    = 8      # animation length in frames
FRAME_DURATION = 0.055  # seconds per frame → full animation ≈ 0.44 s
SIZE           = 72     # canvas size (px) of each generated frame


class Explosion(Sprite):
    """Short frame-based explosion animation played when an alien is destroyed.

    Frames are generated once and shared across all instances via a class-level
    cache, so spawning many explosions at once is cheap.
    """

    _frames: list | None = None  # lazily built, shared

    def __init__(self, cx: int, cy: int):
        super().__init__()
        if Explosion._frames is None:
            Explosion._frames = _build_frames()
        self._elapsed = 0.0
        self.image = Explosion._frames[0]
        self.rect  = self.image.get_rect(center=(cx, cy))

    def update(self, dt: float):
        self._elapsed += dt
        idx = int(self._elapsed / FRAME_DURATION)
        if idx >= FRAME_COUNT:
            self.kill()
            return
        self.image = Explosion._frames[idx]
        self.rect  = self.image.get_rect(center=self.rect.center)


# ---------------------------------------------------------------------------
# Frame generation — no external assets needed
# ---------------------------------------------------------------------------

def _build_frames() -> list[pygame.Surface]:
    """Generate FRAME_COUNT SRCALPHA surfaces using pygame.draw primitives."""
    frames = []
    cx = cy = SIZE // 2

    for i in range(FRAME_COUNT):
        t    = i / max(FRAME_COUNT - 1, 1)   # 0.0 → 1.0
        surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)

        # ── Outer expanding ring: yellow → orange → red, fades out ──
        outer_r = int(12 + t * 22)
        alpha   = int(255 * max(0.0, (1.0 - t) ** 1.2))
        green   = max(0, int(190 * (1.0 - t * 1.1)))

        # Layer several semi-transparent circles for a soft glow look
        for layer in range(5):
            lr = outer_r + layer * 5
            la = max(0, alpha - layer * 48)
            if la > 0:
                pygame.draw.circle(surf, (255, green, 0, la), (cx, cy), lr)

        # ── Bright white-yellow core: shrinks and fades early ──
        core_r = max(0, int(16 - t * 22))
        if core_r > 0:
            core_a = max(0, int(255 * (1.0 - t * 2.2)))
            pygame.draw.circle(surf, (255, 255, 200, core_a), (cx, cy), core_r)

        frames.append(surf)

    return frames
