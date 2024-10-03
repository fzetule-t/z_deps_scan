import re
import subprocess
from logging import Logger

from deps.models import Repo
from deps.models_enu import IdentifierType, UriType
from deps.utils_env import toEnvFormat
from deps.utils_log import startMessage, log, endMessage


def getCurrentBranch(gitRepo):
    try:
        current_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=gitRepo,
                                                 stderr=subprocess.STDOUT, text=True).strip()
        if current_branch == 'HEAD':
            return None
        return current_branch
    except subprocess.CalledProcessError as e:
        raise e


def getCurrentTag(gitRepo):
    result = subprocess.run(['git', 'describe', '--tags', '--exact-match'], cwd=gitRepo, capture_output=True,
                            text=True).stdout.strip()
    if result:
        return result
    return None


def getLocalBranchList(repo: Repo):
    log.info(startMessage(repo))
    result = subprocess.run(['git', 'branch'], capture_output=True, text=True, cwd= repo.getCwd())
    branches = result.stdout.split('\n')
    # Clean up the branch names and remove any empty lines
    branches = [branch.strip().replace('* ', '') for branch in branches if branch.strip()]
    return branches


def getRemoteBranchList(repo: Repo):
    log.info(startMessage(repo))
    try:
        args = ['git', 'ls-remote', '--heads']
        if repo.uri_type == UriType.GIT_URL:
            args.append(getGitUrlWithAuthent(log, repo))

        # Run git ls-remote --heads to list all remote branches
        result = subprocess.run(args, cwd=repo.getCwd(), capture_output=True, text=True,
                                check=True)
        # Extract branch names from the output
        branchList = [line.split('refs/heads/')[1].strip() for line in result.stdout.splitlines()]
        log.info(endMessage(repo) + ', result:\n' + str(branchList))
        return branchList
    except subprocess.CalledProcessError as e:
        log.error(f"Error occurred: {e.stderr}")
        return None


def getLocalTagList(repo):
    result = subprocess.run(['git', 'tag'], capture_output=True, text=True, cwd=repo.getCwd())
    tags = result.stdout.split('\n')
    # Clean up the tag names and remove any empty lines
    tags = [tag.strip() for tag in tags if tag.strip()]
    return tags


def getRemoteTagList(repo):
    log.info(startMessage(repo))
    try:
        args = ['git', 'ls-remote', '--tags']
        if repo.uri_type == UriType.GIT_URL:
            args.append(getGitUrlWithAuthent(log, repo))
        # Run git ls-remote --tags to list all remote tags
        result = subprocess.run(args, capture_output=True, text=True, check=True, cwd=repo.getCwd())
        # Extract tag names from the output
        tagList = [line.split('\t')[1].split('refs/tags/')[1].strip() for line in result.stdout.splitlines()]
        log.info(endMessage(repo) + ', result:\n' + str(tagList))
        return tagList
    except subprocess.CalledProcessError as e:
        log.error(f"Error occurred: {e.stderr}")
        return None


def getGitStatus(processLogger, repo):
    processLogger.info(startMessage(repo))
    cwd = repo.getCwd()
    # Get current branch or commit hash
    # git rev-parse --abbrev-ref HEAD
    # git rev-parse --abbrev-ref HEAD
    identifier = ''
    try:
        identifier = subprocess.check_output(['git', 'symbolic-ref', '--short', 'HEAD'], cwd=cwd).strip().decode(
            'utf-8')
        identifierType = IdentifierType.BRANCH
    except subprocess.CalledProcessError:
        try:
            identifier = subprocess.check_output(['git', 'describe', '--tags', '--exact-match'],
                                                 cwd=cwd).strip().decode('utf-8')
            identifierType = IdentifierType.TAG
        except subprocess.CalledProcessError:
            identifierType = None
            # identifier = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
            #                                      cwd=path_local).strip().decode('utf-8')
            # identifierType = IdentifierType.COMMIT
    # # Check if on a branch or tag
    # try:
    #     subprocess.check_output(['git', 'diff', '--quiet', 'HEAD'], cwd=path_local).strip().decode('utf-8')
    #     identifierType = IdentifierType.BRANCH
    # except subprocess.CalledProcessError:
    #     identifierType = IdentifierType.TAG
    processLogger.info(endMessage(repo) + f', result: identifierType {identifierType}, identifier {identifier}')
    return identifierType, identifier


def getGitUrlWithAuthent(logger: Logger, repo):
    logger.info(startMessage(repo))
    pattern = re.compile(r'(.*)github\.com(.*)')
    replacement = rf'\1{toEnvFormat(repo.user)}:{toEnvFormat(repo.pwd)}@github.com\2'
    url = re.sub(pattern, replacement, repo.uri)
    logger.info(startMessage(repo) + ', url: ' + url)
    return url


def getIdentifierType(repo: Repo):
    # commit = getCurrentCommit()
    cwd = repo.getCwd()
    branch = getCurrentBranch(cwd)
    if branch:
        return IdentifierType.BRANCH, branch
    tag = getCurrentTag(cwd)
    if tag:
        return IdentifierType.TAG, tag
    else:
        raise Exception("Not handled")

# def getCurrentCommit(gitRepo):
#     return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=gitRepo).stdout.strip()
