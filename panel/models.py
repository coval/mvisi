# -*- coding: utf-8 -*-
from django.db import models
import base64, datetime
from operator import itemgetter, attrgetter
try:
    from BeautifulSoup import BeautifulSoup
except:
    pass
try:
    import pysvn
except:
    pass


class Configuration(models.Model):
    svnroot = models.CharField(max_length=256, help_text='')
    mvnroot = models.CharField(max_length=256)
    username = models.CharField(max_length=32, blank=True)
    password = models.CharField(max_length=32, blank=True)
    tempdir = models.CharField(max_length=32, blank=True)
    filter = models.CharField(max_length=32, blank=True)

    def __unicode__(self):
        return "Base config"


class Project(models.Model):
    name = models.CharField(max_length=256)
    description = models.CharField(max_length=256, blank=True)
    artifactId = models.CharField(max_length=256, blank=True)
    groupId = models.CharField(max_length=256, blank=True)
    configuration = models.ForeignKey(Configuration)
    mvnpath = models.CharField(max_length=256, blank=True)
    svnpath = models.CharField(max_length=256, blank=True)

    def __unicode__(self):
        return self.name
    
    def get_mvn_url(self):
        conf = Configuration.objects.get(id=1)
        return conf.mvnroot + self.mvnpath

    def get_mvn_metadata_url(self):
        return self.get_mvn_url() + "/maven-metadata.xml"
    
    def get_absolute_url(self):
        return ''

class Package(models.Model):
    project = models.ForeignKey(Project)
    description = models.CharField(max_length=256, blank=True)
    version = models.CharField(max_length=256,)
    tagbase = models.CharField(max_length=256, blank=True)
    mvnpath = models.CharField(max_length=256, blank=True)
    valid = models.CharField(max_length=256, blank=True)
    plaftorm_installation = models.CharField(max_length=256, blank=True)
    
    def __unicode__(self):
        return "%s - %s"%(self.project.name, self.version)
    
    def get_absolute_url(self):
        return ''
    
    def get_mvn_pom_url(self):
        proj_url = self.project.get_mvn_url()
        url = proj_url + "/" + self.version + "/" + self.project.artifactId + "-" + self.version + ".pom"
        return url
    
    
    def get_other_package(self, factor=1):
        new_version = self.version.split('.')
        try:
            new_suffix = int(new_version[-1]) + factor
            new_version = '.'.join(new_version[:-1]) + '.' + str(new_suffix)
            new_version = Package.objects.get(version=new_version)
        except Exception, e:
            new_version = ''
        return new_version
    
    def get_previous_package(self):
        return self.get_other_package(factor = -1)

    def get_next_package(self):
        return self.get_other_package(factor = 1)


