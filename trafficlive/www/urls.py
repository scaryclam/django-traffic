from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy

from client.views import Dashboard, LoginView


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^$', login_required(Dashboard.as_view()), name='dashboard'),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', LoginView.as_view(), {}, name='auth_login'),
    url(r'^logout/$', auth_views.logout,
        {'next_page': reverse_lazy('auth_login')}, name='auth_logout'),

)

