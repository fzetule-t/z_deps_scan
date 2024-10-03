import re

from django import template
from django.conf import settings
from django.utils.dateformat import format as date_format

from deps.models import Repo
from deps.models_enu import TaskStatus, UriType

register = template.Library()


@register.filter
def dtf(value):
    if value is None:
        return ''
    else:
        return date_format(value, settings.DATETIME_FORMAT)


@register.filter
def split(value, delimiter):
    """Splits the string by the given delimiter."""
    return value.split(delimiter)


@register.filter
def status(status):
    if not status:
        status = TaskStatus.NONE_DONE
    cssClass = status.lower().replace(' ', '_')
    return f'''<span class="status_{cssClass}">{status}</span>'''


@register.filter
def uri(repo: Repo):
    if repo.uri_type == UriType.GIT_URL:
        pattern = r'http://|https://'
        # Use re.sub to replace only the first occurrence
        url = re.sub(pattern, '', repo.uri, count=1)
        return f'''<a target='_blank' href="{repo.uri}">{url}</a>'''
    else:
        return repo.uri
