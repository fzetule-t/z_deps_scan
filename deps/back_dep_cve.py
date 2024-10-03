import json
from logging import Logger

import requests

from deps.models import Cve, Dep
from deps.utils_log import startMessage, endMessage, logResponse
from deps.utils_process import processChunks
from z_deps_scan.settings import OSS_ACTIVATED, OSS_CREDENTIALS_ENCODED


def getCoordinateKey(dep: Dep):
    return f"pkg:maven/{dep.group}/{dep.artifact}@{dep.version}"


def getCveListForDepTree(processLogger, depTreeRoot: Dep):
    visited = set()
    getAllDepFromTree(depTreeRoot, visited)
    visited.remove(depTreeRoot)
    if visited:
        getCveListFromDepList(processLogger, visited)


def getAllDepFromTree(dep: Dep, visited):
    if dep in visited:
        return
    visited.add(dep)
    # Visit all connected nodes through 'b_links'
    for link in dep.a_links.all():
        getAllDepFromTree(link.b, visited)


def getCveListFromDepList(processLogger: Logger, depList):
    if not OSS_ACTIVATED:
        return
    processLogger.info(startMessage())
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {OSS_CREDENTIALS_ENCODED}'
    }

    for chunkList in processChunks(depList, 100):
        coordinates = []
        mapDepList = {}
        for dep in chunkList:
            coordinate_key = getCoordinateKey(dep)
            coordinates += [coordinate_key]
            mapDepList[coordinate_key] = dep

        data = {
            "coordinates": coordinates
        }

        response = requests.post('https://ossindex.sonatype.org/api/v3/component-report', headers=headers,
                                 data=json.dumps(data))

        if response.status_code == 200:
            data = response.json()
            for item in data:
                # TODO extract parsing function appart
                coordinate_key = item.get('coordinates', '')
                # description = item.get('description', '')
                # reference = item.get('reference', '')
                vulnerabilities = item.get('vulnerabilities', [])

                if vulnerabilities:
                    for vulnerability in vulnerabilities:
                        cveId = vulnerability.get('id', '')
                        # display_name = vulnerability.get('displayName', '')
                        title = vulnerability.get('title', '')
                        # vuln_description = vulnerability.get('description', '')
                        cvssScore = vulnerability.get('cvssScore', '')
                        # cvss_vector = vulnerability.get('cvssVector', '')
                        # cwe = vulnerability.get('cwe', '')
                        # cve = vulnerability.get('cve', '')
                        vuln_reference = vulnerability.get('reference', '')
                        # external_references = vulnerability.get('externalReferences', [])

                        cve = Cve.objects.filter(pk=cveId).first()
                        if cve is None:
                            cve = Cve(
                                id=cveId,
                                # 'displayName': display_name,
                                title=title,
                                # 'description': vuln_description,
                                cvssScore=cvssScore,
                                # 'cvssVector': cvss_vector,
                                # 'cwe': cwe,
                                # cve=cve,
                                reference=vuln_reference,
                                # 'externalReferences': external_references
                            )
                        cve.save()
                        cve.repo_dep_list.add(mapDepList[coordinate_key])
                        cve.save()

            processLogger.info(endMessage())
        else:
            processLogger.error(endMessage() + " - " + logResponse(response))
            raise Exception(response.text)


def getCveListJsonForDep(dep: Dep):
    return list(dep.cve_list.all().values('id', 'title', 'cvssScore', 'reference').order_by('-cvssScore'))


def getCveListJsonViewForDep(dep: Dep):
    return list(dep.cve_list.all().values('id'))
