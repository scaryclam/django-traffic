from datetime import datetime, timedelta

from django.views.generic import View, TemplateView
from django.http import HttpResponse
from django.conf import settings

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

        context['employee'] = user
        context['time_entries'] = time_entries
        context['time_entries_start'] = week_start.strftime('%Y-%m-%d')
        context['time_entries_end'] = week_end.strftime('%Y-%m-%d')
        context['time_allocations'] = time_allocations
        context['job_tasks'] = job_tasks
        return context
