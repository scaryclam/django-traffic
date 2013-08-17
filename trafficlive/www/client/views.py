from datetime import datetime, timedelta
from collections import OrderedDict

from django.views.generic import View, TemplateView, FormView
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.views import REDIRECT_FIELD_NAME
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url, HttpResponseRedirect
from django.core.urlresolvers import reverse

from trafficlive.client import Client


class Dashboard(TemplateView):
    template_name = 'client/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(Dashboard, self).get_context_data(**kwargs)
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.username)
        user = client.get_employee_list(
                filter_by='emailAddress|EQ|"%s"' % self.request.user.username)[0][0]

        week_start = datetime.now() - timedelta(days=datetime.now().isoweekday() - 1)
        week_end = week_start + timedelta(days=7)

        time_entries = user.get_time_entries(client.connection,
                                             week_start,
                                             week_end,
                                             window_size=100)
        time_allocations, page = user.get_time_allocations(client.connection,
                                                           window_size=100)
        job_tasks = user.get_job_task_allocations(client.connection,
                                                  window_size=100)
        time_entries_by_day = self.group_time_entries(time_entries)

        context['employee'] = user
        context['time_entries_by_day'] = time_entries_by_day
        context['time_entries_start'] = week_start.strftime('%Y-%m-%d')
        context['time_entries_end'] = week_end.strftime('%Y-%m-%d')
        context['time_allocations'] = time_allocations
        context['job_tasks'] = job_tasks
        return context

    def group_time_entries(self, time_entries):
        groups = OrderedDict()

        for time_entry in time_entries:
            key = datetime.strptime(
                time_entry.start_time, '%Y-%m-%dT%H:%M:%S.000+0000').strftime('%Y-%m-%d')
            if not groups.get(key):
                groups[key] = []
            groups[key].append(time_entry)

        return groups


class LoginView(FormView):
    template_name = 'client/login.html'
    form_class = AuthenticationForm

    def post(self, request, *args, **kwargs):
        return super(LoginView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        redirect_to = self.get_success_url()
        if not is_safe_url(url=redirect_to, host=self.request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        login(self.request, form.get_user())

        return HttpResponseRedirect(redirect_to)

    def get_success_url(self):
        if self.request.GET.get(REDIRECT_FIELD_NAME, False):
            redirect = resolve_url(self.request.GET[REDIRECT_FIELD_NAME])
        else:
            redirect = reverse('dashboard')
        return redirect
