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
from django.template import RequestContext

from trafficlive.client import Client, TimeEntry
from www.apps.user.models import UserProfile


def get_time_period(request):
    if request.GET.get('period_start', None):
        period_start = datetime.strptime(request.GET['period_start'], "%Y-%m-%d")
        if request.GET.get('period_end'):
            period_end = datetime.strptime(request.GET['period_end'], "%Y-%m-%d")
        else:
            period_end = period_start + timedelta(days=5)
    else:
        period_start = datetime.now() - timedelta(days=datetime.now().isoweekday() - 1)
        period_end = period_start + timedelta(days=5)
    return period_start, period_end


class Dashboard(TemplateView):
    template_name = 'client/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(Dashboard, self).get_context_data(**kwargs)
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.email,
                        base_url=settings.TRAFFIC_BASE_URL)
        user = client.get_employee_list(
                filter_by='emailAddress|EQ|"%s"' % self.request.user.email)[0][0]

        period_start, period_end = get_time_period(self.request)

        time_allocations, page = user.get_time_allocations(client.connection,
                                                           window_size=100)
        job_tasks = user.get_job_task_allocations(client.connection,
                                                  window_size=100)
        context['employee'] = user
        context['time_entries_start'] = period_start.strftime('%Y-%m-%d')
        context['time_entries_end'] = period_end.strftime('%Y-%m-%d')
        context['time_allocations'] = time_allocations
        context['job_tasks'] = job_tasks
        return context


class JobTaskListUserView(TemplateView):
    template_name = "client/partials/job_task_list_user.html"

    def get(self, request, *args, **kwargs):
        ret_val = super(JobTaskListUserView, self).get_context_data(request, *args, **kwargs)
        if not ret_val.is_rendered:
            ret_val.render()
        return HttpResponse(json.dumps({'html': ret_val.content}))

    def get_context_data(self, **kwargs):
        context = super(JobTaskListUserView, self).get_context_data(**kwargs)
        user = client.get_employee_list(
                filter_by='emailAddress|EQ|"%s"' % self.request.user.email)[0][0]
        job_tasks = user.get_job_task_allocations(client.connection,
                                                  window_size=100)
        context['job_tasks'] = job_tasks
        return context


class TimeEntryListView(TemplateView):
    template_name = "client/partials/time_entry_list.html"

    def get(self, request, *args, **kwargs):
        ret_val = super(TimeEntryListView, self).get(request, *args, **kwargs)
        if not ret_val.is_rendered:
            ret_val.render()
        return HttpResponse(
                json.dumps({'html': ret_val.content,
                            'period_start': ret_val.context_data['time_entries_start'],
                            'period_end': ret_val.context_data['time_entries_end'],
                            'prev_period': {'start': ret_val.context_data['time_entries_prev_start'],
                                            'end': ret_val.context_data['time_entries_prev_end']},
                            'next_period': {'start': ret_val.context_data['time_entries_next_start'],
                                            'end': ret_val.context_data['time_entries_next_end']}}))

    def get_context_data(self, **kwargs):
        context = super(TimeEntryListView, self).get_context_data(**kwargs)
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.email,
                        base_url=settings.TRAFFIC_BASE_URL)
        user = client.get_employee_list(
                filter_by='emailAddress|EQ|"%s"' % self.request.user.email)[0][0]

        period_start, period_end = get_time_period(self.request)
        time_diff = period_end - period_start
        next_end = period_end + time_diff
        prev_start = period_start - time_diff

        time_entries = user.get_time_entries(client.connection,
                                             period_start,
                                             period_end,
                                             window_size=100)
        job_tasks = user.get_job_task_allocations(client.connection,
                                                  window_size=100)
        time_entries_by_day = self.group_time_entries(time_entries, period_start)

        context['time_entries_by_day'] = time_entries_by_day
        context['time_entries_start'] = period_start.strftime('%Y-%m-%d')
        context['time_entries_end'] = period_end.strftime('%Y-%m-%d')
        context['time_entries_next_start'] = period_end.strftime('%Y-%m-%d')
        context['time_entries_next_end'] = next_end.strftime("%Y-%m-%d")
        context['time_entries_prev_start'] = prev_start.strftime('%Y-%m-%d')
        context['time_entries_prev_end'] = period_start.strftime('%Y-%m-%d')
        return context

    def group_time_entries(self, time_entries, start_day, days=5):
        # Creates an OrderedDict containing n days of empty lists.
        # E.g. OrderedDict([('2013-08-19', []), ('2013-08-20', [])])
        groups = OrderedDict(
            [((start_day + timedelta(days=num)).strftime('%Y-%m-%d'), []) for num in xrange(5)])
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.email,
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
        try:
            profile = UserProfile.objects.get(user=self.request.user.pk)
            if profile.employee_id:
                return HttpResponseRedirect(redirect_to)
        except UserProfile.DoesNotExist:
            profile = UserProfile(user=self.request.user)
        # The employee id is not set. Do this before continuing
        client = Client(settings.TRAFFIC_API_KEY,
                        self.request.user.email,
                        base_url=settings.TRAFFIC_BASE_URL)
        user = client.get_employee_list(
            filter_by='emailAddress|EQ|"%s"' % self.request.user.email)[0][0]
        profile.employee_id = user.staff_id
        profile.save()

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
                        request.user.email,
                        base_url=settings.TRAFFIC_BASE_URL)
        job_number = request.POST.get('job_number', '')
        if not job_number.startswith('J'):
            job_number = 'J%s' % job_number
        filter_str = 'jobNumber|EQ|"%s"' % job_number
        job_list = client.get_job_list(filter_by=filter_str)
        json_data = {'job_html_frags': []}
        for job in job_list[0]:
            job.get_job_detail(client.connection)
            context = RequestContext(request, {'job': job,
                                               'day': request.POST['job_day']})
            html_frag = render_to_string(
                "client/partials/job_description.html", context)
            json_data['job_html_frags'].append(html_frag)
        return HttpResponse(json.dumps(json_data))


