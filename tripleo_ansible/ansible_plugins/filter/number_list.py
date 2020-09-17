#!/usr/bin/python

try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from ansible.parsing.yaml.objects import AnsibleUnicode


class FilterModule(object):
    def filters(self):
        return {
            'number_list': self.number_list
        }

    # converts range list into number list
    # here input parameter and return value as list
    # example: ["12-14", "^13", "17"] into [12, 14, 17]
    def convert_range_to_number_list(self, range_list):
        num_list = []
        exclude_num_list = []
        try:
            for val in range_list:
                val = val.strip(' ')
                if '^' in val:
                    exclude_num_list.append(int(val[1:]))
                elif '-' in val:
                    split_list = val.split("-")
                    range_min = int(split_list[0])
                    range_max = int(split_list[1])
                    num_list.extend(range(range_min, (range_max + 1)))
                else:
                    num_list.append(int(val))
        except ValueError as exc:
            msg = ("Invalid number in input param "
                   "'range_list': %s" % exc)
            raise tc.DeriveParamsError(msg)

        # here, num_list is a list of integers
        return [num for num in num_list if num not in exclude_num_list]

    def number_list(self, range_list):
        try:
            if not range_list:
                msg = "Input param 'range_list' is blank."
                raise Exception(msg)
            range_list = range_list
            # converts into python list if range_list is not list type
            if not isinstance(range_list, list):
                range_list = range_list.split(",")

            num_list = self.convert_range_to_number_list(range_list)
        except Exception as err:
            msg = ('Derive Params Error: %s', err)
            raise tc.DeriveParamsError(msg)

        # converts into comma delimited number list as string
        return ','.join([str(num) for num in num_list])
