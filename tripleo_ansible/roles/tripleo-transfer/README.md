tripleo-transfer
================

An Ansible role to files from one overcloud node to another one.

Optional:

* `tripleo_transfer_storage_root_dir` -- directory on the Ansible host
  under which all data is temporarily stored
  (defaults to "/var/lib/mistral/tripleo-transfer")
* `tripleo_transfer_storage_root_become` -- whether to use `become`
  when creating the storage root directory
  (defaults to false)
* `tripleo_transfer_src_become` -- whether to use `become`
  on the source host
  (defaults to true)
* `tripleo_transfer_dest_become` -- whether to use `become`
  on the destination host
  (defaults to true)
* `tripleo_transfer_dest_wipe` -- whether to wipe the destination
  directory before transferring the content
  (defaults to true)
