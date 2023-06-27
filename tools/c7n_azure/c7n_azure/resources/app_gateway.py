# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

from c7n_azure.resources.arm import ArmResourceManager
from c7n_azure.provider import resources

from c7n.filters import Filter
from c7n.utils import type_schema


@resources.register('application-gateway')
class ApplicationGateway(ArmResourceManager):
    """Azure Application Gateway

    :example:

    This policy will find all Application Gateways

    .. code-block:: yaml

        policies:
          - name: app_gateways
            resource: azure.application-gateway

    """

    class resource_type(ArmResourceManager.resource_type):
        doc_groups = ['Network']

        service = 'azure.mgmt.network'
        client = 'NetworkManagementClient'
        enum_spec = ('application_gateways', 'list_all', None)
        default_report_fields = (
            'name',
            'location',
            'resourceGroup'
        )
        resource_type = 'Microsoft.Network/applicationGateways'


@ApplicationGateway.filter_registry.register('waf')
class ApplicationGatewayWafFilter(Filter):
    """
    Filter Application Gateways using WAF rule configuration

    :example:

    Return all the App Gateways which have rule '944240' disabled.

    .. code-block:: yaml

        policies:
          - name: test-app-gateway
            resource: azure.application-gateway
            filters:
              - type: waf
                override_rule: 944240
                state: disabled
    """

    schema = type_schema(
        'waf',
        required=['override_rule', 'state'],
        **{
            'override_rule': {'type': 'number'},
            'state': {'type': 'string', 'enum': ['disabled']}}
    )

    def process(self, resources, event=None):

        filter_override_rule = self.data.get('override_rule')
        filter_state = self.data.get('state')

        client = self.manager.get_client()
        app_gate_wafs = list(client.web_application_firewall_policies.list_all())
        result = []

        for resource in resources:
            if 'firewallPolicy' not in resource['properties']:
                continue

            waf_policy_name = resource['properties']['firewallPolicy']['id']
            for app_gate_waf in app_gate_wafs:
                if app_gate_waf.id != waf_policy_name:
                    continue

                app_gate_waf = app_gate_waf.serialize(True).get('properties', {})
                for rule_set in app_gate_waf.get('managedRules').get('managedRuleSets'):
                    for group in rule_set.get('ruleGroupOverrides'):
                        for rule in group.get('rules'):
                            if filter_override_rule == int(rule.get('ruleId')) \
                                and filter_state.lower() == rule.get('state').lower():
                                result.append(resource)

        return result
