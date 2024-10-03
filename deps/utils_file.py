import json
import os
import re
import shutil

from django.http import HttpResponse, JsonResponse

from deps.utils_log import log, startMessage, endMessage, exceptionMessage
from z_deps_scan.settings import DATA_DIR


def sanitize_folder_name(folderName):
    # Define a regex pattern to match characters that are not compatible
    # with folder names (Windows example)
    illegalChars = r'[<>:"/\\|?*]'

    # Replace illegal characters with an underscore
    sanitizedName = re.sub(illegalChars, '_', folderName)

    return sanitizedName


def getRepoDataDir(repoId):
    repoDataDir = f"{DATA_DIR}/repos/{str(repoId)}"
    return repoDataDir


def getPathLog(repoId, cmd):
    return getRepoDataDir(repoId) + '/' + cmd + '.log'


def getPathPullLog(repoId):
    return getPathLog(repoId, 'pull')


def getBuildConfDataDir(buildConf):
    buildConfDataDir = getRepoDataDir(buildConf.repo.id) + '/buildConfs/' + str(buildConf.id)
    return buildConfDataDir


def getPathDepListLog(buildConf):
    return getBuildConfDataDir(buildConf) + '/deps.list.log'


def getPathDepListJson(buildConf):
    return getBuildConfDataDir(buildConf) + '/deps.list.json'


def getPathDepTreeLog(buildConf):
    return getBuildConfDataDir(buildConf) + '/deps.tree.log'


def getPathDepsTreeJson(buildConf):
    return getBuildConfDataDir(buildConf) + '/deps.tree.json'


def getPathDepsTreeViewJson(buildConf):
    return getBuildConfDataDir(buildConf) + '/deps.tree.view.json'


def getBuildConfComparisonDataDir(comparisonId):
    return f"{DATA_DIR}/comparisons/{comparisonId}"


def getComparisonResultFilePath(comparisonId):
    return getBuildConfComparisonDataDir(comparisonId) + "/comparison_result.json"


def downloadFile(filePath):
    if os.path.exists(filePath):
        # Open the file in read-binary mode
        with open(filePath, 'r') as f:
            response = HttpResponse(f.read(), content_type='text/plain')
            # attachment
            response['Content-Disposition'] = 'inline; filename="' + os.path.basename(f.name) + '"'
            return response
    else:
        return HttpResponse("File not found", status=404)


def downloadJson(filePath):
    if os.path.exists(filePath):
        # Open the file in read-binary mode
        with open(filePath, 'r') as f:
            data = json.load(f)
            return JsonResponse(data, safe=False)
    else:
        return HttpResponse("File not found", status=404)


def trimBeforeRoot(buildConf):
    return buildConf.filePath


def normalizeFilePath(filePath):
    return filePath.replace('\\', '/')


def deleteDir(path):
    log.info(startMessage() + f': {path}')
    try:
        if not path or not os.path.exists(path):
            log.info(f"No need to delete dir: {path}")
        else:
            shutil.rmtree(path)
            log.info(endMessage() + f': {path}')

    except Exception as e:
        # Handle any other exceptions
        log.error(exceptionMessage(e))
        raise e


def getEnclosingDirPath(filePath):
    return os.path.dirname(filePath)
