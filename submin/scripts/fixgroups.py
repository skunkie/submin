# -*- coding: utf-8 -*-
#
# Fixes names of groups according to this naming convention: repo_branch_ro for READ ONLY access to repo/branch,
# repo_branch_rw for READ-WRITE access and repo_branch_no for NO ACCESS.
# Cyrillic characters are transliterated to latin characters according to "ГОСТ Р 52535.1-2006".
# Allowed characters in the path are a-z, A-Z, 0-9 and "-", all other characters are omitted.
# 
# How to run:
# submin2-admin /var/lib/submin/ shell "execfile('/usr/lib/python2.7/site-packages/submin/scripts/fixgroups.py')"
# submin2-admin /var/lib/submin/ shell "import sys; sys.argv = ['report', 'verbose']; execfile('/usr/lib/python2.7/site-packages/submin/scripts/fixgroups.py')"
from __future__ import print_function

import re
import sys
import submin.plugins.storage.sql.common as storage

from submin.models import group, permissions, user
from submin.models.repository import DoesNotExistError
from submin.models.exceptions import GroupExistsError, MemberExistsError, UnknownGroupError

# ГОСТ Р 52535.1-2006
ru_lat = {
	u"а":"a",
	u"б":"b",
	u"в":"v",
	u"г":"g",
	u"д":"d",
	u"е":"e",
	u"ё":"e",
	u"ж":"zh",
	u"з":"z",
	u"и":"i",
	u"й":"i",
	u"к":"k",
	u"л":"l",
	u"м":"m",
	u"н":"n",
	u"о":"o",
	u"п":"p",
	u"р":"r",
	u"с":"s",
	u"т":"t",
	u"у":"u",
	u"ф":"f",
	u"х":"kh",
	u"ц":"tc",
	u"ч":"ch",
	u"ш":"sh",
	u"щ":"shch",
	u"ы":"y",
	u"э":"e",
	u"ю":"iu",
	u"я":"ia",
	u"А":"A",
	u"Б":"B",
	u"В":"V",
	u"Г":"G",
	u"Д":"D",
	u"Е":"E",
	u"Ё":"E",
	u"Ж":"ZH",
	u"З":"Z",
	u"И":"I",
	u"Й":"I",
	u"К":"K",
	u"Л":"L",
	u"М":"M",
	u"Н":"N",
	u"О":"O",
	u"П":"P",
	u"Р":"R",
	u"С":"S",
	u"Т":"T",
	u"У":"U",
	u"Ф":"F",
	u"Х":"KH",
	u"Ц":"TC",
	u"Ч":"CH",
	u"Ш":"SH",
	u"Щ":"SHCH",
	u"Ы":"Y",
	u"Э":"E",
	u"Ю":"IU",
	u"Я":"IA"
}

not_allowed_characters = re.compile('[^a-zA-Z0-9\-\/]')
permission_to_name = {'rw': 'rw', 'r': 'ro', '': 'no'}
report = len(sys.argv) > 0 and 'report' in sys.argv
verbose = len(sys.argv) > 0 and 'verbose' in sys.argv
verboseprint = print if verbose else lambda *a, **k: None

groups = group.list(user.FakeAdminUser())

def get_correct_groupname(permission_by_group):
	"""Returns correct groupname"""
	permission = permission_to_name[permission_by_group['permission']]
	path = '%s%s' % (permission_by_group['repository'],
		permission_by_group['path'] if permission_by_group['path'] != '/' else '')
	path = path.lower()

	for key in ru_lat:
		path = path.replace(key, ru_lat[key])

	path = re.sub(not_allowed_characters, '', path)
	path = re.sub('/', '_', path)
	correct_groupname = '%s_%s' % (path, permission)

	return correct_groupname

for groupname in groups:
	permissions_by_group = list(permissions.list_by_group(groupname))

	if not permissions_by_group:
		verboseprint("Group %s is not used" % groupname)

		if report:
			continue

		group.Group(groupname).remove()
		verboseprint("Removed unused group %s" % groupname)
		continue

	permissions_to_groupname = []
	match = False  # Gets True when the name of a group matches its permission

	for permission_by_group in permissions_by_group:
		correct_groupname = get_correct_groupname(permission_by_group)
		if groupname == correct_groupname:
			match = True
		permissions_to_groupname.append((permission_by_group, groupname, correct_groupname))

	for ptg in permissions_to_groupname:
		permission_by_group, groupname, correct_groupname = ptg
		last = permissions_to_groupname.index(ptg) == len(permissions_to_groupname) - 1

		if groupname == correct_groupname:
			verboseprint("Groupname %s matches its permission" % groupname)
			continue

		verboseprint("Groupname %s mismatches its permission, its name should be %s" % (groupname, correct_groupname))

		if report:
			continue

		if not match and last:
			try:
				group.rename(groupname, correct_groupname)
				verboseprint("Renamed group %s to %s" % (groupname, correct_groupname))
				continue
			except GroupExistsError:
				verboseprint("Group %s already exists" % correct_groupname)

		try:
			correct_group = group.Group(correct_groupname)
		except UnknownGroupError:
			correct_group = group.add(correct_groupname)
			verboseprint("Created group %s" % correct_groupname)

		old_group = group.Group(groupname)
		members = list(old_group.members())
		for member in members:
			try:
				correct_group.add_member(user.User(member))
				verboseprint("Added %s to group %s" % (member, correct_groupname))
			except MemberExistsError:
				verboseprint("User %s is already a member of group %s" % (member, correct_groupname))

		params = [permission_by_group['repository'], permission_by_group['vcs'],
			permission_by_group['path'], correct_groupname, 'group', permission_by_group['permission']]
		try:
			permissions.add(*params)
			verboseprint("Added permission for group %s" % correct_groupname)
		except storage.SQLIntegrityError:
			permissions.change(*params)
			verboseprint("Changed permission for group %s" % correct_groupname)
		except DoesNotExistError as e:
			verboseprint("Path %s does not exist" % e)

		permissions.remove(permission_by_group['repository'], permission_by_group['vcs'],
			permission_by_group['path'], groupname, 'group')
		verboseprint("Removed permission for group %s" % groupname)

		if not match and last:
			old_group.remove()
			verboseprint("Removed group %s" % groupname)
