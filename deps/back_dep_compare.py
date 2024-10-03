import json
import os
from typing import List

from django.utils import timezone

from deps.models import BuildConfComparison, BuildConf
from deps.models_enu import BuildType, VersionStatus, TaskStatus
from deps.utils_file import getBuildConfComparisonDataDir, getComparisonResultFilePath
from deps.utils_log import log, exceptionMessage
from z_deps_scan.settings import KEY_TITLE


def depListCompare(buildConfComparison: BuildConfComparison):
    log.info('depListCompare')
    try:
        buildConfList = buildConfComparison.build_conf_list.all()
        result = constructTable(buildConfList)
        data_dir = getBuildConfComparisonDataDir(buildConfComparison.id)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        path = getComparisonResultFilePath(buildConfComparison.id)
        with open(path, 'w') as json_file:
            json.dump(result, json_file)
        comparisonSuccess(buildConfComparison)
    except Exception as e:
        log.error(exceptionMessage(e))
        comparisonFail(buildConfComparison)


def hasGradleAndMavenConf(buildConfList):
    hasGradle = False
    hasMaven = False
    for buildConf in buildConfList:
        if buildConf.type == BuildType.MAVEN:
            hasGradle = True
        elif buildConf.type == BuildType.GRADLE:
            hasMaven = True
    return hasGradle and hasMaven


def constructTable(buildConfList: List[BuildConf]):
    col_pos = -1
    result = {KEY_TITLE: []}

    hasGradleAndMaven = hasGradleAndMavenConf(buildConfList)

    for buildConf in buildConfList:
        col_pos += 1
        repo = buildConf.repo
        result[KEY_TITLE] += [
            f"{repo.name} ({repo.identifier_type}/{repo.identifier}) {buildConf.filePath}"]
        for dep in buildConf.dep_list.all():
            group = dep.group
            artifact = dep.artifact
            # packaging = dep.packaging
            version = dep.version
            classifier = dep.classifier
            if classifier and hasGradleAndMaven:
                if buildConf.type == BuildType.MAVEN:
                    classifier = classifier + '/' + getGradleScopeEquivalent(classifier)
                elif buildConf.type == BuildType.GRADLE:
                    classifier = getMavenScopeEquivalent(classifier) + '/' + classifier
            else:
                classifier = dep.classifier
            key = f"{group}:{artifact}:{classifier}"  # :{packaging}

            versionEnhanced = {"version": version, "latestVersion": dep.latestVersion}

            row = result.get(key, [])
            if row.__len__() == 0:
                result[key] = row

            if col_pos == 0:
                if result[key].__len__() == 0:
                    result[key] = [[versionEnhanced]]
                else:
                    result[key][0] += [versionEnhanced]

            # Handle case when there was no corresponding version for some projects
            elif col_pos > 0:
                nbCol = row.__len__()
                to_add = col_pos - nbCol
                i = 0
                while i < to_add:
                    result[key] += [[]]
                    i += 1

                if result[key].__len__() < col_pos + 1:
                    result[key] += [[versionEnhanced]]
                else:
                    result[key][col_pos] += [versionEnhanced]

    # Completing row
    for key in result:
        while result[key].__len__() < col_pos + 1:
            result[key] += [[]]

    for key in list(result.keys())[1:]:
        listVersion = result[key]
        highestVersion = getHighestVersionFromListOfList(listVersion)
        updateVersionStatus(listVersion, highestVersion)

    return result


# Define a key function that handles non-numeric parts
def version_key(versionEnhanced):
    parts = versionEnhanced['version'].split('.')
    numeric_parts = [int(part) if part.isdigit() else 0 for part in parts]
    return tuple(numeric_parts)


def getHighestVersionFromListOfList(versionListOfList: List[List[str]]):
    # Flatten the list of lists into a single list
    flat_list = [item for sublist in versionListOfList for item in sublist]
    sorted_versions = sorted(flat_list, key=version_key, reverse=True)
    latest_version = sorted_versions[0] if sorted_versions else None
    return latest_version['version']


def getLatestVersionFromList(versionList: List[str]):
    # Flatten the list of lists into a single list
    sorted_versions = sorted(versionList, key=version_key, reverse=True)
    latest_version = sorted_versions[0] if sorted_versions else None
    return latest_version['version']


def updateVersionStatus(versionListOfList: List[List[str]], highestVersion: str):
    for item in versionListOfList:
        for versionEnhanced in item:
            version = versionEnhanced['version']
            if version == highestVersion:
                versionEnhanced['versionStatus'] = VersionStatus.HIGHEST
                latestVersion = versionEnhanced['latestVersion']
                if latestVersion:
                    if version == latestVersion:
                        versionEnhanced['versionStatus'] = VersionStatus.LATEST
            else:
                versionEnhanced['versionStatus'] = VersionStatus.LOWEST


def comparisonSuccess(comparison: BuildConfComparison):
    comparison.end_dt = timezone.now()
    comparison.status = TaskStatus.OK
    comparison.save()
    return comparison


def comparisonFail(comparison: BuildConfComparison):
    comparison.end_dt = timezone.now()
    comparison.status = TaskStatus.KO
    comparison.save()
    return comparison


def getMavenScopeEquivalent(gradleConf):
    gradle_to_maven_scope = {
        'compileClasspath': 'compile',
        'runtimeClasspath': 'runtime',
        'compileOnly': 'provided',
        'runtimeOnly': 'runtime',
        'testCompileClasspath': 'test',
        'testRuntimeClasspath': 'test',
        'implementation': 'compile',
        'api': 'compile',  # with transitivity in mind
        'annotationProcessor': 'provided',  # typically configured via Maven Compiler Plugin
        'compileOnlyApi': 'provided',  # conceptually similar to provided but used in a compile-only context
    }

    return gradle_to_maven_scope.get(gradleConf, 'unknown')


def getGradleScopeEquivalent(mavenScope):
    maven_to_gradle_scope = {
        'compile': 'compileClasspath',
        # 'compile': 'api',  # with transitivity in mind
        # 'compile': 'implementation',
        'runtimeClasspath': 'runtimeClasspath',
        'provided': 'compileOnly',
        # 'provided': 'annotationProcessor',  # typically configured via Maven Compiler Plugin
        # 'provided': 'compileOnlyApi',  # conceptually similar to provided but used in a compile-only context
        'runtime': 'runtimeOnly',
        'test': 'testCompileClasspath',
        # 'test': 'testRuntimeClasspath'
    }

    return maven_to_gradle_scope.get(mavenScope, 'unknown')
