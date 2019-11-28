#!/usr/bin/python
import binascii

from ansible.parsing.yaml.objects import AnsibleUnicode


class FilterModule(object):
    def filters(self):
        return {
            'cpu_mask': self.cpu_mask
        }

    # Calculate the cpu mask for the list of CPUs
    # Example - for input of 1,13 the mask would be 2002
    def cpu_mask(self, cpu_list):
        mask = 0
        cpus = []
        for cpu in cpu_list.split(','):
            if '-' in cpu:
                rng = cpu.split('-')
                cpus.extend(range(int(rng[0]), int(rng[1]) + 1))
            else:
                cpus.append(int(cpu))
        cpus.sort()
        max_val = int(cpus[-1])
        byte_arr = bytearray(int(max_val / 8) + 1)

        for item in cpus:
            pos = int(int(item) / 8)
            bit = int(item) % 8
            byte_arr[pos] |= 2**bit

        byte_arr.reverse()
        mask = binascii.hexlify(byte_arr)
        return mask.decode("utf-8").lstrip("0")
