"""hyprctl.py talks to a real running Hyprland via subprocess — these tests
fake subprocess.run so they never actually invoke hyprctl (this suite may
well be running inside a real live Hyprland session, and a test calling the
real `hyprctl reload` would be a disruptive side effect no test should
have).
"""
import subprocess

from hyprform import hyprctl


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_is_available_requires_both_env_and_binary(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")
    assert hyprctl.is_available() is True

    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    assert hyprctl.is_available() is False


def test_list_monitors_returns_none_when_not_available(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    assert hyprctl.list_monitors() is None
    assert hyprctl.list_clients() is None


def test_list_monitors_parses_json(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")
    monkeypatch.setattr(
        hyprctl.subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stdout='[{"name": "DP-1", "width": 2560}]'),
    )
    monitors = hyprctl.list_monitors()
    assert monitors == [{"name": "DP-1", "width": 2560}]


def test_list_monitors_returns_none_on_bad_json(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")
    monkeypatch.setattr(hyprctl.subprocess, "run", lambda *a, **k: _FakeCompleted(stdout="not json"))
    assert hyprctl.list_monitors() is None


def test_list_monitors_returns_none_on_nonzero_exit(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")
    monkeypatch.setattr(hyprctl.subprocess, "run", lambda *a, **k: _FakeCompleted(returncode=1))
    assert hyprctl.list_monitors() is None


def test_list_monitors_returns_none_on_timeout(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")

    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="hyprctl", timeout=2)

    monkeypatch.setattr(hyprctl.subprocess, "run", raise_timeout)
    assert hyprctl.list_monitors() is None


def test_reload_reports_not_running(monkeypatch):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    ok, message = hyprctl.reload()
    assert not ok
    assert "running" in message.lower()


def test_reload_success(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")
    monkeypatch.setattr(hyprctl.subprocess, "run", lambda *a, **k: _FakeCompleted(returncode=0))
    ok, message = hyprctl.reload()
    assert ok
    assert "reloaded" in message.lower()


def test_reload_failure_surfaces_stderr(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(hyprctl.shutil, "which", lambda _cmd: "/usr/bin/hyprctl")
    monkeypatch.setattr(hyprctl.subprocess, "run", lambda *a, **k: _FakeCompleted(returncode=1, stderr="bad config"))
    ok, message = hyprctl.reload()
    assert not ok
    assert "bad config" in message
