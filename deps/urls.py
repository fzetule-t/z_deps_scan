from django.urls import path

from . import view_repo, view_build_conf_comparison, view_build_conf, view_base, view_cve

app_name = "deps"

urlpatterns = [

    path('Credits', view_base.credits),
    path('log', view_base.generalLog),
    #  Repo
    path('Repo/list', view_repo.repoList),
    path('Repo/pull', view_repo.pullList),
    path('Repo/delete', view_repo.deleteList),
    path('Repo/detectBuildConf', view_repo.detectBuildConfList),

    path('Repo/<int:id>', view_repo.detail, ),
    path('Repo/<int:id>/identifierType/select/<str:selected>', view_repo.identifierTypeSelect, ),
    path('Repo/<int:id>/identifier/select/<path:selected>', view_repo.identifierSelect, ),
    path('Repo/<int:id>/pull', view_repo.pull),
    path('Repo/<int:id>/pull/log', view_repo.pullLog),
    path('Repo/<int:id>/delete', view_repo.delete),

    path('Repo/<int:id>/detectBuildConf', view_repo.detectBuildConf),

    # BuildConf
    path('BuildConf/list', view_build_conf.build_conf_list),
    path('BuildConf/delete', view_build_conf.deleteList),
    path('BuildConf/dep_tree/extract', view_build_conf.depTreeExtractForList),
    path('BuildConf/dep_list/extract', view_build_conf.depListExtractForList),

    path('BuildConf/<int:id>/delete', view_build_conf.delete),
    path('BuildConf/<int:id>/dep_list/extract', view_build_conf.depListExtract),
    path('BuildConf/<int:id>/dep_list/log', view_build_conf.depListLog),
    path('BuildConf/<int:id>/dep_list/json', view_build_conf.depListJson),
    path('BuildConf/<int:id>/dep_list/view', view_build_conf.depListView),

    path('BuildConf/<int:id>/dep_tree/extract', view_build_conf.depTreeExtract),
    path('BuildConf/<int:id>/dep_tree/log', view_build_conf.depTreeLog),
    path('BuildConf/<int:id>/dep_tree/json', view_build_conf.depTreeJson),
    path('BuildConf/<int:id>/dep_tree/view', view_build_conf.depTreeView),

    path("BuildConf/dep_list/compare", view_build_conf.initCompareDeps),

    #  Comparison
    path("BuildConfComparison/list/", view_build_conf_comparison.comparison_list),
    path("BuildConfComparison/<int:id>/", view_build_conf_comparison.detail),
    path('BuildConfComparison/<int:id>/start', view_build_conf_comparison.start),
    path('BuildConfComparison/<int:id>/stop', view_build_conf_comparison.stop),
    path('BuildConfComparison/<int:id>/delete', view_build_conf_comparison.delete),
    path('BuildConfComparison/<int:id>/result/json', view_build_conf_comparison.resultJson),
    path("BuildConfComparison/<int:id>/result/view", view_build_conf_comparison.resultView),

    # Cve
    path('Cve/list', view_cve.cveList),

]
