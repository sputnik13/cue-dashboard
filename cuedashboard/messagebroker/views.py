# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Authors: Steve Leon <kokhang@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Copyright [2014] Hewlett-Packard Development Company, L.P.
# limitations under the License.

from cuedashboard import api
from cuedashboard.messagebroker.tables import ClusterTable
from cuedashboard.messagebroker.tabs import ClusterDetailTabs
from cuedashboard.messagebroker import workflows as cue_workflows

from django.core.urlresolvers import reverse
from horizon import tables
from horizon import tabs as horizon_tabs
from horizon.utils import memoized
from horizon import workflows


class IndexView(tables.DataTableView):
    table_class = ClusterTable
    template_name = 'messagebroker/index.html'
    page_title = "Clusters"

    def get_data(self):
        return api.clusters_list(self.request)


class CreateClusterView(workflows.WorkflowView):
    workflow_class = cue_workflows.CreateCluster
    template_name = "messagebroker/launch.html"
    page_title = "Create Cluster"


class DetailView(horizon_tabs.TabbedTableView):
    tab_group_class = ClusterDetailTabs
    template_name = 'messagebroker/detail.html'
    page_title = "Cluster Details: {{ cluster.name }}"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        cluster = self.get_data()
        table = ClusterTable(self.request)
        context["cluster"] = cluster
        flavor = api.flavor(self.request, cluster.flavor)
        context["flavor"] = flavor.name
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(cluster)
        return context

    @memoized.memoized_method
    def get_data(self):

        cluster_id = self.kwargs['cluster_id']
        cluster = api.cluster_get(self.request, cluster_id)
        return cluster

    def get_tabs(self, request, *args, **kwargs):
        cluster = self.get_data()
        # Get flavor name
        flavor = api.flavor(self.request, cluster.flavor)
        return self.tab_group_class(request,
                                    cluster=flavor,
                                    flavor=flavor.name,
                                    **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:project:messagebroker:index')
