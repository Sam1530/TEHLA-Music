import asyncio
import shlex
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

import config
from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def git():
    """
    Safe Git handler:
    - Skips on Heroku / Container (no .git repo)
    - Runs only if proper repo exists
    """

    try:
        repo = Repo()
        LOGGER(__name__).info("Git repository detected.")

    except InvalidGitRepositoryError:
        LOGGER(__name__).warning(
            "No git repository found. Skipping auto-update (Heroku safe mode)."
        )
        return

    except GitCommandError as e:
        LOGGER(__name__).error(f"Git error: {e}")
        return

    # Optional: Only run update if explicitly enabled
    if not getattr(config, "AUTO_UPDATE", False):
        LOGGER(__name__).info("Auto-update disabled in config.")
        return

    try:
        REPO_LINK = config.UPSTREAM_REPO

        if config.GIT_TOKEN:
            GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
            TEMP_REPO = REPO_LINK.split("https://")[1]
            UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.GIT_TOKEN}@{TEMP_REPO}"
        else:
            UPSTREAM_REPO = REPO_LINK

        if "origin" not in repo.remotes:
            repo.create_remote("origin", UPSTREAM_REPO)

        origin = repo.remote("origin")

        LOGGER(__name__).info("Fetching latest updates...")
        origin.fetch()

        try:
            origin.pull()
        except GitCommandError:
            repo.git.reset("--hard", "FETCH_HEAD")

        install_req("pip3 install --no-cache-dir -r requirements.txt")

        LOGGER(__name__).info("Bot successfully updated from upstream.")

    except Exception as e:
        LOGGER(__name__).error(f"Update failed: {e}")
