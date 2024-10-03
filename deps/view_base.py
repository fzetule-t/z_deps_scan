from django.shortcuts import render
from django.views.decorators.http import require_GET

from deps.utils_file import downloadFile
from z_deps_scan.settings import LOG_GENERAL_LOG_FILE_PATH


@require_GET
def generalLog(request):
    return downloadFile(LOG_GENERAL_LOG_FILE_PATH)


@require_GET
def credits(request):
    return render(request, "deps/credits.html")
