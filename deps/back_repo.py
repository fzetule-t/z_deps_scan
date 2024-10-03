import os
import subprocess
from logging import Logger

from django.utils import timezone

from deps.back_git import getGitUrlWithAuthent, getGitStatus, getRemoteBranchList, getRemoteTagList, getLocalBranchList, \
    getLocalTagList
from deps.models import BuildConf, Repo, Identifier
from deps.models_enu import IdentifierType, UriType, TaskStatus, BuildType
from deps.utils_file import normalizeFilePath, getRepoDataDir, getPathPullLog, getBuildConfDataDir
from deps.utils_log import log, setupProcessLogger, endMessage, startMessage, message, exceptionMessage
from deps.utils_process import runCommand, parallelExec


def getIdentifierList(repo):
    repo.identifier_list.all().delete()
    identifierList = set()
    if repo.identifier_type == IdentifierType.BRANCH:
        for branch_list in [getRemoteBranchList(repo), getLocalBranchList(repo)]:
            if branch_list:
                identifierList.update(branch_list)
    elif repo.identifier_type == IdentifierType.TAG:
        for tagList in [getRemoteTagList(repo), getLocalTagList(repo)]:
            if tagList:
                identifierList.update(tagList)
    if identifierList is not None:
        for elem in identifierList:
            newIdentifier = Identifier(
                repo=repo,
                uri=elem,
                type=repo.identifier_type
            )
            newIdentifier.save()


def pull(repoList):
    parallelExec(pullTask, repoList)


def switch(repo: Repo):
    parallelExec(switchTask, [repo])


def switchTask(repo: Repo):
    # if repo.pull_status == TaskStatus.RUNNING or not repo.identifier_type:
    #     return
    pullInit(repo)
    logFilePath = getPathPullLog(repo.id)
    processLogger = setupProcessLogger(logFilePath)
    processLogger.info(startMessage(repo))
    try:
        identifierType = repo.identifier_type
        identifier = repo.identifier

        processLogger.info(f"Trying to switch to '{identifierType}' {identifier}.\n")

        pathLocal = repo.path_local
        if IdentifierType.BRANCH == identifierType:
            # Fetch all branches from origin
            fetch_command = gitCommand(["fetch"])
            runCommand(processLogger, pathLocal, fetch_command)

            # Check if the branch exists locally
            branch_exists_locally = False
            branch_command = gitCommand(["branch", "--list", identifier])
            branch_process = subprocess.run(branch_command, cwd=pathLocal, text=True, capture_output=True)
            if identifier in branch_process.stdout:
                branch_exists_locally = True

            # Check if the branch exists remotely
            branch_exists_remotely = False
            remote_branch_command = gitCommand(["ls-remote", "--exit-code", "origin", identifier])
            remote_branch_process = subprocess.run(remote_branch_command, cwd=pathLocal, text=True,
                                                   capture_output=True)
            if remote_branch_process.returncode == 0:
                branch_exists_remotely = True

            if branch_exists_locally:
                switch_command = gitCommand(["checkout", identifier])
                runCommand(processLogger, pathLocal, switch_command)
            elif branch_exists_remotely:
                # Checkout the branch if it exists remotely but not locally git switch --track origin/feature
                checkout_command = gitCommand(["checkout", "-b", identifier, 'origin/' + identifier])
                runCommand(processLogger, pathLocal, checkout_command)
            else:
                processLogger.warn(f"Branch '{identifier}' does not exist remotely.\n")
                pullFail(processLogger, repo)

        elif IdentifierType.TAG == identifierType:
            # git fetch --depth=1 origin tag <tag_name>
            command1 = gitCommand(["fetch", "--depth=1", "origin", "tag", identifier])
            command2 = gitCommand(["switch", "--detach", identifier])
            runCommand(processLogger, pathLocal, command1)
            runCommand(processLogger, pathLocal, command2)
        pullTask(repo, processLogger)
        pullSuccess(processLogger, repo)
    except Exception as e:
        processLogger.error(exceptionMessage(e))
        pullFail(processLogger, repo)
    finally:
        processLogger.info(endMessage(repo))


def gitCommand(cmd):
    return ["git"] + cmd  # No verbose for checkout ["--verbose"]


def gitRepoDirExists(repo: Repo):
    return repo.path_local and os.path.exists(repo.path_local)


