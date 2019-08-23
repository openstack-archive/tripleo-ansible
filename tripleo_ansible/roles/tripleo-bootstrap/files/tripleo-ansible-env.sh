function set-ansible-env {
    export ANSIBLE_RETRY_FILES_ENABLED=False
    export ANSIBLE_ACTION_PLUGINS="${HOME}/.ansible/plugins/action:/usr/share/ansible/plugins/action:/usr/share/ansible/tripleo-plugins/action:/usr/share/openstack-tripleo-validations/action"
    export ANSIBLE_CALLBACK_PLUGINS="${HOME}/.ansible/plugins/callback:/usr/share/ansible/plugins/callback:/usr/share/ansible/tripleo-plugins/callback:/usr/share/openstack-tripleo-validations/callback"
    export ANSIBLE_FILTER_PLUGINS="${HOME}/.ansible/plugins/filter:/usr/share/ansible/plugins/filter:/usr/share/ansible/tripleo-plugins/filter:/usr/share/openstack-tripleo-validations/filter"
    export ANSIBLE_LIBRARY="${HOME}/.ansible/plugins/modules:/usr/share/ansible/plugins/modules:/usr/share/ansible/tripleo-plugins/modules:/usr/share/openstack-tripleo-validations/modules"
    export ANSIBLE_MODULE_UTILS="${HOME}/.ansible/plugins/module_utils:/usr/share/ansible/plugins/module_utils:/usr/share/ansible/tripleo-plugins/module_utils:/usr/share/openstack-tripleo-validations/module_utils"
    export ANSIBLE_ROLES_PATH="${HOME}/.ansible/roles:/usr/share/ansible/tripleo-roles:/usr/share/ansible/roles:/etc/ansible/roles:/usr/share/openstack-tripleo-validations/roles"
    export ANSIBLE_LOOKUP_PLUGINS="${HOME}/.ansible/plugins/lookup:/usr/share/ansible/plugins/lookup:/usr/share/ansible/tripleo-plugins/lookup:/usr/share/openstack-tripleo-validations/lookup"
    export ANSIBLE_LOAD_CALLBACK_PLUGINS=True
    export ANSIBLE_HOST_KEY_CHECKING=False
    export ANSIBLE_LOG_PATH="${HOME}/.ansible/logs/ansible-$(date +"%Y-%m-%dT%H").log"
    export ANSIBLE_FORKS=25
    export ANSIBLE_TIMEOUT=30
    export ANSIBLE_GATHER_TIMEOUT=30
    export ANSIBLE_SSH_ARGS="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=30m -o ServerAliveInterval=5 -o ServerAliveCountMax=5"
    export ANSIBLE_PIPELINING=True
    export ANSIBLE_SSH_RETRIES=8
}

function unset-ansible-env {
    for i in $(env | grep ANSIBLE_ | awk -F'=' '{print $1}'); do
        unset ${i}
    done
    echo -e "\nAnsible environment deactivated."
    echo -e "To re-activate the environment, run 'set-ansible-env'.\n"
}

set-ansible-env
