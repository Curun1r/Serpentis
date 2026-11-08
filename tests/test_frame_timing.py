"""Maximum FPS follows the requested cap rather than rounded milliseconds."""
import pytest
from frame_timing import FrameLimiter


class Timer:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += max(seconds, 1e-12)


@pytest.mark.parametrize('cap', [30, 60, 120, 144, 240])
def test_frame_starts_respect_cap_and_measured_fps(cap):
    timer = Timer()
    limiter = FrameLimiter(timer.clock, timer.sleep)
    limiter.tick(cap)
    for _ in range(20):
        timer.now += .001
        dt = limiter.tick(cap)
        assert dt >= 1 / cap - 1e-12
    assert limiter.fps == pytest.approx(cap)


def test_cap_changes_apply_without_stale_deadlines():
    timer = Timer()
    limiter = FrameLimiter(timer.clock, timer.sleep)
    limiter.tick(30)
    assert limiter.tick(30) == pytest.approx(1 / 30)
    assert limiter.tick(144) == pytest.approx(1 / 144)
    assert limiter.tick(60) == pytest.approx(1 / 60)
    before = len(timer.waits)
    timer.now += .001
    assert limiter.tick(0) == pytest.approx(.001)
    assert len(timer.waits) == before


def test_over_budget_rendering_is_not_followed_by_catchup_frames():
    timer = Timer()
    limiter = FrameLimiter(timer.clock, timer.sleep)
    limiter.tick(60)
    timer.now += .1
    assert limiter.tick(60) == pytest.approx(.1)
    assert not timer.waits
    assert limiter.tick(60) == pytest.approx(1 / 60)


def test_game_loop_applies_changed_cap_on_next_frame(gameplay, monkeypatch):
    import pygame
    from game import GameState
    from settings_manager import Settings, FRAMERATES

    game = gameplay
    game.state = GameState.SETTINGS
    game._settings.focus.select(3)
    Settings.get().fps_index = FRAMERATES.index(60)
    caps = []

    class Finished(Exception):
        pass

    def tick(cap):
        caps.append(cap)
        if len(caps) == 3:
            raise Finished
        return .01

    monkeypatch.setattr(game._frame_limiter, 'tick', tick)
    monkeypatch.setattr(pygame.event, 'get', lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)])
    monkeypatch.setattr(game, '_present', lambda frame: None)
    with pytest.raises(Finished):
        game.run()
    assert caps == [60, 120, 144]
