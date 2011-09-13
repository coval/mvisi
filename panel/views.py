# -*- coding: utf-8 -*-

import urllib, urllib2, base64
import threading, re
try:
    import pysvn
    from BeautifulSoup import BeautifulSoup
    from fabric.api import local
except:
    pass

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from panel.models import Configuration, Project, Component, Package
from panel.utils import parse_version, get_page, RNObject



def ajax_package_available_versions(request):
    if request.GET:
        project_id = request.GET.get('project_id','')
        project_id = int(project_id)
        package_available_versions_inner(request, project_id)
    
    return HttpResponse("OK")


def package_available_versions(request, project_id=1):
    package_available_versions_inner(request, project_id)
    return HttpResponseRedirect('/projects/%s/'%project_id)

def package_available_versions_inner(request, project_id=1):
    """ Checks available project versions """
    project = Project.objects.get(id=int(project_id))
    page = get_page(project.get_mvn_metadata_url(), project.configuration.id)
    soup = BeautifulSoup(page)
    versions = soup.findAll('version')
    artifactId = soup.find('artifactid')
    groupId = soup.find('groupid')
    if not project.artifactId or not project.groupId:
        project.artifactId = artifactId.string if artifactId else ''
        project.groupId = groupId.string if groupId else ''
        project.save()
    for version in versions:
        package, created = Package.objects.get_or_create(version=version.string, project=project)
        package.get_tag_base()

    

def ajax_check_package(request):
    if request.GET:
        project_id = request.GET.get('project_id','')
        package_id = request.GET.get('package_id','')
        project_id = int(project_id)
        package_id = int(package_id)
        
    check_package_inner(request, project_id, package_id)
    return HttpResponse("OK")


def check_package(request, project_id=1, package_id=1):
    check_package_inner(request, project_id, package_id)
    return HttpResponseRedirect('/projects/%s/packages/%s/'%(project_id, package_id))
    

def check_package_inner(request, project_id=1, package_id=1):
    """ Check package dependencies """
    project_id = int(project_id)
    package_id = int(package_id)
    project = Project.objects.get(id=project_id)
    package = Package.objects.get(id=package_id)
    configuration = project.configuration
    filtr = project.configuration.filter
    url = package.get_mvn_pom_url()
    
    local("rm -rf tempdir")
    local("mkdir tempdir")
    page = get_page(package.get_mvn_pom_url(), project.configuration.id)
    f = open('tempdir/pom.xml','w')
    f.write(page)
    f.close()
    out = local("cd tempdir && mvn help:effective-pom")
    soup = BeautifulSoup(out)
    dep = soup.findAll('dependency')
    for d in dep:
        if filtr in d.find('groupid').string:
            groupid = d.find('groupid').string
            artifactid = d.find('artifactid').string
            version = d.find('version').string
            component, created = Component.objects.get_or_create(name=artifactid, artifactId=artifactid, configuration=configuration,
                                                                 groupId=groupid, version=version)
            component.get_tag_base()
            component.package.add(package)
            component.save()
            
            t = threading.Thread(target=component.get_release_note)
            t.setDaemon(True)
            t.start()

            #t1 = threading.Thread(target=component.check_available_components)
            #t1.setDaemon(True)
            #t1.start()
            
            #ToDo: wyniesc to do ajaxa
            component.check_available_components()
    return 
    #return HttpResponseRedirect('/projects/%s/packages/%s/'%(project_id, package_id))



def ajax_check_available_components(request):
    if request.GET:
        component_id = request.GET.get('component_id','')
        if component_id:
            component_id = int(component_id)
            component = Component.objects.get(id=component_id)
            component.check_available_components()
    return HttpResponse(component_id)

def check_available_components(request, component_id=1):
    """ Check component list """
    component_id = int(component_id)
    component = Component.objects.get(id=component_id)
    component.check_available_components()
    return HttpResponseRedirect('/components/%s/'%component_id)

def projects_main(request):
    "Project list "
    c = dict()
    c['projects'] = Project.objects.all()
    return render_to_response('projects.html', c)

def project_view(request, project_id=1):
    " Main project view"
    c = dict()
    project = Project.objects.get(id=int(project_id))
    c['project'] = project
    packages = Package.objects.filter(project=project)
    c['packages'] = sorted(packages, key=lambda package: parse_version(package.version), reverse=True)
    return render_to_response('project.html', c)
    
    
def show_package(request, project_id, package_id):
    "package view"
    c = dict()
    log_message = set()
    new_messages = {}
    project = Project.objects.get(id=int(project_id))
    package = Package.objects.get(id=int(package_id))
    previous_package = package.get_previous_package()
    
    components = Component.objects.filter(package=package).order_by('artifactId')

    new_components = []
    for component in components:
        component.in_previous = component.in_other_package(package.get_previous_package())
        component.in_next = component.in_other_package(package.get_next_package())
        new_components.append(component)
        
        all_components = component.get_available_components()
        index_prev = all_components.index(component.in_previous) if component.in_previous else 0
        index_curr = all_components.index(component)
        step = index_prev - index_curr
        if step > 1:
            for ind in range(index_curr +1, index_prev):
                for line in all_components[ind].get_release_note().splitlines():
                    if not "[maven-release-plugin]" in line and line != '':
                        if new_messages.has_key(line):
                            ids = new_messages[line]
                            new_messages[line].append(all_components[ind])
                        else:
                            new_messages[line] = [all_components[ind],]
        
        if previous_package not in component.package.all():
            for line in component.release_notes.splitlines():
                if not "[maven-release-plugin]" in line and line != '':
                    if new_messages.has_key(line):
                        ids = new_messages[line]
                        new_messages[line].append(component)
                    else:
                        new_messages[line] = [component,]
        
    c['project'] = project
    c['package'] = package
    c['components'] = new_components
    c['release_notes'] = new_messages
    c['previous_package'] = previous_package
    
    return render_to_response('package.html', c)

def component_info(request, component_id):
    "Component info"
    c = dict()
    component_id = int(component_id)
    component = Component.objects.get(id=component_id)
    c['component'] = component
    if not component.tagbase:
        component.get_tag_base()
        
    log_ob = component.get_release_note().splitlines()
    c['release_notes'] = log_ob
    return render_to_response('component.html', c)
    
    
    
    
    
