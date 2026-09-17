"""Fresh local Codex CLI sessions with structured final messages."""
import json
import os
from pathlib import Path
import shutil
import subprocess

try:
    from .results import MAX_ATTEMPTS, EvaluationError, read_json, validate_result
except ImportError:
    from results import MAX_ATTEMPTS, EvaluationError, read_json, validate_result

HERE = Path(__file__).resolve().parent


def find_codex():
    executable = shutil.which("codex")
    if not executable:
        raise EvaluationError("Codex CLI not installed; install and authenticate codex first")
    help_text = subprocess.run([executable, "exec", "--help"], capture_output=True, text=True)
    required = ("--output-schema", "--output-last-message", "--ephemeral")
    if help_text.returncode or not all(flag in help_text.stdout for flag in required):
        raise EvaluationError("Codex CLI must support exec --output-schema, --output-last-message, and --ephemeral; update Codex")
    return executable


def invoke(executable, competitor, workspace, control, prompt, max_attempts=MAX_ATTEMPTS,
           model=None, journal=None):
    """The caller deletes control (including the private Codex home) before
    starting the other competitor. Only config/auth, never history, is copied.
    """
    control.mkdir()
    home = control / "codex-home"
    home.mkdir(mode=0o700)
    normal_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    for source in [normal_home / "config.toml", normal_home / "auth.json",
                   *normal_home.glob("*.config.toml")]:
        if source.is_file():
            shutil.copyfile(source, home / source.name)
            (home / source.name).chmod(0o600)
    env = dict(os.environ, CODEX_HOME=str(home), TMPDIR=str(workspace / ".eval-tmp"))
    (workspace / ".eval-tmp").mkdir(exist_ok=True)
    output = control / "final.json"
    command = [executable, "exec", "--ephemeral", "--skip-git-repo-check",
               "--sandbox", "read-only" if competitor == "agent_only" else "workspace-write",
               "--cd", str(workspace), "--output-schema", str(HERE / "schemas" / f"{competitor}.json"),
               "--output-last-message", str(output), "--color", "never"]
    # Override inherited permissions so a trusted source checkout is never an
    # additional writable root. /tmp must not implicitly expose the other copy.
    for setting in ['approval_policy="never"', 'history.persistence="none"',
                    'sandbox_workspace_write.writable_roots=[]',
                    'sandbox_workspace_write.exclude_slash_tmp=true',
                    'sandbox_workspace_write.exclude_tmpdir_env_var=true',
                    'sandbox_workspace_write.network_access=false',
                    'web_search="disabled"', 'features.memories=false',
                    'features.shell_snapshot=false', 'agents.enabled=false',
                    f'log_dir={json.dumps(str(home / "log"))}',
                    f'sqlite_home={json.dumps(str(home))}']:
        command += ["-c", setting]
    if journal is not None:
        command += ["--add-dir", str(journal)]
    if model:
        command += ["--model", model]
    command.append("-")
    (control / "prompt.md").write_text(prompt)
    with (control / "codex.log").open("w") as log:
        try:
            proc = subprocess.run(command, input=prompt, text=True, cwd=workspace,
                                  env=env, stdout=log, stderr=subprocess.STDOUT)
        except OSError as exc:
            raise EvaluationError(f"cannot start Codex CLI: {exc}") from exc
    if proc.returncode:
        raise EvaluationError(f"{competitor}: Codex exited with status {proc.returncode}; see logs")
    try:
        return validate_result(read_json(output), competitor, max_attempts)
    except EvaluationError as exc:
        raise EvaluationError(f"{competitor}: invalid structured Codex output: {exc}") from exc
