# Generated by Django 5.0.6 on 2024-10-01 14:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BuildConf',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('updated_dt', models.DateTimeField(auto_now=True)),
                ('filePath', models.CharField(max_length=400)),
                ('type', models.CharField(choices=[('maven', 'Maven'), ('gradle', 'Gradle'), ('unknown', 'Unknown')], default='unknown', max_length=10)),
                ('dep_list_extract_start_dt', models.DateTimeField(blank=True, editable=False, null=True)),
                ('dep_list_extract_end_dt', models.DateTimeField(blank=True, editable=False, null=True)),
                ('dep_list_extract_status', models.CharField(choices=[('', 'None Done'), ('Running', 'Running'), ('OK', 'Ok'), ('KO', 'Ko')], default='', editable=False, max_length=50)),
                ('dep_tree_extract_start_dt', models.DateTimeField(blank=True, editable=False, null=True)),
                ('dep_tree_extract_end_dt', models.DateTimeField(blank=True, editable=False, null=True)),
                ('dep_tree_extract_status', models.CharField(choices=[('', 'None Done'), ('Running', 'Running'), ('OK', 'Ok'), ('KO', 'Ko')], default='', editable=False, max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Repo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('updated_dt', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('uri_type', models.CharField(choices=[('Git url', 'Git Url'), ('Local path', 'Path')], default='Git url', max_length=50)),
                ('uri', models.CharField(max_length=200)),
                ('path_local', models.CharField(blank=True, editable=False, max_length=500, null=True)),
                ('identifier_type', models.CharField(choices=[('branch', 'Branch'), ('tag', 'Tag')], default=None, editable=False, max_length=50, null=True)),
                ('identifier', models.CharField(editable=False, max_length=200, null=True)),
                ('user', models.CharField(blank=True, default='ENV_GIT_USER', max_length=200, null=True)),
                ('pwd', models.CharField(blank=True, default='ENV_GIT_PWD', max_length=200, null=True)),
                ('pull_start_dt', models.DateTimeField(blank=True, editable=False, null=True)),
                ('pull_end_dt', models.DateTimeField(blank=True, editable=False, null=True)),
                ('pull_status', models.CharField(choices=[('', 'None Done'), ('Running', 'Running'), ('OK', 'Ok'), ('KO', 'Ko')], default='', editable=False, max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='BuildConfComparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('updated_dt', models.DateTimeField(auto_now=True)),
                ('start_dt', models.DateTimeField(editable=False, null=True)),
                ('end_dt', models.DateTimeField(editable=False, null=True)),
                ('status', models.CharField(choices=[('', 'None Done'), ('Running', 'Running'), ('OK', 'Ok'), ('KO', 'Ko')], default='', editable=False, max_length=50)),
                ('build_conf_list', models.ManyToManyField(related_name='comparisons', to='deps.buildconf')),
            ],
        ),
        migrations.CreateModel(
            name='Dep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('updated_dt', models.DateTimeField(auto_now=True)),
                ('group', models.CharField(max_length=100)),
                ('artifact', models.CharField(max_length=100)),
                ('packaging', models.CharField(max_length=100)),
                ('version', models.CharField(max_length=100)),
                ('classifier', models.CharField(max_length=100, null=True)),
                ('is_removable', models.BooleanField(default=False)),
                ('in_dep_list', models.BooleanField(default=False)),
                ('in_dep_tree', models.BooleanField(default=False)),
                ('latestVersion', models.CharField(max_length=100, null=True)),
                ('isConstraint', models.BooleanField(default=False)),
                ('versionOverridden', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('is_resolvable', models.BooleanField(default=True)),
                ('buildConf', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dep_list', to='deps.buildconf')),
            ],
        ),
        migrations.CreateModel(
            name='Cve',
            fields=[
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('updated_dt', models.DateTimeField(auto_now=True)),
                ('id', models.CharField(max_length=200, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('cvssScore', models.FloatField()),
                ('reference', models.CharField(max_length=400)),
                ('repo_dep_list', models.ManyToManyField(related_name='cve_list', to='deps.dep')),
            ],
        ),
        migrations.AddField(
            model_name='buildconf',
            name='depTreeRoot',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='depTreeRoot', to='deps.dep'),
        ),
        migrations.CreateModel(
            name='LinkDep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('updated_dt', models.DateTimeField(auto_now=True)),
                ('a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='a_links', to='deps.dep')),
                ('b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='b_links', to='deps.dep')),
            ],
        ),
        migrations.CreateModel(
            name='Identifier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('branch', 'Branch'), ('tag', 'Tag')], default=None, max_length=50)),
                ('uri', models.CharField(max_length=200)),
                ('repo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='identifier_list', to='deps.repo')),
            ],
        ),
        migrations.AddField(
            model_name='buildconf',
            name='repo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='build_conf_list', to='deps.repo'),
        ),
    ]
