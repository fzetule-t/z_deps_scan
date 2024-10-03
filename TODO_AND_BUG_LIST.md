Issue deleting dirs (user perm)

Review bug handling and message display to user

Prevent relaunch of something already running

# JVM

Allow to choose on which java version the mvn and gradle commands runs (nb: sdkman!)
Gradle JAVA compatibility list: https://docs.gradle.org/current/userguide/compatibility.html

# Gradle

Incomplete dependency tree, can use below code:

    https://stackoverflow.com/questions/21645071/using-gradle-to-find-dependency-tree
    project.rootProject.allprojects {
    apply plugin: 'project-report'
    
        this.task("allDependencies", DependencyReportTask::class) {
            evaluationDependsOnChildren()
            this.setRenderer(AsciiDependencyReportRenderer())
        }
    }

# Maven

## Error: "Unable to get mutable Windows environment variable map"
-> See Gradle JAVA compatibility list

## Keep in mind

Maven is not thread safe

# Docker:
 - no root user
 - secu files access (app, data & DB)