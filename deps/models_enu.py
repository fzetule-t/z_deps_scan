from django.db import models


class UriType(models.TextChoices):
    GIT_URL = 'Git url'
    PATH = 'Local path'


class VersionStatus(models.TextChoices):
    HIGHEST = 'highest'
    LOWEST = 'lowest'
    LATEST = 'latest'


class TaskStatus(models.TextChoices):
    NONE_DONE = ''
    RUNNING = 'Running'
    OK = 'OK'
    KO = 'KO'


class BuildType(models.TextChoices):
    MAVEN = 'maven'
    GRADLE = 'gradle'
    UNKNOWN = 'unknown'


class IdentifierType(models.TextChoices):
    BRANCH = 'branch'
    TAG = 'tag'
    # COMMIT = 'commit'
