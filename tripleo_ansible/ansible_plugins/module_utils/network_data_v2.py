#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2018 OpenStack Foundation
# All Rights Reserved.
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

import collections
import ipaddress
import jsonschema
import yaml

DOMAIN_NAME_REGEX = (r'^(?=^.{1,255}$)(?!.*\.\..*)(.{1,63}\.)'
                     r'+(.{0,63}\.?)|(?!\.)(?!.*\.\..*)(^.{1,63}$)'
                     r'|(^\.$)$')
NET_DATA_V2_SCHEMA = '''
---
$schema: http://json-schema.org/draft-04/schema

definitions:
  domain_name_string:
    type: string
    pattern: {domain_name_regex}
  ipv4_allocation_pool:
    type: object
    properties:
      start:
        type: string
        ip_address_version: 4
      end:
        type: string
        ip_address_version: 4
    additionalProperties: False
    uniqueItems: true
    required:
    - start
    - end
  ipv4_route:
    type: object
    properties:
      destination:
        type: string
        ip_subnet_version: 4
      nexthop:
        type: string
        ip_address_version: 4
    additionalProperties: False
    uniqueItems: true
    required:
    - destination
    - nexthop
  ipv6_allocation_pool:
    type: object
    properties:
      start:
        type: string
        ip_address_version: 6
      end:
        type: string
        ip_address_version: 6
    additionalProperties: False
    uniqueItems: true
    required:
    - start
    - end
  ipv6_route:
    type: object
    properties:
      destination:
        type: string
        ip_subnet_version: 6
      nexthop:
        type: string
        ip_address_version: 6
    additionalProperties: False
    uniqueItems: true
    required:
    - destination
    - nexthop

  ipv4_subnet:
    type: object
    properties:
      ip_subnet:
        type: string
        ip_subnet_version: 4
      gateway_ip:
        type: string
        ip_address_version: 4
      allocation_pools:
        type: array
        items:
          $ref: "#/definitions/ipv4_allocation_pool"
      enable_dhcp:
        type: boolean
      routes:
        type: array
        items:
          $ref: "#/definitions/ipv4_route"
      vlan:
        type: integer
        minimum: 1
        maximum: 4096
      physical_network:
        type: string
      network_type:
        enum:
        - flat
        - vlan
      segmentation_id:
        type: integer
        minimum: 1
        maximum: 4096
    additionalProperties: False
    required:
    - ip_subnet

  ipv6_subnet:
    type: object
    properties:
      ipv6_subnet:
        type: string
        ip_subnet_version: 6
      gateway_ipv6:
        type: string
        ip_address_version: 6
      ipv6_allocation_pools:
        type: array
        items:
          $ref: "#/definitions/ipv6_allocation_pool"
      routes_ipv6:
        type: array
        items:
          $ref: "#/definitions/ipv6_route"
      ipv6_address_mode:
        enum:
        - null
        - dhcpv6-stateful
        - dhcpv6-stateless
      ipv6_ra_mode:
        enum:
        - null
        - dhcpv6-stateful
        - dhcpv6-stateless
      enable_dhcp:
        type: boolean
      vlan:
        type: integer
        minimum: 1
        maximum: 4096
      physical_network:
        type: string
      network_type:
        type: string
        enum:
        - flat
        - vlan
      segmentation_id:
        type: integer
        minimum: 1
        maximum: 4096
    additionalProperties: False
    required:
    - ipv6_subnet

  dual_subnet:
    type: object
    properties:
      ip_subnet:
        type: string
        ip_subnet_version: 4
      gateway_ip:
        type: string
        ip_address_version: 4
      allocation_pools:
        type: array
        items:
          $ref: "#/definitions/ipv4_allocation_pool"
      routes:
        type: array
        items:
          $ref: "#/definitions/ipv4_route"
      ipv6_subnet:
        type: string
        ip_subnet_version: 6
      gateway_ipv6:
        type: string
        ip_address_version: 6
      ipv6_allocation_pools:
        type: array
        items:
          $ref: "#/definitions/ipv6_allocation_pool"
      routes_ipv6:
        type: array
        items:
          $ref: "#/definitions/ipv6_route"
      ipv6_address_mode:
        enum:
        - null
        - dhcpv6-stateful
        - dhcpv6-stateless
      ipv6_ra_mode:
        enum:
        - null
        - dhcpv6-stateful
        - dhcpv6-stateless
      enable_dhcp:
        type: boolean
      vlan:
        type: integer
        minimum: 1
        maximum: 4096
      physical_network:
        type: string
      network_type:
        type: string
        enum:
        - flat
        - vlan
      segmentation_id:
        type: integer
        minimum: 1
        maximum: 4096
    additionalProperties: False
    required:
    - ip_subnet
    - ipv6_subnet

type: object
properties:
  name:
    type: string
  name_lower:
    type: string
  admin_state_up:
    type: boolean
  dns_domain:
    $ref: "#/definitions/domain_name_string"
  mtu:
    type: integer
    minimum: 1000
    maximum: 65536
  shared:
    type: boolean
  service_net_map_replace:
    type: string
  ipv6:
    type: boolean
  vip:
    type: boolean
  subnets:
    type: object
    additionalProperties:
      oneOf:
      - $ref: "#/definitions/ipv4_subnet"
      - $ref: "#/definitions/ipv6_subnet"
      - $ref: "#/definitions/dual_subnet"
additionalProperties: False
required:
- name
- subnets
'''.format(domain_name_regex=DOMAIN_NAME_REGEX)


