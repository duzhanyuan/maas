# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "DHCPSnippetHandler",
    "DHCPSnippetsHandler",
    ]

from email.utils import format_datetime

from maasserver.api.support import (
    admin_method,
    operation,
    OperationsHandler,
)
from maasserver.exceptions import MAASAPIValidationError
from maasserver.forms_dhcpsnippet import DHCPSnippetForm
from maasserver.models import DHCPSnippet
from piston3.utils import rc


DISPLAYED_DHCP_SNIPPET_FIELDS = (
    'id',
    'name',
    'value',
    'history',
    'description',
    'enabled',
    'node',
    'subnet',
    'global_snippet',
)


class DHCPSnippetHandler(OperationsHandler):
    """Manage an individual DHCP snippet.

    The DHCP snippet is identified by its id.
    """
    api_doc_section_name = "DHCP Snippet"
    create = None
    model = DHCPSnippet
    fields = DISPLAYED_DHCP_SNIPPET_FIELDS

    @classmethod
    def resource_uri(cls, dhcp_snippet=None):
        # See the comment in NodeHandler.resource_uri.
        if dhcp_snippet is not None:
            dhcp_snippet_id = dhcp_snippet.id
        else:
            dhcp_snippet_id = "id"
        return ('dhcp_snippet_handler', (dhcp_snippet_id,))

    @classmethod
    def value(handler, dhcp_snippet):
        return dhcp_snippet.value.data

    @classmethod
    def history(handler, dhcp_snippet):
        return [
            {
                'id': value.id,
                'value': value.data,
                'created': format_datetime(value.created),
            }
            for value in dhcp_snippet.value.previous_versions()
        ]

    @classmethod
    def global_snippet(handler, dhcp_snippet):
        return dhcp_snippet.node is None and dhcp_snippet.subnet is None

    def read(self, request, dhcp_snippet_id):
        """Read DHCP snippet.

        Returns 404 if the snippet is not found.
        """
        return DHCPSnippet.objects.get_dhcp_snippet_or_404(
            dhcp_snippet_id)

    @admin_method
    def update(self, request, dhcp_snippet_id):
        """Update a DHCP snippet.

        :param name: The name of the DHCP snippet.
        :type name: unicode

        :param value: The new value of the DHCP snippet to be used in
            dhcpd.conf. Previous values are stored and can be reverted.
        :type value: unicode

        :param description: A description of what the DHCP snippet does.
        :type description: unicode

        :param enabled: Whether or not the DHCP snippet is currently enabled.
        :type enabled: boolean

        :param node: The node the DHCP snippet is to be used for. Can not be
            set if subnet is set.
        :type node: unicode

        :param subnet: The subnet the DHCP snippet is to be used for. Can not
            be set if node is set.
        :type subnet: unicode

        :param global_snippet: Set the DHCP snippet to be a global option. This
            removes any node or subnet links.
        :type global_snippet: boolean

        Returns 404 if the DHCP snippet is not found.
        """
        dhcp_snippet = DHCPSnippet.objects.get_dhcp_snippet_or_404(
            dhcp_snippet_id)
        form = DHCPSnippetForm(instance=dhcp_snippet, data=request.data)
        if form.is_valid():
            return form.save()
        else:
            raise MAASAPIValidationError(form.errors)

    @admin_method
    def delete(self, request, dhcp_snippet_id):
        """Delete a DHCP snippet.

        Returns 404 if the DHCP snippet is not found.
        """
        dhcp_snippet = DHCPSnippet.objects.get_dhcp_snippet_or_404(
            dhcp_snippet_id)
        dhcp_snippet.delete()
        return rc.DELETED

    @admin_method
    @operation(idempotent=False)
    def revert(self, request, dhcp_snippet_id):
        """Revert the value of a DHCP snippet to an earlier revision.

        :param to: What revision in the DHCP snippet's history to revert to.
            This can either be an ID or a negative number representing how far
            back to go.
        :type to: integer

        Returns 404 if the DHCP snippet is not found.
        """
        revert_to = request.data.get('to')
        if revert_to is None:
            raise MAASAPIValidationError('You must specify where to revert to')
        try:
            revert_to = int(revert_to)
        except ValueError:
            raise MAASAPIValidationError(
                "%s is an invalid 'to' value" % revert_to)

        dhcp_snippet = DHCPSnippet.objects.get_dhcp_snippet_or_404(
            dhcp_snippet_id)
        try:
            def gc_hook(value):
                dhcp_snippet.value = value
                dhcp_snippet.save()
            dhcp_snippet.value.revert(revert_to, gc_hook=gc_hook)
            return dhcp_snippet
        except ValueError as e:
            raise MAASAPIValidationError(e.args[0])


class DHCPSnippetsHandler(OperationsHandler):
    """Manage the collection of all DHCP snippets in MAAS."""
    api_doc_section_name = "DHCP Snippets"
    update = delete = None

    @classmethod
    def resource_uri(cls, *args, **kwargs):
        return ('dhcp_snippets_handler', [])

    def read(self, request):
        """List all DHCP snippets."""
        return DHCPSnippet.objects.all().select_related(
            'value', 'subnet', 'node')

    @admin_method
    def create(Self, request):
        """Create a DHCP snippet.

        :param name: The name of the DHCP snippet. This is required to create
            a new DHCP snippet.
        :type name: unicode

        :param value: The snippet of config inserted into dhcpd.conf. This is
            required to create a new DHCP snippet.
        :type value: unicode

        :param description: A description of what the snippet does.
        :type description: unicode

        :param enabled: Whether or not the snippet is currently enabled.
        :type enabled: boolean

        :param node: The node this snippet applies to. Cannot be used with
            subnet or global_snippet.
        :type node: unicode

        :param subnet: The subnet this snippet applies to. Cannot be used with
            node or global_snippet.
        :type subnet: unicode

        :param global_snippet: Whether or not this snippet is to be applied
            globally. Cannot be used with node or subnet.
        :type global_snippet: boolean

        Returns 404 if the DHCP snippet is not found.
        """
        form = DHCPSnippetForm(data=request.data)
        if form.is_valid():
            return form.save()
        else:
            raise MAASAPIValidationError(form.errors)
