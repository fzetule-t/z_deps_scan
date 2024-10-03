import json
import threading

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .back_dep_compare import depListCompare
from .models import *
from .models_enu import VersionStatus
from .utils_file import getComparisonResultFilePath, downloadJson


@require_GET
def comparison_list(request):
    context = {"buildConfComparisonList": BuildConfComparison.objects.all(), 'TaskStatus': TaskStatus}
    return render(request, "deps/build_conf_comparison_list.html", context)


@require_GET
def detail(request, id):
    comparison = get_object_or_404(Repo, pk=id)
    return render(request, "deps/comparison_detail.html", {"comparison": comparison})


@require_POST
def start(request, id):
    comparison = get_object_or_404(BuildConfComparison, pk=id)
    comparison.status = TaskStatus.RUNNING
    comparison.start_dt = timezone.now()
    comparison.end_dt = None
    comparison.save()

    def wrapper():
        depListCompare(comparison)

    thread = threading.Thread(target=wrapper)
    thread.start()
    return HttpResponse(status=200)


@require_POST
def stop(request, id):
    comparison = get_object_or_404(BuildConfComparison, pk=id)
    comparison.status = TaskStatus.KO
    comparison.end_dt = timezone.now()
    comparison.save()
    return HttpResponse(status=200)


@require_http_methods(["DELETE"])
def delete(request, id):
    comparison = get_object_or_404(BuildConfComparison, pk=id)
    comparison.delete()
    return HttpResponse(status=200)


@require_GET
def resultJson(request, id):
    comparison = get_object_or_404(BuildConfComparison, pk=id)
    return downloadJson(getComparisonResultFilePath(comparison.id))


@require_GET
def resultView(request, id):
    comparison = get_object_or_404(BuildConfComparison, pk=id)

    try:
        with open(getComparisonResultFilePath(comparison.id), 'r') as json_file:
            depListComparisonResult = json.load(json_file)  # Parse JSON data

        context = {
            'comparison': comparison
            , 'TaskStatus': TaskStatus
            , 'VersionStatus': VersionStatus
            , 'depListComparisonResult': depListComparisonResult
        }
        return render(request, "deps/build_conf_comparison_result.html", context)

    except FileNotFoundError:
        return render(request, 'error.html', {'error_message': 'JSON file not found'})

    except json.JSONDecodeError:
        return render(request, 'error.html', {'error_message': 'Error decoding JSON data'})
