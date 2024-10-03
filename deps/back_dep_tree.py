import json
import os
import re
import sys

from django.utils import timezone

from deps.back_dep_cve import getCveListForDepTree, getCveListJsonForDep
from deps.models import LinkDep, Dep, BuildConf
from deps.models_enu import TaskStatus, BuildType
from deps.utils_file import getPathDepTreeLog, getPathDepsTreeJson, getPathDepsTreeViewJson, getEnclosingDirPath
from deps.utils_log import setupProcessLogger, startMessage, endMessage, exceptionMessage
from deps.utils_process import runCommand, parallelExec
from deps.utils_str import countLeadingBlanks
from z_deps_scan.settings import MAVEN_EXEC, MAVEN_SETTINGS_PATH, GRADLEW_EXEC

translation_table = str.maketrans({
    '+': ' ',
    # '-': ' ',
    '\\': ' ',
    '|': ' '
})


def depTreeExtractInit(processLogger, buildConf):
    buildConf.dep_tree_extract_start_dt = timezone.now()
    buildConf.dep_tree_extract_end_dt = None
    buildConf.dep_tree_extract_status = TaskStatus.RUNNING
    buildConf.save()


def depTreeExtract(buildConfList):
    parallelExec(depTreeExtractTask, buildConfList)


def depTreeExtractTask(buildConf: BuildConf):
    pathDepsTreeLog = getPathDepTreeLog(buildConf)
    processLogger = setupProcessLogger(pathDepsTreeLog)
    processLogger.info(startMessage(buildConf))
    try:
        depTreeExtractInit(processLogger, buildConf)
        pathDepsTreeJson = getPathDepsTreeJson(buildConf)
        pathDepsTreeViewJson = getPathDepsTreeViewJson(buildConf)

        buildConfPath = buildConf.getFullFilePath()
        buildType = buildConf.type

        if buildConf.depTreeRoot is not None:
            buildConf.depTreeRoot.deleteDepTree()
        depTreeRoot = None

        if buildType == BuildType.GRADLE:
            depTreeRoot = depTreeExtractForGradle(processLogger, buildConf, pathDepsTreeLog, buildConfPath)
        elif buildType == BuildType.MAVEN:
            depTreeRoot = depTreeExtractForMaven(processLogger, buildConf, pathDepsTreeLog, buildConfPath)

        buildConf.depTreeRoot = depTreeRoot
        buildConf.save()
        sys.setrecursionlimit(2000)
        to_json = repoTreeToJson(depTreeRoot)
        with open(pathDepsTreeJson, 'w') as fileParsed:
            fileParsed.write(json.dumps(to_json, indent=2))
            processLogger.info(endMessage(buildConf) + f" to {pathDepsTreeJson}")

        mapDep = {}
        view_json = repoTreeToViewJson(mapDep, depTreeRoot, 0)
        with open(pathDepsTreeViewJson, 'w') as fileParsed:
            fileParsed.write(json.dumps(view_json, indent=2))
            processLogger.info(endMessage(buildConf) + f" to {pathDepsTreeViewJson}")

        depTreeExtractSuccess(processLogger, buildConf)
    except Exception as e:
        processLogger.error(exceptionMessage(e))
        depTreeExtractFail(processLogger, buildConf)


def depTreeExtractSuccess(processLogger, buildConf: BuildConf):
    processLogger.info(startMessage(buildConf))
    buildConf.dep_tree_extract_end_dt = timezone.now()
    buildConf.dep_tree_extract_status = TaskStatus.OK
    buildConf.save()
    processLogger.info(endMessage(buildConf))
    return buildConf


def depTreeExtractFail(processLogger, buildConf: BuildConf):
    processLogger.info(startMessage(buildConf))
    buildConf.dep_tree_extract_end_dt = timezone.now()
    buildConf.dep_tree_extract_status = TaskStatus.KO
    buildConf.save()
    processLogger.info(endMessage(buildConf))
    return buildConf


def depTreeExtractForMaven(processLogger, repo, pathDepsTreeLog, buildConfFilPath):
    command = [MAVEN_EXEC, '-f', buildConfFilPath, '-s', MAVEN_SETTINGS_PATH, '-Dstyle.color=never', 'dependency:tree']
    runCommand(processLogger, getEnclosingDirPath(buildConfFilPath), command)

    return parseMavenTree(processLogger, repo, pathDepsTreeLog)


