# -*- coding: utf-8 -*-
from django.contrib import admin
from panel.models import Configuration, Project, Component, Package

class ComponentAdmin(admin.ModelAdmin):
    list_display = ['artifactId', 'version', 'groupId']




admin.site.register(Configuration)
admin.site.register(Component, ComponentAdmin)
admin.site.register(Project)
#admin.site.register(Component)
admin.site.register(Package)