class Component(models.Model):
    name = models.CharField(max_length=256)
    artifactId = models.CharField(max_length=256, blank=True)
    groupId = models.CharField(max_length=256, blank=True)
    version = models.CharField(max_length=256, blank=True)
    package = models.ManyToManyField(Package, blank=True)
    tagbase = models.CharField(max_length=256, blank=True)
    mvnpath = models.CharField(max_length=256, blank=True)
    revision = models.IntegerField(null=True)
    date = models.DateField(null=True)
    release_notes = models.TextField(max_length=2500, blank=True) #ToDo: zmienic na pole

    def get_absolute_url(self):
        return ''

    def get_tag_base(self):
        conf = Configuration.objects.get(id=1)
        pom_url = self.get_mvn_pom_url()
        
        def find_tagbase(pom):
            from panel.utils import get_page
            if self.tagbase:
                return
            print(pom)
            page = get_page(pom)
            soup = BeautifulSoup(page)
            tagbase = soup.find('tagbase')
            if not tagbase:
                try:
                    version = soup.project.find('parent').version.string if soup.project.find('parent').version.string else soup.project.version.string
                except Exception, e:
                    print("Some error: %s"%e)
                    return ''
                artifactid = soup.project.find('parent').artifactid.string
                groupid = soup.project.find('parent').groupid.string
                if not artifactid:
                    return ''
                new_pom = conf.mvnroot + groupid.replace('.','/') + '/' + artifactid + '/' + version + "/" + artifactid + "-" + version + ".pom"
                find_tagbase(new_pom)
            else:
                self.tagbase = tagbase.string
                self.save()
        find_tagbase(pom_url)
        return self.tagbase.replace(conf.svnroot,'')

    
    def get_mvn_url(self):
        conf = Configuration.objects.get(id=1)
        short = self.groupId.replace('.','/') + '/' + self.artifactId
        return conf.mvnroot + short
    
    def get_mvn_metadata_url(self):
        return self.get_mvn_url() + "/maven-metadata.xml"

    def get_mvn_pom_url(self):
        return self.get_mvn_url() + "/" + self.version + "/" + self.artifactId + "-" + self.version + ".pom"
        
    def get_svn_tag(self):
        module_name = self.tagbase.split('/')[-1]
        return self.tagbase + "/" + module_name + '-' + self.version
    
    def get_svn_revision(self):
        from panel.utils import get_login, ssl_server_trust_prompt
        client = pysvn.Client()
        client.callback_get_login = get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        if not self.revision or not self.date:
            info = client.info2(self.get_svn_tag()+"/"+"pom.xml")
            self.revision = info[0][1]['last_changed_rev'].number
            date = info[0][1]['last_changed_date']
            self.date = datetime.date.fromtimestamp(date)
            self.save()
        return self.revision

    def get_svn_previous_revision(self):
        "Revision of previously released component"
        from panel.utils import get_login, ssl_server_trust_prompt
        client = pysvn.Client()
        client.callback_get_login = get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        
        last_nr = self.get_svn_tag().split('.')[-1]
        last_nr = int(last_nr) - 1
        new_tag = self.get_svn_tag().split('.')[:-1]
        new_tag = '.'.join(new_tag) + '.' + str(last_nr)
        info = client.info2(new_tag+"/"+"pom.xml")
        return info[0][1]['last_changed_rev'].number

    def compage_revisions(self, old_revision, new_revision):
        from panel.utils import get_login, ssl_server_trust_prompt
        
        tag = self.get_svn_tag()
        tag = tag.replace('tags','trunk').split('/')[:-1]
        svnpath = '/'.join(tag)
        
        client = pysvn.Client()
        client.callback_get_login = get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        
        log = client.log(svnpath, revision_start=pysvn.Revision( pysvn.opt_revision_kind.number, old_revision ),
                         revision_end=pysvn.Revision( pysvn.opt_revision_kind.number, new_revision ))
        return log

    def get_release_note(self):

        if self.release_notes:
            return self.release_notes
        log_ob=''
        simillar_component = Component.objects.filter(tagbase=self.tagbase, version=self.version).exclude(id=self.id)
        if simillar_component and simillar_component[0].release_notes:
            sim_com=simillar_component[0]
            self.revision = sim_com.revision
            self.date = sim_com.date
            self.release_notes = sim_com.release_notes
            log_ob = self.release_notes
            self.save()
        if not self.release_notes or self.release_notes == '':
            log_message = ''
            try:
                new_rev = self.get_svn_revision()
                old_rev = self.get_svn_previous_revision()
                log_ob = self.compage_revisions(new_rev, old_rev)
                for log in log_ob:
                    log_message += "%s\n"%(log['message'])
                    self.release_notes = log_message
                    self.save()
            except Exception, e:
                print("Error in getting release note: %s"%e)
                return ""
        
        return self.release_notes

    def check_available_components(self):
        from panel.utils import get_page
        page = get_page(self.get_mvn_metadata_url())
        soup = BeautifulSoup(page)
        versions = soup.findAll('version')
        for version in versions:
            new_comp, created = Component.objects.get_or_create(name=self.name, artifactId=self.artifactId, version=version.string,
                                                               groupId=self.groupId)
            new_comp.tagbase=self.tagbase
            new_comp.save()
        self.get_tag_base()
        return ''
    
    def get_available_components(self):
        from panel.views import parse_version
        components = Component.objects.filter(artifactId=self.artifactId, groupId=self.groupId)
        components = sorted(components, key=lambda component: parse_version(component.version), reverse=True)
        return components
    
    def get_newest_component(self):
        components = self.get_available_components()
        if components:
            return components[0] if components[0] != self else ''
        else:
            return ''
    
    def in_other_package(self, package):
        """ checks witch version is in given package """
        try:
            component = Component.objects.get(artifactId=self.artifactId, groupId=self.groupId, package=package)
        except:
            return ''
        return component


    def get_other_versions(self):
        "other versions of component"
        from panel.views import parse_version
        components = []
        comp = Component.objects.filter(artifactId=self.artifactId)
        #try:
        #    components = [c.version for c in comp if c.version != self.version]
        #except Exception, e:
        #    print e, components
        for c in comp:
            if c.version != self.version:
                components.append(c)
        components = sorted(components, key=lambda component: parse_version(component.version), reverse=True)
        return components


    def check_tag_base(self):
        pass


    def __unicode__(self):
        return self.artifactId

