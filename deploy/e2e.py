"""Build and exercise the disposable full-stack acceptance environment."""

import argparse
import os
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Build the production image and acceptance model layer")
    parser.add_argument(
        "--integrations", action="store_true", help="Also start S3-compatible storage and local AI models",
    )
    parser.add_argument("--keep", action="store_true", help="Keep this isolated stack and its data after running")
    parser.add_argument("--skip-tests", action="store_true", help="Start and seed the stack for interactive testing")
    args = parser.parse_args()
    environment = os.environ.copy()
    environment["E2E_LLM_ENABLED"] = "true" if args.integrations else "false"
    environment["E2E_INTEGRATIONS"] = "1" if args.integrations else "0"
    compose = ["docker", "compose", "-f", "deploy/compose.e2e.yml"]
    if args.integrations:
        compose += ["--profile", "integrations"]

    def run(command, **kwargs):
        subprocess.run(command, cwd=ROOT, env=environment, check=True, **kwargs)

    try:
        if args.build:
            run(["docker", "build", "-t", "docvault:e2e-base", "."])
            run(compose + ["build"])
        run(compose + ["up", "-d", "--wait", "--wait-timeout", "300"])
        run(compose + ["exec", "-T", "web", "python", "manage.py", "seed_e2e"])
        if args.integrations:
            for model in ("qwen2.5:0.5b", "all-minilm"):
                run(compose + ["exec", "-T", "ollama", "ollama", "pull", model])
        deadline = time.monotonic() + 120
        while True:
            try:
                with urlopen("http://127.0.0.1:18086/ready/", timeout=10) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("The acceptance database, Redis, Elasticsearch and worker did not become ready")
            time.sleep(2)
        if not args.skip_tests:
            npm = "npm.cmd" if os.name == "nt" else "npm"
            subprocess.run([npm, "run", "e2e"], cwd=ROOT / "src-ui", env=environment, check=True)
    finally:
        if not args.keep:
            subprocess.run(compose + ["logs", "--no-color", "--tail", "100"], cwd=ROOT, env=environment)
            subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], cwd=ROOT, env=environment)


if __name__ == "__main__":
    main()
