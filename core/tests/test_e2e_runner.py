import subprocess

import pytest

from deploy import e2e


@pytest.mark.parametrize("keep", [False, True])
def test_diagnostic_write_failure_preserves_original_error_and_cleanup_policy(monkeypatch, tmp_path, keep):
    report = tmp_path / "src-ui" / "test-results" / "services.log"
    report.mkdir(parents=True)
    monkeypatch.setattr(e2e, "ROOT", tmp_path)
    monkeypatch.setattr(e2e.sys, "argv", ["e2e.py", *(["--keep"] if keep else [])])
    original_error = subprocess.CalledProcessError(17, ["docker", "compose", "up"])
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if "up" in command:
            raise original_error
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(e2e.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError) as raised:
        e2e.main()

    assert raised.value is original_error
    assert any("down" in command for command in commands) is not keep
