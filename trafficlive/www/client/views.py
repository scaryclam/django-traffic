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
        time_entries, page = user.get_time_entries(client.connection,
                                                   week_start,
                                                   week_end,
                                                   window_size=100)
        time_allocations, page = user.get_time_allocations(client.connection)
        import ipdb
        ipdb.set_trace()
        context['employee'] = user
        context['time_entries'] = time_entries
        context['time_allocations'] = time_allocations
        return context

