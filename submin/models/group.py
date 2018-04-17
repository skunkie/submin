from submin import models
from submin.hooks.common import trigger_hook
storage = models.storage.get("group")
from submin.models.exceptions import UnknownGroupError

def list(session_user):
	all_groups = [Group(raw_data=g) for g in storage.list()]
	groups = []
	for g in all_groups:
		if session_user.is_admin or session_user.name in g.members():
			groups.append(g.name)
	
	return groups

def add(name):
	"""Add a new, empty group"""
	storage.add(name)
	trigger_hook('group-create', groupname=name)
	return Group(name)

class Group(object):
	def __init__(self, groupname=None, raw_data=None):
		"""Constructor, either takes a groupname or raw data

		If groupname is provided, the storage is used to get the required data.
		If raw_data is provided, the storage is not used.
		"""
		db_group = raw_data

		if not raw_data:
			db_group = storage.group_data(groupname)
			if not db_group:
				raise UnknownGroupError(groupname)

		self._type = 'group' # needed for Manager
		self._id   = db_group['id']
		self._name = db_group['name']

	def __str__(self):
		return self.name

	def remove(self):
		oldmembers=self.members()
		storage.remove_permissions(self._id)
		storage.remove_managers(self._id)
		storage.remove_members_from_group(self._id)
		storage.remove(self._id)
		trigger_hook('group-delete', groupname=self._name, group_oldmembers=oldmembers)

	def members(self):
		return storage.members(self._id)

	def add_member(self, user):
		storage.add_member(self._id, user.id)
		trigger_hook('group-add-member', groupname=self._name, username=user.name)

	def remove_member(self, user):
		storage.remove_member(self._id, user.id)
		trigger_hook('group-delete-member', groupname=self._name, username=user.name)

	# Properties
	def _getId(self):
		return self._id

	def _getName(self):
		return self._name

	id   = property(_getId)   # id is read-only
	name = property(_getName) # name is read-only

__doc__ = """
Storage contract
================

Username is unique and primary key.

* list()
	Returns a sorted list of groups, sorted by groupname

* add(groupname)
	Adds a new group, raises `GroupExistsError` if there already is a group
	with this groupname

* group_data(groupname)
	Returns a dictionary with all required group data.
	Returns `None` if no group with this username exists.
	Fields which need to be implemented (with properties?): name
	
* remove(groupid)
	Removes group with id *groupid*. Before a group can be removed, all
	remove_-functions below must have been called. This happens in the model,
	so storage designers need not worry about this restriction.

* remove_permissions(groupid)
	Removes repository permissions for group with id *groupid*

* remove_managers(groupid)
	Removes group managers with id *groupid*

* remove_members_from_group(groupid)
	Removes all members of group with id *groupid*

* members(groupid)
	Returns a sorted itarable of membernames, sorted by username, for group
	with id *groupid*.

* add_member(groupid, userid)
	Adds the user with id *userid* to the group with id *groupid*. Can
	raise a MemberExistsError.

* remove_member(groupid, userid)
	Removes the user with id *userid* from the group with id *groupid*
"""
