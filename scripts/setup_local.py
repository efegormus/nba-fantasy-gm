"""Initialize local secrets and apply migrations without overwriting configuration."""

import secrets
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = root / ".env"
if not env.exists():
    template = (root / ".env.example").read_text()
    env.write_text(
        template.replace(
            "LOCAL_API_TOKEN=\n", "LOCAL_API_TOKEN=" + secrets.token_urlsafe(32) + "\n"
        )
    )
    env.chmod(0o600)
(root / "data").mkdir(exist_ok=True)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, check=True)
print("Local configuration and database ready. No Yahoo connection was attempted.")
