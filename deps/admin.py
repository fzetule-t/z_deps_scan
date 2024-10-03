from django.contrib import admin
from django.contrib.auth.models import Group

from .models import Repo


@admin.register(Repo)
class RepoAdmin(admin.ModelAdmin):
    list_display = (
        'created_dt', 'updated_dt', 'name', 'uri_type', 'uri', 'identifier_type', 'identifier', 'pull_start_dt',
        'pull_end_dt', 'pull_status', 'path_local')


admin.site.unregister(Group)

# admin.site.unregister(Sites)