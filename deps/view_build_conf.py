import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST, require_GET, require_http_methods

from deps import back_dep_list, back_dep_tree
from deps.models import BuildConf, BuildConfComparison
from deps.models_enu import TaskStatus, BuildType, IdentifierType
from deps.utils_file import downloadFile, downloadJson, getPathDepTreeLog, getPathDepsTreeJson, \
    getPathDepsTreeViewJson, getPathDepListLog, getPathDepListJson


@require_GET
def build_conf_list(request):
    repoFilter = request.GET.get('repo', None)
    buildConfFilter = request.GET.get('buildConf', None)
    buildConfList = BuildConf.objects.all()
    context = {'buildConfList': buildConfList,
               'TaskStatus': TaskStatus,
               'BuildType': BuildType,
               'IdentifierType': IdentifierType,
               'repoFilter': repoFilter,
               'buildConfFilter': buildConfFilter
               }

    return render(request, "deps/build_conf_list.html", context)


@require_POST
def deleteList(request):
    buildConfList = getSelectedBuildConfList(request)
    for buildConf in buildConfList:
        buildConf.delete()
    return HttpResponse(status=200)


@require_http_methods(["DELETE"])
def delete(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    buildConf.delete()
    return HttpResponse(status=200)


@require_POST
def depListExtract(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    back_dep_list.depListExtract([buildConf])
    return HttpResponse(status=200)


@require_POST
def depListExtractForList(request):
    buildConfList = getSelectedBuildConfList(request)
    back_dep_list.depListExtract(buildConfList)
    return HttpResponse(status=200)


@require_GET
def depListLog(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    pathDepListLog = getPathDepListLog(buildConf)
    return downloadFile(pathDepListLog)


@require_GET
def depListJson(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    pathDepListJson = getPathDepListJson(buildConf)
    return downloadJson(pathDepListJson)


@require_GET
def depListView(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    pathDepListJson = getPathDepListJson(buildConf)

    try:
        with open(pathDepListJson, 'r') as json_file:
            depList = json.load(json_file)  # Parse JSON data

        context = {
            'repo': buildConf.repo
            , 'buildConf': buildConf
            , 'depList': depList
            # , 'depList': buildConf.dep_list.all()
        }
        return render(request, "deps/build_conf_dep_list.html", context)
    except FileNotFoundError:
        return render(request, 'error.html', {'error_message': 'JSON file not found'})

    except json.JSONDecodeError:
        return render(request, 'error.html', {'error_message': 'Error decoding JSON data'})


@require_POST
def initCompareDeps(request):
    buildConfList = getSelectedBuildConfList(request)

    comparison = BuildConfComparison()
    comparison.save()
    comparison.build_conf_list.set(buildConfList)
    comparison.save()
    return HttpResponse(status=200)


def getSelectedBuildConfList(request):
    buildConfIds = request.POST.getlist('buildConfIds')
    buildConfList = BuildConf.objects.filter(id__in=buildConfIds)
    return buildConfList


@require_POST
def depTreeExtract(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)

    buildConfList = [buildConf]
    back_dep_tree.depTreeExtract(buildConfList)
    return HttpResponse(status=200)


@require_POST
def depTreeExtractForList(request):
    buildConfList = getSelectedBuildConfList(request)

    back_dep_tree.depTreeExtract(buildConfList)
    return HttpResponse(status=200)


@require_GET
def depTreeLog(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    pathDepsTreeLog = getPathDepTreeLog(buildConf)
    return downloadFile(pathDepsTreeLog)


@require_GET
def depTreeJson(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)
    pathDepsTreeJson = getPathDepsTreeJson(buildConf)
    return downloadJson(pathDepsTreeJson)


@require_GET
def depTreeView(request, id):
    buildConf = get_object_or_404(BuildConf, pk=id)

    try:
        with open(getPathDepsTreeViewJson(buildConf), 'r') as json_file:
            buildConfDepTree = json.dumps(json.load(json_file))  # Parse JSON data

        context = {
            'repo': buildConf.repo
            , 'buildConf': buildConf
            , 'buildConfDepTree': buildConfDepTree
        }
        return render(request, "deps/build_conf_dep_tree.html", context)

    except FileNotFoundError:
        return render(request, 'error.html', {'error_message': 'JSON file not found'})

    except json.JSONDecodeError:
        return render(request, 'error.html', {'error_message': 'Error decoding JSON data'})
