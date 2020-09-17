#!/usr/bin/python

try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from ansible.parsing.yaml.objects import AnsibleUnicode


class FilterModule(object):
    def filters(self):
        return {
            'range_list': self.range_list
        }

    # converts number list into range list.
    # here input parameter and return value as list
    # example: [12, 13, 14, 17] into ["12-14", "17"]
    def _convert_number_to_range_list(self, num_list):
        num_list.sort()
        range_list = []
        range_min = num_list[0]
        for num in num_list:
            next_val = num + 1
            if next_val not in num_list:
                if range_min != num:
                    range_list.append(str(range_min) + '-' + str(num))
                else:
                    range_list.append(str(range_min))
                next_index = num_list.index(num) + 1
                if next_index < len(num_list):
                    range_min = num_list[next_index]

        # here, range_list is a list of strings
        return range_list

    def range_list(self, num_list):
        if not num_list:
            msg = "Input param 'num_list' is blank."
            raise tc.DeriveParamsError(msg)
        try:
            # splitting a string (comma delimited list) into
            # list of numbers
            # example: "12,13,14,17" string into [12,13,14,17]
            num_list = [int(num.strip(' '))
                        for num in num_list.split(",")]
        except ValueError as exc:
            msg = ("Invalid number in input param "
                   "'num_list': %s" % exc)
            raise tc.DeriveParamsError(msg)

        range_list = self._convert_number_to_range_list(num_list)

        # converts into comma delimited range list as string
        return ','.join(range_list)
