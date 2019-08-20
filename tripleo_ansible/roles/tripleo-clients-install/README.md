# tripleo-clients-install

Installs openstack clients packages


## Role Variables
### Common variables
- tripleo_clients_install_python_prefix: package prefix
```YAML
tripleo_clients_install_python_prefix: python3
```

### main task
- tripleo_clients_install_dict: hash listing the different client and package
  state:
```YAML
tripleo_clients_install_dict:
  aodh: present
  barbican: absent
```

### install_pkgs task
- tripleo_clients_install_client: client name you want to manage
```YAML
tripleo_clients_install_client: aodh
```
- tripleo_clients_install_pkg_state: package state you want
```YAML
tripleo_clients_install_pkg_state: present
```
