import re

from django import forms
from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from deps.models import BuildConfComparison
from deps.models_enu import TaskStatus, UriType, IdentifierType
from deps.templatetags.custom_filters import dtf

register = template.Library()


@register.simple_tag(takes_context=True)
def action_form(context, comparison, action):
    action_url = f'/deps/BuildConfComparison/{comparison.id}/{action}/'
    csrf_token = context.get('csrf_token', '')
    return f'''<form method="post" action="{action_url}" style="display:inline;">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
            <button type="submit">{action.capitalize()}</button>
        </form>
    '''


def linkToMavenRepoArtifact(group, artifact):
    return linkImg(f'https://mvnrepository.com/artifact/{group}/{artifact}', 'mavenRepo.png', 'To Maven Repo')


def linkToMavenRepoVersion(group, artifact, version):
    return linkImg(f'https://mvnrepository.com/artifact/{group}/{artifact}/{version}', 'mavenRepo.png',
                   'To Maven Repo')


@register.simple_tag
def linkToMavenRepoArtifactDep(dep):
    if isinstance(dep, dict):
        group = dep.get('group')
        artifact = dep.get('artifact')
    else:
        group = getattr(dep, 'group', None)
        artifact = getattr(dep, 'artifact', None)
    return linkToMavenRepoArtifact(group, artifact)


@register.simple_tag
def linkToMavenRepoVersionDep(dep):
    if isinstance(dep, dict):
        group = dep.get('group')
        artifact = dep.get('artifact')
        version = dep.get('version')
    else:
        group = getattr(dep, 'group', None)
        artifact = getattr(dep, 'artifact', None)
        version = getattr(dep, 'version', None)
    return linkToMavenRepoVersion(group, artifact, version)


@register.simple_tag
def linkToMavenRepoArtifactSplit(keySplit):
    return linkToMavenRepoArtifact(keySplit[0], keySplit[1])


@register.simple_tag
def linkToMavenRepoVersionSplit(keySplit, version):
    return linkToMavenRepoVersion(keySplit[0], keySplit[1], version)


@register.simple_tag
def linkImg(href, img, title=None):
    return mark_safe(f'<a href="{href}" target="_blank">{getLabel(href, img, title)}</a>')


@register.simple_tag
def getLabel(label, img=None, title=None):
    if not title:
        title = label
    return label if not img else mark_safe(f'<img src="{static("icon/" + img)}" title="{title}" alt="{label}">')


def button_action(httpMethod, entity, action, redirect, label=None, status=None, img=None):
    if label is None:
        label = action
    action_url = f'/deps/{entity.__class__.__name__}/{entity.id}/{action}'
    disabled = 'disabled' if (status == TaskStatus.RUNNING) else ''
    label = getLabel(label, img)
    className = 'button-start' if (TaskStatus.RUNNING == status) else 'button-end'
    return f'''<button class="{className}" onclick="{httpMethod}(this, '{action_url}', '{redirect}')" {disabled}>{label}</button>'''


@register.simple_tag
def button_post(entity, action, redirect, label=None, status=None, img=None):
    return button_action('httpPost', entity, action, redirect, label, status, img)


@register.simple_tag
def button_delete(entity, action, redirect, status=None, label=None):
    return button_action('httpDelete', entity, action, redirect, label, status, 'delete.png')


@register.simple_tag
def button_post_ids(entity, action, idNames, redirect, label=None, img=None):
    if label is None:
        label = action
    label = getLabel(label, 'delete.png')
    return f'''<button class="button-end" onclick="submitSelected('/deps/{entity.__class__.__name__}/{entity.id}/{action}', '{idNames}', '{redirect}')">
    {label}
    </button>'''


# @register.simple_tag
# def buildConfSelectCheckboxPost(buildConf):
#     action_url = f'/deps/BuildConf/{buildConf.id}/{"unselect" if buildConf.selected else "select"}'
#
#     # autocomplete="off" -> This is to prevent Firefox to use its cache to auto-complete checkboxes
#     return f'''<input type="checkbox" name="buildConfIds" autocomplete="off" value="{buildConf.id}"
#                    {"checked" if buildConf.selected else ""}
#                    onclick="httpPost('{action_url}', '/deps/Repo/list')"
#             >
#             {trimBeforeRoot(buildConf.filePath)}
#             </input>
#     '''

def getLink(title, href, target, imgAlt, imgSrc=None):
    label = getLabel(imgAlt, imgSrc)
    return mark_safe(f'''<a class="button-link" title="{title}" href="{href}" target='{target}'>{label}</a>''')


@register.simple_tag
def getLog(entity, action):
    href = f'/deps/{entity.__class__.__name__}/{entity.id}/{action}'
    return getLink('Get log', href, '_blank', 'LOG', 'log_file.png')


@register.simple_tag
def getGeneralLog():
    href = f'/deps/log'
    return getLink('Get general log', href, '_blank', 'LOG', 'log_file.png')


@register.simple_tag
def getJson(entity, action):
    href = f'/deps/{entity.__class__.__name__}/{entity.id}/{action}'
    return getLink('Get json', href, '_blank', 'JSON', 'json_file.png')