def _get_detailed_errors(error, depth, absolute_schema_path, absolute_schema,
                         filter_errors=True):
    """Returns a list of error messages from all subschema validations.

    Recurses the error tree and adds one message per sub error. That list can
    get long, because jsonschema also tests the hypothesis that the provided
    network element type is wrong (e.g. "ovs_bridge" instead of "ovs_bond").
    Setting `filter_errors=True` assumes the type, if specified, is correct and
    therefore produces a much shorter list of more relevant results.
    """

    if not error.context:
        return []

    sub_errors = error.context
    if filter_errors:
        if (absolute_schema_path[-1] in ['oneOf', 'anyOf']
                and isinstance(error.instance, collections.Mapping)
                and 'type' in error.instance):
            found, index = _find_type_in_schema_list(
                error.validator_value, error.instance['type'])
            if found:
                sub_errors = [i for i in sub_errors if (
                              i.schema_path[0] == index)]

    details = []
    sub_errors = sorted(sub_errors, key=lambda e: e.schema_path)
    for sub_error in sub_errors:
        schema_path = collections.deque(absolute_schema_path)
        schema_path.extend(sub_error.schema_path)
        details.append("{} {}: {}".format(
            '-' * depth,
            _pretty_print_schema_path(schema_path, absolute_schema),
            sub_error.message)
        )
        details.extend(_get_detailed_errors(
            sub_error, depth + 1, schema_path, absolute_schema,
            filter_errors))
    return details


def _find_type_in_schema_list(schemas, type):
    """Finds an object of a given type in an anyOf/oneOf array.

    Returns a tuple (`found`, `index`), where `found` indicates whether
    on object of type `type` was found in the `schemas` array.
    If so, `index` contains the object's position in the array.
    """
    for index, schema in enumerate(schemas):
        if not isinstance(schema, collections.Mapping):
            continue
        if '$ref' in schema and schema['$ref'].split('/')[-1] == type:
            return True, index
        if ('properties' in schema and 'type' in schema['properties']
                and schema['properties']['type'] == type):
            return True, index
    return False, 0


def _pretty_print_schema_path(absolute_schema_path, absolute_schema):
    """Returns a representation of the schema path that's easier to read.

    For example:
    >>> _pretty_print_schema_path("items/oneOf/0/properties/use_dhcp/oneOf/2")
    "items/oneOf/interface/use_dhcp/oneOf/param"
    """

    pretty_path = []
    current_path = []
    current_schema = absolute_schema
    for item in absolute_schema_path:
        if item not in ["properties"]:
            pretty_path.append(item)
        current_path.append(item)
        current_schema = current_schema[item]
        if (isinstance(current_schema, collections.Mapping)
                and '$ref' in current_schema):
            if (isinstance(pretty_path[-1], int) and pretty_path[-2]
                    in ['oneOf', 'anyOf']):
                pretty_path[-1] = current_schema['$ref'].split('/')[-1]
            current_path = current_schema['$ref'].split('/')
            current_schema = absolute_schema
            for i in current_path[1:]:
                current_schema = current_schema[i]
    return '/'.join([str(x) for x in pretty_path])


def validate_json_schema(net_data):

    def ip_subnet_version_validator(validator, ip_version, instance, schema):
        msg = '{} does not appear to be an IPv{} subnet'.format(
            instance, ip_version)
        try:
            if not ipaddress.ip_network(instance).version == ip_version:
                yield jsonschema.ValidationError(msg)
        except ValueError:
            yield jsonschema.ValidationError(msg)

    def ip_address_version_validator(validator, ip_version, instance, schema):
        msg = '{} does not appear to be an IPv{} address'.format(
            instance, ip_version)
        try:
            if not ipaddress.ip_address(instance).version == ip_version:
                yield jsonschema.ValidationError(msg)
        except ValueError:
            yield jsonschema.ValidationError(msg)

    schema = yaml.safe_load(NET_DATA_V2_SCHEMA)
    net_data_validator = jsonschema.validators.extend(
        jsonschema.Draft4Validator,
        validators={'ip_subnet_version': ip_subnet_version_validator,
                    'ip_address_version': ip_address_version_validator})
    validator = net_data_validator(schema)
    errors = validator.iter_errors(instance=net_data)

    error_messages = []
    for error in errors:
        details = _get_detailed_errors(error, 1, error.schema_path, schema)

        config_path = '/'.join([str(x) for x in error.path])
        if details:
            error_messages.append(
                "Failed schema validation at {}:\n    {}\n"
                "  Sub-schemas tested and not matching:\n  {}".format(
                    config_path, error.message, '\n  '.join(details)))
        else:
            error_messages.append(
                "Failed schema validation at {}:\n    {}".format(
                    config_path, error.message))

    return error_messages
