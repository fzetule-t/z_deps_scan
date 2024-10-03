import json
import os
import re
import xml.etree.ElementTree as ET

from django.utils import timezone

from deps.back_dep_cve import getCveListFromDepList, getCveListJsonForDep
from deps.back_dep_latest import updateLatestVersion
from deps.back_dep_tree import replaceLeadingBySpace
from deps.models import Dep, BuildConf
from deps.models_enu import TaskStatus, BuildType, VersionStatus
from deps.utils_file import getPathDepListLog, getPathDepListJson, getEnclosingDirPath
from deps.utils_log import setupProcessLogger, endMessage, startMessage, exceptionMessage
from deps.utils_process import runCommand, parallelExec
from z_deps_scan.settings import MAVEN_EXEC, MAVEN_SETTINGS_PATH, OSS_ACTIVATED, GRADLEW_EXEC


def depListExtractInit(processLogger, buildConf):
    processLogger.info(startMessage(buildConf))
    buildConf.dep_list_extract_start_dt = timezone.now()
    buildConf.dep_list_extract_end_dt = None
    buildConf.dep_list_extract_status = TaskStatus.RUNNING
    buildConf.save()
    processLogger.info(endMessage(buildConf))


def depListExtract(buildConfList):
    parallelExec(depListExtractTask, buildConfList)


def depListExtractTask(buildConf: BuildConf):
    pathDepListLog = getPathDepListLog(buildConf)
    processLogger = setupProcessLogger(pathDepListLog)
    processLogger.info(startMessage(buildConf))
    try:
        depListExtractInit(processLogger, buildConf)
        buildConf.dep_list.all().delete()

        pathDepListJson = getPathDepListJson(buildConf)

        lines_seen = set()

        build_type = buildConf.type
        filePath = buildConf.getFullFilePath()
        if build_type == BuildType.GRADLE:
            lines_seen = depListExtractForGradle(processLogger, pathDepListLog, filePath)
        elif build_type == BuildType.MAVEN:
            lines_seen = depListExtractForMaven(processLogger, pathDepListLog, filePath)
            dep = parsePomAndExtractRoot(buildConf)
            saveDepFromDepList(dep)

        for line in lines_seen:
            split = line.strip().split(':')
            if build_type == BuildType.GRADLE:
                dep = Dep(
                    buildConf=buildConf,
                    group=split[0],
                    artifact=split[1],
                    version=split[2],  # TODO handle cases like 'osx-x86_64:4.1.101.Final'
                    classifier=split[3]
                )
            elif build_type == BuildType.MAVEN:
                dep = Dep(
                    buildConf=buildConf,
                    group=split[0],
                    artifact=split[1],
                    packaging=split[2],
                    version=split[3],
                    classifier=split[4]
                )
            saveDepFromDepList(dep)

        depListAll = buildConf.dep_list.all()
        if not depListAll:
            processLogger.warn('No dependencies found')
        else:
            updateLatestVersion(depListAll)

            depListForView = depListAll.values('id', 'group', 'artifact', 'packaging', 'version', 'classifier',
                                               'latestVersion')
            updateVersionStatus(depListForView)
            data = []
            if OSS_ACTIVATED:
                getCveListFromDepList(processLogger, depListAll)
                for dep in depListForView:
                    # Get the related cve_list for each dep
                    dep_id = dep['id']
                    dep_instance = buildConf.dep_list.get(id=dep_id)
                    dep['cve_list'] = getCveListJsonForDep(dep_instance)
                    data.append(dep)
            data = list(depListForView)
            json_data = json.dumps(data, indent=2)

            with open(pathDepListJson, 'w') as fileJson:
                fileJson.write(json_data)

        depListExtractSuccess(buildConf)
    except Exception as e:
        processLogger.error(exceptionMessage(e))
        depListExtractFail(buildConf)
    finally:
        processLogger.info(endMessage(buildConf))


def updateVersionStatus(depList):
    for dep in depList:
        latestVersion = dep['latestVersion']
        if latestVersion:
            if latestVersion == dep['version']:
                dep['versionStatus'] = VersionStatus.LATEST
            else:
                dep['versionStatus'] = VersionStatus.HIGHEST