def pullTask(repo: Repo, processLogger=None):
    pullInit(repo)
    logFilePath = getPathPullLog(repo.id)
    if processLogger is None:
        processLogger = setupProcessLogger(logFilePath)
    try:
        uriType = repo.uri_type
        path_local = repo.path_local

        # if repo.pull_status == TaskStatus.OK and repo.identifier_type == IdentifierType.TAG:
        #     with open(logFilePath, 'w') as logFile:
        #         logFile.write(f"This is a tag '{repo.identifier}' won't pull again.\n")
        #         pullSuccess(repo)
        #         return

        if uriType == UriType.GIT_URL:
            if not gitRepoDirExists(repo):
                os.makedirs(path_local)
                gitUrl = getGitUrlWithAuthent(processLogger, repo)
                command = gitCommand(["clone", "--depth=1", gitUrl, path_local])
                runCommand(processLogger, path_local, command)
                command = gitCommand(["config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"])
                runCommand(processLogger, path_local, command)
                identifierType, identifier = getGitStatus(processLogger, repo)
                repo.identifier_type = identifierType
                repo.identifier = identifier
                repo.save()
            else:
                command = gitCommand(["pull"])
                runCommand(processLogger, path_local, command)

        elif uriType == UriType.PATH:
            command = gitCommand(["pull"])
            runCommand(processLogger, path_local, command)
        detectBuildConf(repo, processLogger)
        pullSuccess(processLogger, repo)
    except Exception as e:
        processLogger.error(exceptionMessage(e))
        pullFail(processLogger, repo)


def pullInit(repo: Repo):
    repo.pull_status = TaskStatus.RUNNING
    repo.pull_start_dt = timezone.now()
    repo.pull_end_dt = None
    if repo.uri_type == UriType.PATH:
        repo.path_local = repo.uri
    elif repo.uri_type == UriType.GIT_URL:
        repoDataDir = getRepoDataDir(repo.id)
        repo.path_local = normalizeFilePath(repoDataDir + '/root')
        repoDataDir = repoDataDir
        if not os.path.exists(repoDataDir):
            os.makedirs(repoDataDir)

    repo.save()


def pullFail(processLogger, repo):
    repo.pull_end_dt = timezone.now()
    repo.pull_status = TaskStatus.KO
    repo.save()


def pullSuccess(processLogger, repo):
    repo.pull_end_dt = timezone.now()
    repo.pull_status = TaskStatus.OK
    repo.save()


def find_files(start_dir, searchedFilename):
    foundFiles = []
    for dirPath, dirNames, filenames in os.walk(start_dir):
        for filename in filenames:
            if filename == searchedFilename:
                foundFiles.append(os.path.join(dirPath, filename))
    return foundFiles


def detectBuildConf(repo, processLogger: Logger = None):
    logger = processLogger if processLogger else log
    logger.info(startMessage(repo))
    current_build_confs = list(repo.build_conf_list.all())
    current_build_conf_set = set((bc.type, bc.filePath) for bc in current_build_confs)

    cwd = repo.getCwd()
    new_build_conf_set = set()

    pom_files_found = find_files(cwd, 'pom.xml')
    if pom_files_found:
        logger.info(message(repo) + ", Found the following pom.xml files:")
        for pom_file in pom_files_found:
            pom_file = normalizeFilePath(pom_file)
            pom_file = pom_file.replace(normalizeFilePath(repo.path_local), '')
            logger.info(f"- {pom_file}")
            new_build_conf_set.add((BuildType.MAVEN, pom_file))

    gradle_files_found = find_files(cwd, 'build.gradle')
    if gradle_files_found:
        logger.info(message(repo) + ", Found the following build.gradle files:")
        for gradleFile in gradle_files_found:
            gradleFile = normalizeFilePath(gradleFile)
            gradleFile = gradleFile.replace(normalizeFilePath(repo.path_local), '')
            logger.info(f"- {gradleFile}")
            new_build_conf_set.add((BuildType.GRADLE, gradleFile))

    # Delete build_confs that no longer exist
    for build_conf in current_build_confs:
        if (build_conf.type, build_conf.filePath) not in new_build_conf_set:
            build_conf.delete()

    # Add new build_confs
    for build_type, file_path in new_build_conf_set:
        if (build_type, file_path) not in current_build_conf_set:
            buildConf = BuildConf(
                repo=repo,
                type=build_type,
                filePath=file_path
            )
            buildConf.save()
            buildConfDataDir = getBuildConfDataDir(buildConf)
            if not os.path.exists(buildConfDataDir):
                os.makedirs(buildConfDataDir)

    logger.info(endMessage(repo))
