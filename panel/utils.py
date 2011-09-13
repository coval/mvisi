import threading, re
import urllib, urllib2, base64

try:
    from BeautifulSoup import BeautifulSoup
except:
    pass

from panel.models import Configuration, Project, Component, Package

component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre':'c', 'preview':'c','-':'final-','rc':'c','dev':'@'}.get


class RNObject(object):
    def __init__(self, line, id):
        self.line = line
        self.id = id


def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part,part)
        if not part or part=='.':
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        else:
            yield '*'+part

    yield '*final'  # ensure that alpha/beta/candidate are before final

def parse_version(s):
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            if part<'*final':   # remove '-' before a prerelease tag
                while parts and parts[-1]=='*final-': parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1]=='00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)


def get_login( *some_vars ):
    """ Function for pysvn callback """
    #ToDo: better password corelation with proper configurations
    try:
        conf = Configuration.objects.get(id=1)
        username = conf.username
        password = conf.password
    except Exception, e:
        username = ''
        password = ''
    return True, username, password, True


def ssl_server_trust_prompt( *some_vars ):
    """ Function for pysvn callback """
    return True, 1, True

def get_page(url, conf_id=1):
    conf = Configuration.objects.get(id=conf_id)
    username = conf.username
    password = conf.password
    
    req = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    req.add_header("Authorization", "Basic %s" % base64string)
    response = urllib2.urlopen(req)
    the_page = response.read()
    response.close()
    return the_page

def find_tagbase(pom, component, conf):
    """ Getting tagbase for component or package"""
    if component.tagbase:
        return component.tagbase
    
    page = get_page(pom, conf.id)
    soup = BeautifulSoup(page)
    tagbase = soup.find('tagbase')
    scm = soup.find('scm')
    if scm:
        scm = scm.find('connection').string
        scm = scm.replace("scm:svn:",'')
        component.svntagpath = scm
        component.save()
    
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
        find_tagbase(new_pom, component, conf)
    else:
        print tagbase.string
        component.tagbase = tagbase.string
        component.save()
        return tagbase.string




