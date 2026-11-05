"""Qualify one installed workflow, with isolated runtime dependencies and stage receipts."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Stages:
    def __init__(self, output: Path):
        self.output = output
        self.rows = []

    def save(self):
        (self.output / "stages.json").write_text(json.dumps(self.rows, indent=2) + "\n")

    def run(self, name, command, *, cwd, timeout=300, env=None):
        row = {"stage": name, "status": "running", "log": f"{len(self.rows) + 1:02d}-{name}.log"}
        self.rows.append(row)
        self.save()
        print(f"START {name}", flush=True)
        started = time.monotonic()
        try:
            with (self.output / row["log"]).open("w") as stream:
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                try:
                    process.wait(timeout=timeout)
                except BaseException:
                    # Stop descendants too; a failed probe must not leave a search alive.
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGTERM)
                    with suppress(subprocess.TimeoutExpired):
                        process.wait(timeout=2)
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    raise
            row.update(
                status="passed" if process.returncode == 0 else "failed",
                returncode=process.returncode,
            )
        except subprocess.TimeoutExpired as error:
            row["status"] = "timeout"
            raise RuntimeError(f"{name} timed out; see {row['log']}") from error
        except OSError:
            row["status"] = "failed"
            raise
        except BaseException:
            row["status"] = "interrupted"
            raise
        finally:
            row["seconds"] = round(time.monotonic() - started, 3)
            self.save()
            print(f"{row['status'].upper()} {name}: {row['seconds']:.2f}s", flush=True)
        if row["status"] != "passed":
            raise RuntimeError(f"{name} failed; see {row['log']}")


def qualify(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    stages = Stages(output)
    stages.run(
        "build", ["uv", "build", "--no-sources", "--out-dir", str(output / "dist")], cwd=ROOT
    )
    wheels, sdists = list((output / "dist").glob("*.whl")), list((output / "dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected exactly one wheel and sdist")
    wheel, sdist = wheels[0], sdists[0]
    stages.run(
        "distribution-safety",
        [
            sys.executable,
            str(ROOT / "scripts/check_public_safety.py"),
            "--distribution",
            str(wheel),
            "--distribution",
            str(sdist),
        ],
        cwd=ROOT,
    )
    stages.run(
        "metadata", ["uv", "run", "--locked", "twine", "check", str(wheel), str(sdist)], cwd=ROOT
    )
    stages.run(
        "archive-inventory",
        [
            sys.executable,
            str(Path(__file__).with_name("inventory.py")),
            "--source",
            str(ROOT),
            "--wheel",
            str(wheel),
            "--sdist",
            str(sdist),
        ],
        cwd=ROOT,
    )
    with tempfile.TemporaryDirectory(prefix="hop-install-check-") as temporary:
        work = Path(temporary)
        with tarfile.open(sdist) as archive:
            archive.extractall(work / "sdist", filter="data")
        roots = list((work / "sdist").iterdir())
        if (
            len(roots) != 1
            or not (roots[0] / "examples/complete-construction/product-request.json").is_file()
        ):
            raise ValueError("Source distribution omits the public preparation example")
        prefix = work / "venv"
        stages.run("environment", ["uv", "venv", "--python", sys.executable, str(prefix)], cwd=work)
        constraints = work / "runtime.txt"
        stages.run(
            "runtime-lock",
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(constraints),
            ],
            cwd=ROOT,
        )
        stages.run(
            "install",
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(prefix / "bin/python"),
                "--constraint",
                str(constraints),
                str(wheel),
            ],
            cwd=work,
        )
        stages.run(
            "dependency-check",
            ["uv", "pip", "check", "--python", str(prefix / "bin/python")],
            cwd=work,
        )
        environment = {
            k: v
            for k, v in os.environ.items()
            if k not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
        }
        stages.run(
            "installed-workflow",
            [
                str(prefix / "bin/python"),
                "-I",
                str(Path(__file__).with_name("probe.py")),
                "--prefix",
                str(prefix),
                "--out",
                str(work / "case"),
                "--case",
                str(ROOT / "scripts/design-discovery-smoke.py"),
            ],
            cwd=work,
            env=environment,
        )
    (output / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "scope": "representative-installed-workflow",
                "artifacts": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (wheel, sdist)
                },
                "seconds": round(sum(row["seconds"] for row in stages.rows), 3),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    qualify(parser.parse_args().out.resolve())