@register.simple_tag
def goToView(entity, action):
    href = f'/deps/{entity.__class__.__name__}/{entity.id}/{action}'
    return getLink('Go to view', href, '', 'VIEW', 'view.png')


@register.simple_tag
def goToGit(repo):
    if repo.uri_type == UriType.GIT_URL and repo.identifier:
        if repo.identifier_type == IdentifierType.BRANCH or repo.identifier_type == IdentifierType.TAG:
            # Remove '.git' from repo.uri using re.sub()
            url = re.sub(r'\.git$', '', repo.uri)
            url = url + '/tree/' + repo.identifier
            return getLink('Go to git', url, '_blank', 'GIT', 'gitHub.png')
    return ''


@register.simple_tag
def goToGitForBuildConf(buildConf):
    repo = buildConf.repo
    if repo.uri_type == UriType.GIT_URL and repo.identifier:
        if repo.identifier_type == IdentifierType.BRANCH or repo.identifier_type == IdentifierType.TAG:
            # Remove '.git' from repo.uri using re.sub()
            url = re.sub(r'\.git$', '', repo.uri)
            url = url + '/blob/' + repo.identifier + buildConf.filePath
            return getLink('Go to git', url, '_blank', 'GIT', 'gitHub.png')
    return ''


@register.simple_tag
def goToRepoBuildConf(repo):
    url = f'/deps/BuildConf/list?repo={repo.id}'
    return getLink('Go to build confs', url, '', 'BuildConfs', 'buildConf.png')


@register.simple_tag
def goToRepo(repo):
    url = f'/deps/Repo/list?repo={repo.id}'
    return getLink('Go to repo', url, '', repo.id)


@register.simple_tag
def goToBuildConf(buildConf):
    url = f'/deps/BuildConf/list?buildConf={buildConf.id}'
    return getLink('Go to build conf', url, '', buildConf.id)


class IdentifierTypeForm(forms.Form):
    identifier_type = forms.ChoiceField(choices=[(choice.value, choice.label) for choice in IdentifierType], label='',
                                        widget=forms.Select(attrs={'autocomplete': 'off'}))


@register.simple_tag
def identifierTypeForm(repo):
    form = IdentifierTypeForm(initial={'identifier_type': repo.identifier_type})
    attrs = {'autocomplete': 'off',
             'onchange': f'httpPost(this, "/deps/Repo/{repo.id}/identifierType/select/" + this.value, "/deps/Repo/list")'
             }
    if repo.pull_status == TaskStatus.RUNNING:
        attrs['disabled'] = 'disabled'
    form.fields['identifier_type'].widget.attrs.update(attrs)
    if not repo.identifier_type:
        existing_choices = form.fields['identifier_type'].choices
        new_choice = ('', '')
        existing_choices.append(new_choice)
        form.fields['identifier_type'].choices = existing_choices
    return form.as_p()


class IdentifierForm(forms.Form):
    identifier = forms.ChoiceField(choices=[], label='', widget=forms.Select())


@register.simple_tag
def identifierForm(repo):
    form = IdentifierForm(initial={'identifier': repo.identifier})
    #  urllib.parse.quote(choice.uri, safe='')
    form.fields['identifier'].choices = [(choice.uri, choice.uri) for choice in
                                         repo.identifier_list.filter(type=repo.identifier_type)]
    if not repo.identifier:
        existing_choices = form.fields['identifier'].choices
        new_choice = ('', '')
        existing_choices.append(new_choice)
        form.fields['identifier'].choices = existing_choices

    attrs = {'autocomplete': 'off',
             'onchange': f'httpPost(this, "/deps/Repo/{repo.id}/identifier/select/" + this.value, "/deps/Repo/list")'
             }
    if repo.pull_status == TaskStatus.RUNNING or repo.identifier_type is None:
        attrs['disabled'] = 'disabled'
    form.fields['identifier'].widget.attrs.update(attrs)
    return form.__str__()


@register.simple_tag
def comparisonToHtml(comparison: BuildConfComparison):
    html = ''
    mapPerRepo = {}
    for buildConf in comparison.build_conf_list.all():
        if buildConf.repo in mapPerRepo:
            mapPerRepo[buildConf.repo].append(buildConf)
        else:
            mapPerRepo[buildConf.repo] = [buildConf]

    for repo, buildConfListPerRepo in mapPerRepo.items():
        html += f'<br>Repo {goToRepo(repo)}: {repo.name} ({repo.identifier_type}/{repo.identifier}) :'
        for buildConf in buildConfListPerRepo:
            html += f'<br> - BuildConf {goToBuildConf(buildConf)}: {buildConf.filePath} (Dep List {buildConf.dep_list_extract_status} {dtf(buildConf.dep_list_extract_end_dt)})'
    return mark_safe(html)


@register.simple_tag
def goToAdmin():
    url = f'/admin'
    return getLink('Go to admin', url, '', 'Admin')


@register.simple_tag
def goToCredits():
    url = f'/deps/Credits'
    return getLink('Go to credits', url, '', 'Credits')
