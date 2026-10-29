import os, subprocess, sys
SCRIPT = os.path.abspath("minigit.py")

def run(cwd, *args):
    return subprocess.run([sys.executable, SCRIPT, *args], cwd=cwd,
                          capture_output=True, text=True).stdout

def test_commit_and_log(tmp_path):
    run(tmp_path, "init")
    (tmp_path / "a.txt").write_text("v1")
    run(tmp_path, "add", ".")
    run(tmp_path, "commit", "-m", "one")
    assert "one" in run(tmp_path, "log")

def test_checkout_restores_old_version(tmp_path):
    run(tmp_path, "init")
    f = tmp_path / "a.txt"
    f.write_text("v1")
    run(tmp_path, "add", ".")
    run(tmp_path, "commit", "-m", "one")
    first = run(tmp_path, "log").split()[1]
    f.write_text("v2")
    run(tmp_path, "add", ".")
    run(tmp_path, "commit", "-m", "two")
    run(tmp_path, "checkout", first)
    assert f.read_text() == "v1"
