import unittest
import shutil # for temporary dir
import tempfile # for temporary dir
from mock import Mock

mock_settings = Mock()
mock_settings.storage = "sql"
mock_settings.sqlite_path = ":memory:"
mock_settings.base_dir = "/"

from submin.bootstrap import setSettings
setSettings(mock_settings)

from submin.models import storage
from submin.models import user
from submin.models import group
from submin.models import options
from submin.path.path import Path
from submin.models.exceptions import UserExistsError, UnknownUserError, UserPermissionError
from submin.models.validators import *
from submin.models.repository import Repository
from submin.models import permissions

import tempfile
import shutil
import os

class UserTests(unittest.TestCase):
	def setUp(self):
		self.submin_env = Path(tempfile.mkdtemp(prefix='submin-unittest'))
		conf_dir = self.submin_env + 'conf'
		svn_dir = self.submin_env + 'svn'
		os.mkdir(conf_dir)
		os.mkdir(svn_dir)
		mock_settings.base_dir = self.submin_env
		storage.open(mock_settings)
		storage.database_evolve()
		options.set_value('svn_authz_file', conf_dir + 'authz') # needed for export
		options.set_value('svn_dir', svn_dir) # needed for export
		options.set_value('git_dir', self.submin_env + 'git')
		options.set_value('vcs_plugins', 'svn, git')
		self.tmp_dirs = []
		user.add("test", email="a@a.a", password="x")
		self.u = user.User("test")

	def tearDown(self):
		self.u.remove()
		storage.close()
		shutil.rmtree(self.submin_env)

	def addRepository(self, reposname, vcstype):
		from submin.models.user import FakeAdminUser
		Repository.add(vcstype, reposname, FakeAdminUser())

	def setEmail(self, u, email):
		u.email = email

	def setUsername(self, u, username):
		u.name = username

	def setFullname(self, u, fullname):
		u.fullname = fullname

	def testEmailSingleQuoteInvalid(self):
		self.assertRaises(InvalidEmail, self.setEmail, self.u, "a'@example.com")

	def testEmailDoubleQuoteInvalid(self):
		self.assertRaises(InvalidEmail, self.setEmail, self.u, 'a"@example.com')

	def testEmailDoubleDot(self):
		self.assertRaises(InvalidEmail, self.setEmail, self.u, "a@example..com")

	def testEmailDoubleAt(self):
		self.assertRaises(InvalidEmail, self.setEmail, self.u, "a@@example.com")

	def testEmailSimple(self):
		e = "a@a.a"
		self.u.email = e
		self.assertEquals(e, self.u.email)

	def testEmailEndingDotOk(self):
		e = "a@a.a."
		self.u.email = e
		self.assertEquals(e, self.u.email)

	def testEmailIPAddressOK(self):
		e = "a@999.999.999.999"
		self.u.email = e
		self.assertEquals(e, self.u.email)

	def testEmailUserPlusOk(self):
		e = "a+b@example.com"
		self.u.email = e
		self.assertEquals(e, self.u.email)

	def testPassword(self):
		self.u.set_password("foobar")
		self.assertTrue(self.u.check_password("foobar"))

	def testAddDoubleUser(self):
		self.assertRaises(UserExistsError, user.add, "test", "a@a.a", "x")

	def testUnknownUser(self):
		self.assertRaises(UnknownUserError, user.User, "not a user")

	def testUserName(self):
		self.assertEquals(str(self.u), "test")

	def testNotAdmin(self):
		self.assertRaises(UserPermissionError, self.u.set_notifications,
			[{'name': 'repos', 'vcs': 'git', 'enabled': True}], self.u)

	def testListUsersAdmin(self):
		mock_user = Mock()
		mock_user.is_admin = True
		user.add("foo", email="a@a.a", password="x")
		users = sorted([x for x in user.list(mock_user)])
		self.assertEquals(users, ["foo", "test"])

	def testListUsersNonAdmin(self):
		mock_user = Mock()
		mock_user.is_admin = False
		mock_user.name = "foo"
		user.add("foo", email="a@a.a", password="x")
		users = sorted([x for x in user.list(mock_user)])
		self.assertEquals(users, ["foo"])

	def testRemoveUser(self):
		mock_user = Mock()
		mock_user.is_admin = True
		user.add("foo", email="a@a.a", password="x")
		foo = user.User("foo")
		foo.remove()
		self.assert_("foo" not in [x for x in user.list(mock_user)])

	def testUserName(self):
		self.assertEquals(self.u.name, "test")

	def testSetUserName(self):
		self.u.name = "foo"
		self.assertEquals(self.u.name, "foo")

	def testInvalidUserName(self):
		invalid_chars = '\'"\n'
		for invalid_char in invalid_chars:
			self.assertRaises(InvalidUsername, self.setUsername, self.u,
					invalid_char)

	def testFullName(self):
		expected_full_name = "Full Name"
		self.u.fullname = expected_full_name
		self.assertEquals(self.u.fullname, expected_full_name)

	def testInvalidFullName(self):
		invalid_chars = '\'"\n'
		for invalid_char in invalid_chars.split():
			self.assertRaises(InvalidFullname, self.setFullname, self.u,
					invalid_char)

	def testSetIsAdmin(self):
		self.assertFalse(self.u.is_admin)
		self.u.is_admin = True
		self.assertTrue(self.u.is_admin)
		self.u.is_admin = False
		self.assertFalse(self.u.is_admin)

	def testSaveNotificationsAdmin(self):
		self.addRepository('repos', 'svn') # otherwise, we cannot add notifications
		mock_admin = Mock()
		mock_admin.is_admin = True
		self.u.set_notifications([
				{'name': 'repos', 'vcs': 'svn', 'enabled': True},
				{'name': 'non-existing', 'vcs': 'svn', 'enabled': True}
			], mock_admin)
		notifications = self.u.notifications()
		self.assertFalse('non-existing' in notifications)
		u2 = user.User("test")
		notifications = u2.notifications()
		self.assertFalse('repos' in notifications)

	def testSaveNotificationsNonAdminNotAllowed(self):
		"""If not allowed, should raise Exception"""
		# default permissions are set to false
		self.assertRaises(UserPermissionError, self.u.set_notifications,
			[{'name': 'repos', 'vcs': 'svn', 'enabled': True}], self.u)

	def testSaveNotificationsNonAdminAllowed(self):
		"""First set allowed as admin, then set enabled as user"""
		self.addRepository('repos', 'svn') # otherwise, we cannot add notifications
		permissions.add('repos', 'svn', '/', self.u.name, 'user', 'r')
		self.u.set_notifications([{'name': 'repos', 'vcs': 'svn', 'enabled': True}], self.u)
		notifications = self.u.notifications()
		self.assertTrue(notifications["repos"]["enabled"])

	def testNotificationWithEmptyPermission(self):
		self.addRepository('repos', 'svn')
		permissions.add('repos', 'svn', '/', self.u.name, 'user', '')
		self.assertRaises(UserPermissionError, self.u.set_notifications,
			[{'name': 'repos', 'vcs': 'svn', 'enabled': True}], self.u)

	def testNotificationWithEmptyGroupPermission(self):
		self.addRepository('repos', 'svn')
		group.add('untrusted')
		untrusted = group.Group('untrusted')
		untrusted.add_member(self.u)
		permissions.add('repos', 'svn', '/', 'untrusted', 'group', '')
		self.assertRaises(UserPermissionError, self.u.set_notifications,
			[{'name': 'repos', 'vcs': 'svn', 'enabled': True}], self.u)
		n = self.u.notifications()
		self.assertEquals(n, {})

if __name__ == "__main__":
	unittest.main()
