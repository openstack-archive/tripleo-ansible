# TripleO Create Admin #

A role to create an admin user to be later used for running playbooks.

## Role Variables ##

| Name              | Default Value       | Description           |
|-------------------|---------------------|-----------------------|
| `tripleo_admin_user` | `tripleo-admin`     | Name of user to create|
| `tripleo_admin_pubkey` | `[undefined]`     | Public key for authorization|

## Requirements ##

 - ansible >= 2.4
 - python >= 2.6
