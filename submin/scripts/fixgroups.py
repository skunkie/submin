# -*- coding: utf-8 -*-
# submin2-admin /var/lib/submin/ shell "execfile('/usr/lib/python2.7/site-packages/submin/scripts/fixgroups.py')"
# submin2-admin /var/lib/submin/ shell "import sys; sys.argv = ['report']; execfile('/usr/lib/python2.7/site-packages/submin/scripts/fixgroups.py')"

import re
import sys
import submin.plugins.storage.sql.common as storage

from submin.models import group, permissions, user
from submin.models.repository import DoesNotExistError
from submin.models.exceptions import GroupExistsError, MemberExistsError, UnknownGroupError

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

groups = group.list(user.FakeAdminUser())

for groupname in groups:
	permissions_by_group = list(permissions.list_by_group(groupname))

	if not permissions_by_group:

		if len(sys.argv) > 0 and sys.argv[0] == 'report':
			print "Group %s is not used" % groupname
			continue

		group.Group(groupname).remove()
		print "Removed unused group %s" % groupname
		continue

	for pbg in permissions_by_group:
		permission = {'rw': 'rw', 'r': 'ro', '': 'no'}[pbg['permission']]
		path = '%s%s' % (pbg['repository'], pbg['path'] if pbg['path'] != '/' else '')
		path = path.lower()

		for key in ru_lat:
			path = path.replace(key, ru_lat[key])

		path = re.sub(not_allowed_characters, '', path)
		path = re.sub('/', '_', path)

		correct_groupname = '%s_%s' % (path, permission)

		if groupname != correct_groupname:
			print "Groupname %s mismatches its permission, its name should be %s" % (groupname, correct_groupname)

			if len(sys.argv) > 0 and sys.argv[0] == 'report':
				continue

			if permissions_by_group.index(pbg) == len(permissions_by_group) - 1:
				try:
					group.rename(groupname, correct_groupname)
					print "Renamed group %s to %s" % (groupname, correct_groupname)
					continue
				except GroupExistsError:
					print "Group %s already exists" % correct_groupname

			try:
				correct_group = group.Group(correct_groupname)
			except UnknownGroupError:
				correct_group = group.add(correct_groupname)
				print "Created group %s" % correct_groupname

			old_group = group.Group(groupname)
			members = list(old_group.members())
			for member in members:
				try:
					correct_group.add_member(user.User(member))
					print "Added %s to group %s" % (member, correct_groupname)
				except MemberExistsError:
					print "User %s is already a member of group %s" % (member, correct_groupname)
					pass

			params = [pbg['repository'], pbg['vcs'], pbg['path'], correct_groupname, 'group', pbg['permission']]
			try:
				permissions.add(*params)
				print "Added permission for group %s" % correct_groupname
			except storage.SQLIntegrityError:
				permissions.change(*params)
				print "Changed permission for group %s" % correct_groupname
			except DoesNotExistError as e:
				print "Path %s does not exist" % e

			if permissions_by_group.index(pbg) == len(permissions_by_group) - 1:
				old_group.remove()
				print "Removed group %s" % groupname