def parseMavenTree(processLogger, buildConf: BuildConf, depTreeLog):
    mapLevelDep = {}
    mapDep = {}

    with open(depTreeLog, 'r') as fileNonParsed:
        lines = fileNonParsed.readlines()
        start_parsing = False
        end_parsing = False

        for line in lines:
            if "[INFO] --- dependency:" in line:
                start_parsing = True
                continue
            if start_parsing and "[INFO] ---------------" in line:
                end_parsing = True
                continue
            if not start_parsing or end_parsing or line.strip() == '':
                continue

            line = line[7:]  # remove [INFO]
            line = replaceLeadingBySpace(line)
            leadingBlanks = countLeadingBlanks(line)
            level = (leadingBlanks / 3)
            split = line.strip().split(':')
            dep = Dep(
                buildConf=None,
                group=split[0],
                artifact=split[1],
                packaging=split[2],
                version=split[3],
                classifier=split[4] if len(split) >= 5 else None
            )
            keyDep = dep.__key__()
            if keyDep not in mapDep:
                dep = saveDepFromDepTree(dep)
                mapDep[keyDep] = dep
            mapLevelDep[level] = dep
            if level > 0:
                linkDep = LinkDep(
                    a=mapLevelDep[level - 1],
                    b=dep
                )
                linkDep.save()

    depTreeRoot = mapLevelDep[0]
    # Detect useless dependencies
    for key, dep in mapDep.items():
        if isLevel1(dep, depTreeRoot) and hasOtherFatherThanRoot(dep, depTreeRoot):
            dep.is_removable = True  # TODO removable if newest version is overriding it
            dep.save()
    getCveListForDepTree(processLogger, depTreeRoot)
    return depTreeRoot


def isLevel1(dep, depTree):
    for link in dep.b_links.all():
        if link.a == depTree:
            return True
    return False


def hasOtherFatherThanRoot(dep, depTreeRoot):
    for link in dep.b_links.all():
        if link.a != depTreeRoot:
            return True
    return False


def repoTreeToJson(dep: Dep):
    cve_list = getCveListJsonForDep(dep)
    return {
        'group': dep.group,
        'artifact': dep.artifact,
        'packaging': dep.packaging,
        'version': dep.version,
        'classifier': dep.classifier,
        'cve_list': cve_list,
        'children': [
            repoTreeToJson(link.b) for link in dep.a_links.all()
        ]
    }


def repoTreeToViewJson(mapDep, dep: Dep, level):
    title = dep.group + ':' + dep.artifact + ':' + dep.version
    key = dep.__key3__()
    expanded = True
    if key in mapDep:
        expanded = False
        # title += ' (*)'
    else:
        mapDep[key] = dep
    if dep.versionOverridden is not None:
        title += ' (' + dep.versionOverridden + ' overridden)'
    if not dep.is_resolvable:
        title += ' (n)'
    if level == 1:
        if dep.is_removable:
            title += ' (removable)'

    children = [
        repoTreeToViewJson(mapDep, link.b, level + 1) for link in dep.a_links.all()
    ]

    for cve in getCveListJsonForDep(dep):
        cvssScoreStr = str(cve['cvssScore'])
        children.append({
            'title': cve['id'] + ' (' + cvssScoreStr + ')',
            'key': cve['id'],
            'reference': cve['reference'],
            'cvssScore': cvssScoreStr,
            'expanded': expanded,
            'extraClasses': 'cve-node'  # TODO color depending on severity
        })

    return {
        'title': title,
        'key': title,
        'expanded': expanded,
        'children': children,
        'checkbox': True,
    }


def saveDepFromDepTree(dep):
    depInDb = Dep.objects.filter(buildConf=dep.buildConf, group=dep.group, artifact=dep.artifact,
                                 version=dep.version, isConstraint=dep.isConstraint).first()
    if depInDb:
        dep = depInDb

    dep.in_dep_tree = True
    dep.save()
    return dep


