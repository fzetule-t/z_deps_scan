from concurrent.futures import wait

import requests

from deps.models import Dep
from deps.utils_log import endMessage, logResponse, log
from deps.utils_process import parallelExec
from z_deps_scan.settings import CHECK_LATEST_VERSION


def updateLatestVersion(depList):
    if CHECK_LATEST_VERSION:
        futures = parallelExec(getLatestVersionTask, depList)
        wait(futures)


def getLatestVersionTask(dep: Dep):
    latestVersion = getLatestVersionApi(dep)
    if latestVersion is not None:
        dep.latestVersion = latestVersion
        dep.save()


def getLatestVersionApi(dep: Dep):
    # Construct the search URL
    url = f"https://search.maven.org/solrsearch/select?q=g:{dep.group}+AND+a:{dep.artifact}&rows=1&wt=json&sort=version desc"

    # Send the GET request
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        # Extract the latest version
        if data['response']['docs']:
            latest_version = data['response']['docs'][0]['latestVersion']
            return latest_version
        else:
            return None
    else:
        # TODO log aside
        log.info(
            endMessage() + f" - No latest found for group_id:artifact_id {dep.group}:{dep.artifact}\n{logResponse(response)}")
        return None
