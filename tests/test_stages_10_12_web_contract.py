from __future__ import annotations

from pathlib import Path


WEB_ROOT = Path(__file__).parents[1] / "src" / "autonomous_ai_world" / "web"


def test_stage_10_navigation_and_action_animation_are_present() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "NAV_ROUTES" in script
    assert "navigationRoute" in script
    assert "beginDirectAnimation" in script
    assert "animateAction" in script
    assert "scene.collisionsEnabled = true" in script


def test_stage_11_client_acknowledges_and_resumes_ordered_messages() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "protocol_ack" in script
    assert "message.message_id <= worldView.lastMessageId" in script
    assert "session_id=${encodeURIComponent(worldView.sessionId)}" in script
    assert 'message.type === "heartbeat"' in script


def test_stage_12_has_character_voice_profiles_and_controls() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    for speaker in ("pomni", "ragatha", "jax", "gangle", "kinger", "zooble", "caine"):
        assert f"{speaker}:" in script
    assert "SpeechSynthesisUtterance" in script
    assert "dominant_emotion" in script
    assert 'id="voices"' in page
    assert 'id="volume"' in page
