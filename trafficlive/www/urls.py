from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy

from apps.client.views import Dashboard, LoginView, SearchJobNumbers, UpdateTimeEntry, CreateTimeEntry


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^$', login_required(Dashboard.as_view()), name='dashboard'),
    url(r'^job/search/$', login_required(SearchJobNumbers.as_view()), name='job_search_ajax'),
    url(r'^job/update/$', login_required(UpdateTimeEntry.as_view()), name='job_update_ajax'),
    url(r'^job/create/$', login_required(CreateTimeEntry.as_view()), name='job_time_create_ajax'),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', LoginView.as_view(), {}, name='auth_login'),
    url(r'^logout/$', auth_views.logout,
        {'next_page': reverse_lazy('auth_login')}, name='auth_logout'),
)
