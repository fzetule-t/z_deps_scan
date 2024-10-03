# middleware.py
import re
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import redirect

from z_deps_scan import settings


class CustomErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        code = response.status_code
        if code >= 400:
            return JsonResponse({'message': response.reason_phrase}, status=code)
        else:
            return response


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = settings.LOGIN_URL
        self.allowed_urls = [
            re.compile(r'^admin/login/'),
            # re.compile(r'^admin/password_reset/'),
            re.compile(r'^admin/logout/'),
            re.compile(r'^accounts/login/'),
            re.compile(r'^accounts/logout/')
        ]

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info.lstrip('/')
            if not any(url.match(path) for url in self.allowed_urls):
                login_url_with_next = f"{self.login_url}?{urlencode({'next': request.path})}"
                return redirect(login_url_with_next)
        response = self.get_response(request)
        return response
