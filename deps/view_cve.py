from django.shortcuts import render
from django.views.decorators.http import require_GET

from deps.models import Cve, BuildConf
from deps.utils_log import log, startMessage


@require_GET
def cveList(request):
    log.info(startMessage())
    repoFilter = request.GET.get('repo', None)
    buildConfFilter = request.GET.get('buildConf', None)
    buildConfList = BuildConf.objects.all()
    depList = []
    for buildConf in buildConfList:
        for dep in buildConf.dep_list.all():
            if dep.cve_list:
                depList.append(dep)

    context = {'depList': depList,
               'repoFilter': repoFilter,  # TODO
               'buildConfFilter': buildConfFilter  # TODO
               }

    return render(request, "deps/cve_list.html", context)
