import tasks


def test_extra_arguments_are_passed_to_the_command(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks.subprocess, "call", lambda cmd, **kw: calls.append((cmd, kw["env"])) or 0)
    monkeypatch.setattr(tasks.sys, "argv", ["tasks.py", "run", "--server.port", "8502"])
    assert tasks.main() == 0
    cmd, env = calls[-1]
    assert cmd[-2:] == ["--server.port", "8502"] and "app/main.py" in cmd
    assert env["OFFLINE"] == "1"


def test_unknown_task_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(tasks.sys, "argv", ["tasks.py", "nope"])
    assert tasks.main() == 2
    assert "usage" in capsys.readouterr().out