def depTreeExtractForGradle(processLogger, buildConf, pathDepsTreeLog, buildConfPath):
    gradlewPath = buildConfPath

    while not os.path.exists(os.path.join(gradlewPath, GRADLEW_EXEC)):
        # Move up one directory level
        gradlewPath = getEnclosingDirPath(gradlewPath)
    # for gradleConf in confList:
    command = [gradlewPath + "/" + GRADLEW_EXEC, "-p", getEnclosingDirPath(buildConfPath), 'dependencies']
    # ,'--configuration', 'dokkaGfmMultiModulePlugin']
    # gradleConf
    runCommand(processLogger, getEnclosingDirPath(buildConfPath), command)

    return parseGradleTree(processLogger, buildConf, pathDepsTreeLog)


def parseGradleTree(processLogger, buildConf: BuildConf, depTreeLog):
    depRoot = Dep(
        buildConf=None,
        group='ROOT',
        artifact='ROOT',
        packaging='ROOT',
        version='ROOT',
        classifier='ROOT'
    )
    depRoot.save()
    level = 0
    mapLevelDep = {level: depRoot}
    mapDep = {}

    with open(depTreeLog, 'r') as fileNonParsed:
        lines = fileNonParsed.readlines()
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
                    level = 1
                    dep = Dep(
                        buildConf=None,
                        group=gradleConf,
                        artifact='',
                        packaging='',
                        version='',
                        classifier=gradleConf
                    )
                    dep.save()
                    linkDep = LinkDep(
                        a=mapLevelDep[level - 1],
                        b=dep
                    )
                    linkDep.save()
                    # mapDep[gradleConf] = dep
                    mapLevelDep[level] = dep
            if gradleConf != '' and lineStrip != "No dependencies":
                # (*) - Indicates repeated occurrences of a transitive dependency subtree.
                # Gradle expands transitive dependency subtrees only once per project; repeat occurrences only display the root of the subtree, followed by this annotation.
                lineStrip = line.rstrip()
                is_resolvable = True
                if "(n)" in lineStrip:
                    is_resolvable = False
                    lineStrip = lineStrip \
                        .replace("(n)", "")
                if "(*)" in lineStrip:
                    lineStrip = lineStrip \
                        .replace("(*)", "")

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

                lineStrip = replaceLeadingBySpace(lineStrip)
                leadingBlanks = countLeadingBlanks(lineStrip)
                lineStrip = lineStrip.strip()
                level = (leadingBlanks / 5) + 1
                lineStrip = lineStrip + ':' + gradleConf
                if lineStrip.__contains__('project :') or not is_resolvable:
                    split = lineStrip.split(':')
                    dep = Dep(
                        buildConf=None,
                        group=split[0].strip(),
                        artifact=split[1].strip(),
                        version='',
                        classifier='',
                        is_resolvable=is_resolvable
                    )
                else:
                    split = lineStrip.split(':')
                    dep = Dep(
                        buildConf=None,
                        group=split[0],
                        artifact=split[1],
                        version=split[2],
                        classifier=split[3],
                        isConstraint=isConstraint,
                        versionOverridden=versionOverridden,
                        is_resolvable=is_resolvable
                    )
                keyDep = dep.__key__()
                if keyDep not in mapDep:
                    dep = saveDepFromDepTree(dep)
                    mapDep[keyDep] = dep
                else:
                    dep = mapDep[keyDep]
                parent = mapLevelDep[level - 1]
                if level > 0 and parent is not None:
                    existingLink = LinkDep.objects.filter(a=parent, b=dep)
                    if not existingLink:
                        linkDep = LinkDep(
                            a=parent,
                            b=dep
                        )
                        linkDep.save()
                # if versionOverridden is None:
                mapLevelDep[level] = dep
                # else:
                #     mapLevelDep[level] = None
            previousLine = lineStrip
    # Detect useless dependencies
    # for key, dep in mapDep.items():
    #     if isLevel1(dep, depTreeRoot) and hasOtherFatherThanRoot(dep, depTreeRoot):
    #         dep.is_removable = True  # TODO removable if newest version is overriding it
    #         dep.save()
    # getCveListForDepTree(processLogger, depTreeRoot)
    # return depTreeRoot
    processLogger.info(endMessage(buildConf))
    return depRoot


def replaceLeadingBySpace(line: str):
    line = line.translate(translation_table)
    P_DEP_TREE_PARSING = r'^([- ]+)([a-z]*)'
    match = re.match(P_DEP_TREE_PARSING, line)
    if match:
        count = len(match.group(1))
        replacement = ' ' * count
        line = replacement + line[count:]
    return line
