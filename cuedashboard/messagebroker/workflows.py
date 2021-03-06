# Copyright 2013 Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms import ValidationError
from horizon import exceptions
from horizon import forms
from horizon.utils import memoized
from horizon.utils import validators
from horizon import workflows
from openstack_dashboard import api
from oslo_utils import importutils

from cuedashboard.api import cluster_create

instance_utils = importutils.import_module(
    "openstack_dashboard.dashboards.project.instances.utils")


LOG = logging.getLogger(__name__)


class PasswordMixin(forms.SelfHandlingForm):
    password = forms.RegexField(
        label="Password",
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(render_value=False))
    no_autocomplete = True

    def clean(self):
        '''Check to make sure password fields match.'''
        data = super(forms.Form, self).clean()
        if 'password' in data:
            if data['password'] != data.get('confirm_password', None):
                raise ValidationError('Passwords do not match.')
        return data


class SetInstanceDetailsAction(workflows.Action):
    name = forms.CharField(max_length=80, label="Cluster Name")
    flavor = forms.ChoiceField(label="Flavor",
                               help_text="The amount of RAM and CPU included"
                                         " in each node of the cluster.")
    size = forms.IntegerField(label="Cluster Size",
                              min_value=1,
                              initial=1,
                              help_text="The number of nodes that make up "
                                        "the cluster.")
    network = forms.ChoiceField(label="Network",
                                help_text="Network to attach to the "
                                          "cluster.")
    username = forms.CharField(max_length=80, label="User Name",
                               help_text="User name for logging into the "
                                         "RabbitMQ Management UI.")
    password = forms.RegexField(
        label="Password",
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(render_value=False))

    def clean(self):
        '''Check to make sure password fields match.'''
        data = super(forms.Form, self).clean()
        if 'password' in data:
            if data['password'] != data.get('confirm_password', None):
                raise ValidationError('Passwords do not match.')
        return data

    class Meta(object):
        name = "Details"
        help_text_template = "messagebroker/_launch_details_help.html"

    @memoized.memoized_method
    def flavors(self, request):
        try:
            return api.nova.flavor_list(request)
        except Exception:
            LOG.exception("Exception while obtaining flavors list")
            redirect = reverse("horizon:project:messagebroker:index")
            exceptions.handle(request,
                              'Unable to obtain flavors.',
                              redirect=redirect)

    def populate_flavor_choices(self, request, context):
        flavors = self.flavors(request)
        if flavors:
            return instance_utils.sort_flavor_list(request, flavors)
        return []

    @memoized.memoized_method
    def networks(self, request):
        try:
            tenant_id = self.request.user.tenant_id
            networks = api.neutron.network_list_for_tenant(request, tenant_id)
            network_list = [(network.id, network.name_or_id)
                            for network in networks]
        except Exception:
            network_list = []
            exceptions.handle(request,
                              'Unable to retrieve networks.')
        return network_list

    def populate_network_choices(self, request, context):
        return self.networks(request)

    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        flavors = json.dumps([f._info for f in
                              instance_utils.flavor_list(self.request)])
        try:
            extra['flavors'] = flavors

        except Exception:
            exceptions.handle(self.request,
                              "Unable to retrieve quota information.")
        return super(SetInstanceDetailsAction, self).get_help_text(extra)


class SetClusterDetails(workflows.Step):
    action_class = SetInstanceDetailsAction
    contributes = ("name", "flavor", "size", "network", "username", "password")


class CreateCluster(workflows.Workflow):
    slug = "create_cluster"
    name = "Create Cluster"
    finalize_button_name = "Create"
    success_message = 'Created cluster named "%(name)s".'
    failure_message = 'Unable to create cluster named "%(name)s".'
    success_url = "horizon:project:messagebroker:index"
    default_steps = (SetClusterDetails,)

    def __init__(self, request=None, context_seed=None, entry_point=None,
                 *args, **kwargs):
        super(CreateCluster, self).__init__(request, context_seed,
                                            entry_point, *args, **kwargs)
        self.attrs['autocomplete'] = (
            settings.HORIZON_CONFIG.get('password_autocomplete'))

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown cluster')
        return message % {"name": name}

    def handle(self, request, context):
        try:
            LOG.info("Launching message broker cluster with parameters "
                     "{name=%s, flavor=%s, size=%s, nics=%s}",
                     context['name'], context['flavor'],
                     context['size'], context['network'])

            cluster_create(request, context['name'], context['network'],
                           context['flavor'], context['size'],
                           context['username'], context['password'])
            return True
        except Exception:
            exceptions.handle(request)
            return False
