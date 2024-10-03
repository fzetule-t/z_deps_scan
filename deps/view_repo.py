from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from . import back_repo
from .back_git import getIdentifierType
from .back_repo import switch, gitRepoDirExists, pullTask, getIdentifierList
from .models import *
from .utils_file import downloadFile, getPathPullLog
from .utils_log import log, startMessage


@require_GET
def repoList(request):
    log.info(startMessage())

    repoFilter = request.GET.get('repo', None)
    repoList = Repo.objects.all()

    # TODO find better solution
    for repo in repoList:
        if repo.uri_type == UriType.PATH and repo.identifier_type == None:
            identifier_type, identifier = getIdentifierType(repo)
            repo.identifier_type = identifier_type
            repo.identifier = identifier
            repo.save()
            getIdentifierList(repo)
            back_repo.detectBuildConf(repo)

    context = {'repoList': repoList,
               'TaskStatus': TaskStatus,
               'BuildType': BuildType,
               'IdentifierType': IdentifierType,
               'repoFilter': repoFilter
               }

    return render(request, "deps/repo_list.html", context)


@require_POST
def pull(request, id):
    repo = get_object_or_404(Repo, pk=id)
    back_repo.pull([repo])

    return HttpResponse(status=200)


@require_GET
def pullLog(request, id):
    repo = get_object_or_404(Repo, pk=id)
    return downloadFile(getPathPullLog(repo.id))


@require_POST
def pullList(request):
    repoList = getSelectedRepoList(request)
    back_repo.pull(repoList)

    return HttpResponse(status=200)


@require_POST
def detectBuildConf(request, id):
    repo = get_object_or_404(Repo, pk=id)
    back_repo.detectBuildConf(repo)
    return HttpResponse(status=200)


@require_POST
def detectBuildConfList(request):
    repoList = getSelectedRepoList(request)
    for repo in repoList:
        back_repo.detectBuildConf(repo)
    return HttpResponse(status=200)


@require_http_methods(["DELETE"])
def delete(request, id):
    repo = get_object_or_404(Repo, pk=id)
    # TODO kill checkout in progress
    repo.delete()
    return HttpResponse(status=200)


@require_POST
def deleteList(request):
    repoList = getSelectedRepoList(request)
    for repo in repoList:
        repo.delete()
    return HttpResponse(status=200)


@require_GET
def detail(request, id):
    repo = get_object_or_404(Repo, pk=id)
    return render(request, "deps/repo_detail.html", {"repo": repo})


@require_POST
def identifierTypeSelect(request, id, selected):
    repo = get_object_or_404(Repo, pk=id)
    repo.identifier_type = selected
    repo.identifier = None
    repo.save()
    repo.reset()
    if not gitRepoDirExists(repo) and repo.uri_type == UriType.GIT_URL:
        pullTask(repo)
    getIdentifierList(repo)
    return HttpResponse(status=200)


@require_POST
def identifierSelect(request, id, selected):
    repo = get_object_or_404(Repo, pk=id)
    repo.identifier = selected
    repo.save()
    repo.reset()
    switch(repo)
    return HttpResponse(status=200)


def getSelectedRepoList(request):
    repoIds = request.POST.getlist('repoIds')
    repoList = Repo.objects.filter(id__in=repoIds)
    return repoList
