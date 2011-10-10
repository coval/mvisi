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
    svnroot = models.CharField(max_length=256, help_text='Root path ex.: https://your_company/your_project/')
    mvnroot = models.CharField(max_length=256, help_text='Root path ex.: https://your_company/your_project/releases/')
    username = models.CharField(max_length=32, blank=True, help_text='Username for authorization to svn and maven repo')
    password = models.CharField(max_length=32, blank=True, help_text='Password for authorization to svn and maven repo')
    tempdir = models.CharField(max_length=32, blank=True)
    filter = models.CharField(max_length=32, blank=True, help_text='Restrict only to those groups. Ex. com.nsn')

    def __unicode__(self):
        return "Config: %s"%self.id


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
        conf = self.configuration
        return conf.mvnroot + self.mvnpath

    def get_mvn_metadata_url(self):
        return self.get_mvn_url() + "/maven-metadata.xml"
    
    def get_absolute_url(self):
        return "/projects/%s/"%self.id


class Package(models.Model):
    project = models.ForeignKey(Project)
    description = models.CharField(max_length=256, blank=True)
    version = models.CharField(max_length=256,)
    tagbase = models.CharField(max_length=512, blank=True)
    svnpath = models.CharField(max_length=1025, blank=True)
    mvnpath = models.CharField(max_length=512, blank=True)
    valid = models.CharField(max_length=256, blank=True)
    date = models.DateField(null=True)
    plaftorm_installation = models.CharField(max_length=256, blank=True)
    
    def __unicode__(self):
        return "%s - %s"%(self.project.name, self.version)
    
    def get_absolute_url(self):
        return "/projects/%s/packages/%s/"%(self.project.id, self.id)

    def get_tag_base(self):
        from panel.utils import find_tagbase
        pom_url = self.get_mvn_pom_url()
        conf = self.project.configuration
        return find_tagbase(pom_url, self, conf)

    def __get_login(self, *some_vars):
        from panel.utils import get_login
        conf = self.project.configuration
        return get_login(conf)


    def get_svn_tag(self):
        module_name = self.get_tag_base().split('/')[-1]
        return self.tagbase + "/" + self.project.artifactId + '-' + self.version
    
    def get_svn_date(self):
        if self.date:
            return self.date
        from panel.utils import ssl_server_trust_prompt
        client = pysvn.Client()
        client.callback_get_login = self.__get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        info = client.info2(self.get_svn_tag()+"/"+"pom.xml")
        self.revision = info[0][1]['last_changed_rev'].number
        date = info[0][1]['last_changed_date']
        self.date = datetime.date.fromtimestamp(date)
        self.save()
        return self.date

    
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
    mvnpath = models.CharField(max_length=512, blank=True)
    svnpath = models.CharField(max_length=1025, blank=True)
    svntagpath = models.CharField(max_length=1025, blank=True)
    revision = models.IntegerField(null=True)
    date = models.DateField(null=True)
    release_notes = models.TextField(max_length=2500, blank=True)
    configuration = models.ForeignKey(Configuration)

    def get_absolute_url(self):
        return "/components/%s/"%self.id

    def get_tag_base(self):
        conf = self.configuration
        if self.tagbase:
            return self.tagbase.replace(conf.svnroot,'')
        from panel.utils import find_tagbase
        pom_url = self.get_mvn_pom_url()
        find_tagbase(pom_url, self, conf)
        return self.tagbase.replace(conf.svnroot,'')

    
    def get_mvn_url(self):
        conf = self.configuration
        short = self.groupId.replace('.','/') + '/' + self.artifactId
        return conf.mvnroot + short
    
    def get_mvn_metadata_url(self):
        return self.get_mvn_url() + "/maven-metadata.xml"

    def get_mvn_pom_url(self):
        return self.get_mvn_url() + "/" + self.version + "/" + self.artifactId + "-" + self.version + ".pom"
    
    def __get_login(self, *some_vars):
        from panel.utils import get_login
        conf = self.configuration
        return get_login(conf)
    
    
    def get_svn_tag(self):
        if self.svntagpath:
            return self.svntagpath
        from panel.utils import ssl_server_trust_prompt
        client = pysvn.Client()
        client.callback_get_login = self.__get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        dir_list = client.ls(str(self.tagbase))
        for dir in dir_list:
            if self.version in dir['name']:
                print dir['name']
                self.svntagpath = dir['name']
                self.save()
                return dir['name']
        return ""
    
   
    def get_svn_revision(self):
        if self.revision:
            return self.revision
        from panel.utils import ssl_server_trust_prompt
        client = pysvn.Client()
        client.callback_get_login = self.__get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        if not self.revision or not self.date:
            print self.get_svn_tag()+"/"+"pom.xml"
            try:
                info = client.info2(self.get_svn_tag()+"/"+"pom.xml")
            except Exception, e:
                print "Error getting revision: %s"%e
                return ""
            self.revision = info[0][1]['last_changed_rev'].number
            date = info[0][1]['last_changed_date']
            self.date = datetime.date.fromtimestamp(date)
            self.save()
        return self.revision

    def get_svn_previous_revision(self):
        "Revision of previously released component"
        from panel.utils import ssl_server_trust_prompt
        client = pysvn.Client()
        client.callback_get_login = self.__get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        
        #self.get_available_components()
        try:
            last_nr = self.get_svn_tag().split('.')[-1]
            last_nr = int(last_nr) - 1 #ToDo: refactor
            new_tag = self.get_svn_tag().split('.')[:-1]
            new_tag = '.'.join(new_tag) + '.' + str(last_nr)
            info = client.info2(new_tag+"/"+"pom.xml")
        except Exception, e:
            print "Error getting previous revision: %s"%e
            return ""
        return info[0][1]['last_changed_rev'].number

    def compare_revisions(self, old_revision, new_revision):
        from panel.utils import ssl_server_trust_prompt
        
        tag = self.get_svn_tag()
        tag = tag.replace('tags','trunk').split('/')[:-1]
        svnpath = '/'.join(tag)
            
        #svnpath = self.svnpath
        #print svnpath
        client = pysvn.Client()
        client.callback_get_login = self.__get_login
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        
        try:
            log = client.log(svnpath, revision_start=pysvn.Revision( pysvn.opt_revision_kind.number, old_revision ),
                            revision_end=pysvn.Revision( pysvn.opt_revision_kind.number, new_revision ))
        except:
            #Specyfic hack
            tag[-1] = "mvn-%s"%tag[-1]
            svnpath = '/'.join(tag)
            print "New svnpath is: %s"%svnpath
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
            new_rev = self.get_svn_revision()
            old_rev = self.get_svn_previous_revision()
            
            if new_rev and old_rev:
                log_ob = self.compare_revisions(new_rev, old_rev)
                for log in log_ob:
                    log_message += "%s\n"%(log['message'])
                    self.release_notes = log_message
                    self.save()
        
        return self.release_notes

    def check_available_components(self):
        from panel.utils import get_page
        page = get_page(self.get_mvn_metadata_url(), self.configuration.id)
        soup = BeautifulSoup(page)
        versions = soup.findAll('version')
        for version in versions:
            new_comp, created = Component.objects.get_or_create(name=self.name, artifactId=self.artifactId, version=version.string,
                                                               groupId=self.groupId, configuration=self.configuration)
            new_comp.tagbase=self.tagbase
            new_comp.save()
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


    def __unicode__(self):
        return self.artifactId