class UpdateTimeEntry(View):
    def post(self, request, *args, **kwargs):
        client = Client(settings.TRAFFIC_API_KEY,
                        request.user.email,
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
        prev_minutes = time_entry.minutes
        time_entry.start_time = start
        time_entry.end_time = end
        time_entry.minutes = minutes
        time_entry.date_modified = None
        response = client.update_time_entry(time_entry)
        json_data = {'day': request.POST['time_entry_day'],
                     'minutes': minutes - prev_minutes}
        return HttpResponse(json.dumps(json_data))


class CreateTimeEntry(View):
    def post(self, request, *args, **kwargs):
        start_val = request.POST['start_time']
        end_val = request.POST['end_time']
        day = request.POST['job_day']
        employee_id = request.user.get_profile().employee_id
        try:
            start_dt = datetime.strptime("%sT%s:00.000+0000" % (day, start_val),
                                         "%Y-%m-%dT%H:%M:%S.000+0000")
        except ValueError:
            return HttpResponse(json.dumps({'field': "start_time",
                                            'message': "Please use the format HH:MM"}), status=500)
        try:
            end_dt = datetime.strptime("%sT%s:00.000+0000" % (day, end_val),
                                       "%Y-%m-%dT%H:%M:%S.000+0000")
        except ValueError:
            return HttpResponse(json.dunps({'field': "end_time",
                                            'message': "Please use the format HH:MM"}), status=500)
        minutes = (end_dt - start_dt).seconds / 60
        data = {
            'jobId': {'id': request.POST['job_id']},
            'id': "-1",
            'version': "-1",
            'dateModified': None,
            'jobTaskId': {'id': request.POST['task_id']},
            'billable': False,
            'exported': False,
            'lockedByApproval': False,
            'comment': None,
            'endTime': "%sT%s.000+0000" % (day, end_val),
            'minutes': minutes,
            'trafficEmployeeId': {'id': employee_id},
            'taskDescription': request.POST['task_desc'],
            'taskComplete': None,
            'taskRate': {'amountString': request.POST['task_rate'].split('|')[0],
                         'currencyType': request.POST['task_rate'].split('|')[1]},
            'valueOfTimeEntry': {'amountString': 0,#request.POST['entry_value'].split('|')[0],
                                 'currencyType': "GBP"},#request.POST['entry_value'].split('|')[1]},
            'chargeBandId': {'id': request.POST['charge_band']},
            'timeEntryCost': {'amountString': request.POST['task_cost'].split('|')[0],
                              'currencyType': request.POST['task_cost'].split('|')[1]},
            'timeEntryPersonalRate': {'amountString': request.POST['personal_rate'].split('|')[0],
                                      'currencyType': request.POST['personal_rate'].split('|')[1]},
            'jobStageDescription': None,
            'lockedByApprovalEmployeeId': None,
            'lockedByApprovalDate': None,
            'exportError': None,
            'workPoints': None,
            'startTime': "%sT%s.000+0000" % (day, start_val),
        }
        client = Client(settings.TRAFFIC_API_KEY,
                        request.user.email,
                        base_url=settings.TRAFFIC_BASE_URL)
        time_entry = TimeEntry(data)
        new_time_entry = TimeEntry(
            json.loads(client.send_new_time_entry(time_entry)))
        new_time_entry.start = start_val
        new_time_entry.end = end_val
        new_time_entry.minutes = minutes
        job = client.get_job_id(new_time_entry.job_id)
        new_time_entry.job_number = job.job_number
        context = RequestContext(request, {'entry': new_time_entry,
                                           'day': request.POST['job_day']})
        html_frag = render_to_string(
            "client/partials/time_entry.html", context)
        return HttpResponse(json.dumps({'html': html_frag, 'day': day,
                                        'minutes': minutes}))
