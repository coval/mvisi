from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^visi/', include('visi.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    #(r'^check/$', 'panel.views.check_dependency'),
    (r'^projects/(?P<project_id>\d+)/packages/(?P<package_id>\d+)/check/$', 'panel.views.check_package'),
    (r'^projects/(?P<project_id>\d+)/packages/(?P<package_id>\d+)/$', 'panel.views.show_package'),
    (r'^projects/(?P<project_id>\d+)/check/$', 'panel.views.package_available_versions'),
    (r'^projects/(?P<project_id>\d+)/$', 'panel.views.project_view'),
    #(r'^projects/(?P<project_id>\d+)/packages/$', 'panel.views.packages'),
    (r'^projects/', 'panel.views.projects_main'),
    (r'^components/(?P<component_id>\d+)/check/$', 'panel.views.check_available_components'),
    
    (r'^components/(?P<component_id>\d+)/$', 'panel.views.component_info'),
    #(r'^components/$', 'panel.views.components'),
    
    # Ajax
    (r'^ajax/component/check/$', 'panel.views.ajax_check_available_components'),
    (r'^ajax/package/check/$', 'panel.views.ajax_check_package'),
    (r'^ajax/project/check/$', 'panel.views.ajax_package_available_versions'),
    
    
    
    
    (r'^$', 'panel.views.projects_main'),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': '/home/pawel/visi/static'}),
   
)
