from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from deps.models_enu import UriType, IdentifierType, TaskStatus, BuildType
from deps.utils_file import deleteDir, getBuildConfDataDir, getBuildConfComparisonDataDir


class Repo(models.Model):
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100)
    uri_type = models.CharField(
        max_length=50,
        choices=UriType.choices,
        default=UriType.GIT_URL
    )
    uri = models.CharField(max_length=200)
    path_local = models.CharField(max_length=500, null=True, blank=True, editable=False)
    identifier_type = models.CharField(
        max_length=50,
        choices=IdentifierType.choices,
        default=None,
        null=True,
        editable=False
    )
    identifier = models.CharField(max_length=200, null=True, editable=False)
    user = models.CharField(max_length=200, null=True, blank=True, default='ENV_GIT_USER')
    pwd = models.CharField(max_length=200, null=True, blank=True, default='ENV_GIT_PWD')
    pull_start_dt = models.DateTimeField(null=True, blank=True, editable=False)
    pull_end_dt = models.DateTimeField(null=True, blank=True, editable=False)
    pull_status = models.CharField(
        max_length=50,
        choices=TaskStatus.choices,
        default=TaskStatus.NONE_DONE,
        editable=False
    )

    def getCwd(self):
        if self.uri_type == UriType.GIT_URL:
            return self.path_local
        elif self.uri_type == UriType.PATH:
            return self.uri

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name + ', ' + self.uri_type + ': ' + self.uri

    def reset(self):
        self.build_conf_list.all().delete()
        self.pull_start_dt = None
        self.pull_end_dt = None
        self.pull_status = TaskStatus.NONE_DONE
        self.save()

    def delete(self, *args, **kwargs):
        deleteDir(self.path_local)
        super().delete(*args, **kwargs)


class Identifier(models.Model):
    type = models.CharField(
        max_length=50,
        choices=IdentifierType.choices,
        default=None
    )
    uri = models.CharField(max_length=200)
    repo = models.ForeignKey(Repo, related_name='identifier_list', on_delete=models.CASCADE, null=True)


class BuildConf(models.Model):
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    repo = models.ForeignKey(Repo, related_name='build_conf_list', on_delete=models.CASCADE, null=True)
    filePath = models.CharField(max_length=400)
    type = models.CharField(
        max_length=10,
        choices=BuildType.choices,
        default=BuildType.UNKNOWN,
    )
    dep_list_extract_start_dt = models.DateTimeField(null=True, blank=True, editable=False)
    dep_list_extract_end_dt = models.DateTimeField(null=True, blank=True, editable=False)
    dep_list_extract_status = models.CharField(
        max_length=50,
        choices=TaskStatus.choices,
        default=TaskStatus.NONE_DONE,
        editable=False
    )

    dep_tree_extract_start_dt = models.DateTimeField(null=True, blank=True, editable=False)
    dep_tree_extract_end_dt = models.DateTimeField(null=True, blank=True, editable=False)
    dep_tree_extract_status = models.CharField(
        max_length=50,
        choices=TaskStatus.choices,
        default=TaskStatus.NONE_DONE,
        editable=False
    )
    depTreeRoot = models.ForeignKey('Dep', related_name='depTreeRoot', null=True, on_delete=models.SET_NULL,
                                    editable=False)

    def getFullFilePath(self):
        return self.repo.getCwd() + self.filePath

    def delete(self, *args, **kwargs):
        deleteDir(getBuildConfDataDir(self))
        super().delete(*args, **kwargs)


class Dep(models.Model):
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    group = models.CharField(max_length=100)
    artifact = models.CharField(max_length=100)
    packaging = models.CharField(max_length=100)
    version = models.CharField(max_length=100)
    classifier = models.CharField(max_length=100, null=True)
    is_removable = models.BooleanField(default=False)
    buildConf = models.ForeignKey(BuildConf, related_name='dep_list', on_delete=models.CASCADE, null=True)
    in_dep_list = models.BooleanField(default=False)
    in_dep_tree = models.BooleanField(default=False)
    latestVersion = models.CharField(max_length=100, null=True)
    isConstraint = models.BooleanField(default=False)
    versionOverridden = models.CharField(max_length=100, null=True, default=None, blank=True)
    is_resolvable = models.BooleanField(default=True)

    def deleteDepList(self):
        self.in_dep_List = False
        if self.in_dep_tree:
            self.save()
        else:
            self.delete()

    def deleteDepTree(self):
        # LinkDep.objects.all().delete()
        # Dep.objects.all().delete()
        for link in self.a_links.all():
            link.delete()
        if self.in_dep_list:
            self.in_dep_tree = False
            self.save()
        else:
            self.delete()

    def __key3__(self):
        return self.group + '_' + self.artifact + '_' + self.version

    def __key__(self):
        return self.group + '_' + self.artifact + '_' + self.version + '_' + str(
            self.isConstraint)  # due to circular references case with bom


# |    |    +--- com.fasterxml.jackson.core:jackson-databind:2.12.7 -> 2.12.7.1
# |    |    |    +--- com.fasterxml.jackson.core:jackson-annotations:2.12.7
# |    |    |    |    \--- com.fasterxml.jackson:jackson-bom:2.12.7
# |    |    |    |         +--- com.fasterxml.jackson.core:jackson-annotations:2.12.7 (c)
# |    |    |    |         +--- com.fasterxml.jackson.core:jackson-databind:2.12.7 -> 2.12.7.1 (c)
# |    |    |    |         +--- com.fasterxml.jackson.module:jackson-module-kotlin:2.12.7 (c)
# |    |    |    |         \--- com.fasterxml.jackson.core:jackson-core:2.12.7 (c)


class LinkDep(models.Model):
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    a = models.ForeignKey(Dep, related_name='a_links', on_delete=models.CASCADE)
    b = models.ForeignKey(Dep, related_name='b_links', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.a.id} -> {self.b.id}"

    def delete(self, *args, **kwargs):
        try:
            self.b.deleteDepTree()
        except ObjectDoesNotExist:
            pass

        # Call the superclass delete method to delete the instance
        super().delete(args, kwargs)


class Cve(models.Model):
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=200, primary_key=True)
    title = models.CharField(max_length=200)
    cvssScore = models.FloatField()
    reference = models.CharField(max_length=400)
    repo_dep_list = models.ManyToManyField(Dep, related_name='cve_list')


@receiver(m2m_changed, sender=Cve)
def m2m_change_order(sender, instance, created, **kwargs):
    if not instance.repo_dep_list.exist():
        instance.delete()


class BuildConfComparison(models.Model):
    created_dt = models.DateTimeField(auto_now_add=True)
    updated_dt = models.DateTimeField(auto_now=True)
    start_dt = models.DateTimeField(null=True, editable=False)
    end_dt = models.DateTimeField(null=True, editable=False)
    status = models.CharField(
        max_length=50,
        choices=TaskStatus.choices,
        default=TaskStatus.NONE_DONE,
        editable=False
    )
    build_conf_list = models.ManyToManyField(BuildConf, related_name='comparisons')

    def __str__(self):
        buildConfFiles = ", ".join([build_conf.getFullFilePath() for build_conf in self.build_conf_list.all()])
        return f"Comparison with BuildConfs: {buildConfFiles}, in status: {self.status}"

    def delete(self, *args, **kwargs):
        deleteDir(getBuildConfComparisonDataDir(self.id))
        super().delete(*args, **kwargs)