def depListExtractForMaven(processLogger, pathDepListLog, buildConfPath):
    processLogger.info(startMessage() + f" for {buildConfPath} to {pathDepListLog}")
    lines_seen = set()
    command = [MAVEN_EXEC, '-f', buildConfPath, '-s', MAVEN_SETTINGS_PATH, '-Dstyle.color=never', 'dependency:list']
    runCommand(processLogger, getEnclosingDirPath(buildConfPath), command)
    with open(pathDepListLog, 'r') as depListLog:
        lines = depListLog.readlines()
        for line in lines:
            if any(scope in line for scope in ['[INFO]']):
                if any(scope in line for scope in [':jar', ':compile', ':provided', ':runtime', ':test']):
                    parsedLine = line \
                        .replace('[INFO]', '') \
                        .replace(" ", "") \
                        .strip()

                    parsedLine = re.sub('--.*$', '', parsedLine)
                    parsedLine = re.sub('-- module.*', '', parsedLine)
                    if line not in lines_seen:  # not a duplicate
                        lines_seen.add(parsedLine)
    processLogger.info(endMessage() + f" for {buildConfPath} to {pathDepListLog}")
    return lines_seen


def depListExtractForGradle(processLogger, pathDepListLog, repo_path):
    processLogger.info(startMessage() + f" for {repo_path} to {pathDepListLog}")
    lineSeenList = set()
    gradlewPath = repo_path

    while not os.path.exists(os.path.join(gradlewPath, GRADLEW_EXEC)):
        # Move up one directory level
        gradlewPath = getEnclosingDirPath(gradlewPath)

        # TODO Threadify ? is gradle thread safe ?
    command = [gradlewPath + "/" + GRADLEW_EXEC, "-p", getEnclosingDirPath(repo_path), "dependencies"]

    runCommand(processLogger, getEnclosingDirPath(repo_path), command)
    with open(pathDepListLog, 'r') as depListLog:
        lines = depListLog.readlines()
        gradleConf = ''
        previousLine = None
        for line in lines:
            lineStrip = line.strip()
            if lineStrip == '' or previousLine == '':
                gradleConf = ''
            elif gradleConf == '' and previousLine != '' and (
                    lineStrip == "No dependencies" or lineStrip.startswith('+') or lineStrip.startswith('\\')):
                if lineStrip != "No dependencies":
                    gradleConf = previousLine.split(' - ')[0]  # TODO store description ?
            if gradleConf != '' and lineStrip != "No dependencies" and "(n)" not in lineStrip and "(*)" not in lineStrip:
                lineStrip = line.rstrip()
                isConstraint = False
                if "(c)" in lineStrip:
                    isConstraint = True
                    lineStrip = lineStrip \
                        .replace("(c)", "")
                versionOverridden = None

                if '->' in lineStrip:
                    match = re.match(r"([^:]+):([^:]+)(:([^:]+))? -> (.*)", lineStrip)
                    nbGroups = sum(1 for group in match.groups() if group is not None)
                    if nbGroups == 3:
                        # case '+--- com.google.code.findbugs:jsr305 -> 3.0.2'
                        lineStrip = lineStrip.replace(' -> ', ':')
                    else:
                        # case org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.8.0 -> 1.8.20
                        versionOverridden = match.group(3).replace(':', '')
                        lineStrip = match.group(1) + ':' + match.group(2) + ':' + match.group(5)

                lineStrip = replaceLeadingBySpace(lineStrip).strip()
                lineStrip = lineStrip + ':' + gradleConf
                if not lineStrip.__contains__('project :'):
                    lineSeenList.add(lineStrip)

            previousLine = lineStrip
    processLogger.info(f"{endMessage()} for {repo_path} to {pathDepListLog}")
    return lineSeenList


def depListExtractSuccess(buildConf: BuildConf):
    buildConf.dep_list_extract_end_dt = timezone.now()
    buildConf.dep_list_extract_status = TaskStatus.OK
    buildConf.save()
    return buildConf


def depListExtractFail(buildConf: BuildConf):
    buildConf.dep_list_extract_end_dt = timezone.now()
    buildConf.dep_list_extract_status = TaskStatus.KO
    buildConf.save()
    return buildConf


def parsePomAndExtractRoot(buildConf):
    tree = ET.parse(buildConf.getFullFilePath())
    root = tree.getroot()

    # Define the namespace dictionary
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

    # Find elements
    group_id = root.find('m:groupId', ns)
    artifact_id = root.find('m:artifactId', ns)
    version = root.find('m:version', ns)
    # name = root.find('m:name', ns)
    packaging = root.find('m:packaging', ns)

    # Use default values if elements are not found
    group_id = group_id.text if group_id is not None else root.find('m:parent/m:groupId', ns).text
    artifact_id = artifact_id.text
    version = version.text if version is not None else root.find('m:parent/m:version', ns).text
    packaging = packaging.text if packaging is not None else 'jar'

    return Dep(
        buildConf=buildConf,
        group=group_id,
        artifact=artifact_id,
        packaging=packaging,
        version=version
    )


def saveDepFromDepList(dep):
    depInDb = Dep.objects.filter(buildConf=dep.buildConf, group=dep.group, artifact=dep.artifact,
                                 version=dep.version).first()
    if depInDb:
        dep = depInDb
    dep.in_dep_List = True
    dep.save()
