import json
from datetime import datetime, timedelta
from collections import OrderedDict

from django.views.generic import View, TemplateView, FormView, View
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.views import REDIRECT_FIELD_NAME
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string

from trafficlive.client import Client


class Dashboard(TemplateView):
    template_name = 'client/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(Dashboard, self).get_context_data(**kwargs)
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.username,
                        base_url=settings.TRAFFIC_BASE_URL)
        user = client.get_employee_list(
                filter_by='emailAddress|EQ|"%s"' % self.request.user.username)[0][0]

        week_start = datetime.now() - timedelta(days=datetime.now().isoweekday() - 1)
        week_end = week_start + timedelta(days=5)

        time_entries = user.get_time_entries(client.connection,
                                             week_start,
                                             week_end,
                                             window_size=100)
        time_allocations, page = user.get_time_allocations(client.connection,
                                                           window_size=100)
        job_tasks = user.get_job_task_allocations(client.connection,
                                                  window_size=100)
        time_entries_by_day = self.group_time_entries(time_entries, week_start)

        context['employee'] = user
        context['time_entries_by_day'] = time_entries_by_day
        context['time_entries_start'] = week_start.strftime('%Y-%m-%d')
        context['time_entries_end'] = week_end.strftime('%Y-%m-%d')
        context['time_allocations'] = time_allocations
        context['job_tasks'] = job_tasks
        return context

    def group_time_entries(self, time_entries, start_day, days=5):
        # Creates an OrderedDict containing n days of empty lists.
        # E.g. OrderedDict([('2013-08-19', []), ('2013-08-20', [])])
        groups = OrderedDict(
            [((start_day + timedelta(days=num)).strftime('%Y-%m-%d'), []) for num in xrange(5)])
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.username,
                        base_url=settings.TRAFFIC_BASE_URL)


        for time_entry in time_entries:
            job = client.get_job_id(time_entry.job_id)
            time_entry_start_dt = datetime.strptime(
                time_entry.start_time, '%Y-%m-%dT%H:%M:%S.000+0000')
            time_entry_end_dt = datetime.strptime(
                time_entry.end_time, '%Y-%m-%dT%H:%M:%S.000+0000')
            time_entry.date = time_entry_start_dt.strftime('%Y-%m-%d')
            time_entry.start = time_entry_start_dt.strftime('%H:%M:%S')
            time_entry.end = time_entry_end_dt.strftime('%H:%M:%S')
            time_entry.job_number = job.job_number
            key = time_entry_start_dt.strftime('%Y-%m-%d')
            if not groups.get(key):
                groups[key] = {'time_entries': [], 'total_minutes': 0}
            groups[key]['time_entries'].append(time_entry)
            groups[key]['total_minutes'] += time_entry.minutes

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


class SearchJobNumbers(View):
    def post(self, request, *args, **kwargs):
        client = Client(settings.TRAFFIC_API_KEY,
                        request.user.username,
                        base_url=settings.TRAFFIC_BASE_URL)
        job_number = request.POST.get('job_number', '')
        if not job_number.startswith('J'):
            job_number = 'J%s' % job_number
        filter_str = 'jobNumber|EQ|"%s"' % job_number
        job_list = client.get_job_list(filter_by=filter_str)
        json_data = {'job_html_frags': []}
        for job in job_list[0]:
            job.get_job_detail(client.connection)
            html_frag = render_to_string(
                "client/partials/job_description.html", {'job': job})
            json_data['job_html_frags'].append(html_frag)
        return HttpResponse(json.dumps(json_data))


class UpdateTimeEntry(View):
    def post(self, request, *args, **kwargs):
        client = Client(settings.TRAFFIC_API_KEY,
                        request.user.username,
                        base_url=settings.TRAFFIC_BASE_URL)
        start = "%sT%s.000+0000" % (request.POST['time_entry_day'],
                                    request.POST['start_time'])
        end = "%sT%s.000+0000" % (request.POST['time_entry_day'],
                                  request.POST['end_time'])
        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.000+0000")
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S.000+0000")
        seconds = (end_dt - start_dt).seconds
        if seconds > 0:
            minutes = seconds / 60
        else:
            minutes = 0
        time_entry_id = request.POST['time_entry_id']

        time_entry = client.get_time_entry(time_entry_id)
        time_entry.start_time = start
        time_entry.end_time = end
        time_entry.minutes = minutes
        time_entry.date_modified = None
        response = client.update_time_entry(time_entry)
        json_data = {}
        return HttpResponse(json.dumps(json_data))
