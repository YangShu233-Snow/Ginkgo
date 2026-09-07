import logging
import subprocess
import re
from pathlib import Path

from click import Abort
from ghp_import import ghp_import, GhpError

import ginkgo

logger = logging.getLogger(__name__)
BASEPATH = Path().cwd()

commit_default_message = "Deployed {sha} by Ginkgo {version}."

def _calculate_sha(repo_path: Path | None = None)->str:

    proc = subprocess.Popen(
        ['git', 'rev-parse', '--short', 'HEAD'],
        cwd=repo_path or None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, _ = proc.communicate()
    sha = stdout.decode('utf-8').strip()

    return sha

def _get_remote_url(remote_name: str)-> str:
    key = f'remote.{remote_name}.url'

    proc = subprocess.Popen(
        ['git', 'config', '--get', key],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, _ = proc.communicate()
    remote = stdout.decode('utf-8').strip()

    ssh_pattern = r'^\w+@\w+\.\w+:(.*?)\.git'
    http_pattern = r'^https?://.*?/(.*?)\.git'

    res = re.match(ssh_pattern, remote) or re.match(http_pattern, remote)

    if res:
        username, repo_name = res.group(1).split('/', 1)
        url = f'https://{username}.github.io/{repo_name}'

        return url

    return None

def deploy(
    site_dir: Path | str = 'site', 
    message: str | None = None,
    force: bool = False,
    no_history: bool = False,
    shell: bool = False
):
    remote_name = 'origin'
    if not message:
        message = commit_default_message.format(
            sha = _calculate_sha(BASEPATH),
            version = ginkgo.__version__
        )

    try:
        ghp_import(
                site_dir,
                mesg=message,
                remote='origin',
                branch='gh-pages',
                push=True,
                force=force,
                use_shell=shell,
                no_history=no_history,
                nojekyll=True,
            )
    except GhpError as ghp_e:
        logger.error(f'Deploy to remote repo failed!')
        logger.error(f'Error message: {ghp_e.message}')
        raise Abort()

    url = _get_remote_url(remote_name)

    if url:
        logger.info('Deploy successfully.')
        logger.info(f'Your Ginkgo website should be available at {url} after a while.')