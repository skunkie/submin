import ldap
from submin.models import options
from submin.models.validators import *

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
ldap.protocol_version = ldap.VERSION3

def external_sync():
	"""Synchronizes external users"""
	from submin.models import user

	errormsgs = []
	if options.value('enabled_external', 'no') == 'no':
		errormsgs.append('external is not enabled')
		return {'errormsgs': errormsgs, 'success': False}

	group = LDAPGroup(options.value('external_passwd'), options.value('external_user'))
	if not group:
		errormsgs.append('cannot connect to LDAP server')
		return {'errormsgs': errormsgs, 'success': False}

	group_members = group.members
	if not group_members:
		errormsgs.append('cannot find LDAP group or its members')
		return {'errormsgs': errormsgs, 'success': False}

	user_list = user.list(user.FakeAdminUser())

	for username in group_members:
		email = group_members[username]['email']
		fullname = group_members[username]['fullname']

		if not validate_username(username):
			errormsgs.append(InvalidUsername(username))
			continue

		if not validate_email(email):
			errormsgs.append(InvalidEmail(email))
			continue

		if not validate_fullname(fullname):
			errormsgs.append(InvalidFullname(fullname))
			fullname = username

		if username not in user_list:  # A new user
			user.add(username=username, email=email, send_mail=False)
			user.User(username).fullname = fullname
		else:
			u = user.User(username)  # Update fullname and email if necessary
			if (u.email, u.fullname) != (email, fullname):
				u.email = email
				u.fullname = fullname

	return {'errormsgs': errormsgs, 'success': True}

class LDAPGroup(object):
	def __init__(self, username, password):
		self._con = None
		self._members = {}
		self._connect(username, password)

	def _connect(self, username, password):
		"""Returns True if connection to the LDAP server using the given credentials is successful"""
		try:
			self._con = ldap.initialize(options.value('external_server', ''))
			self._con.simple_bind_s('%s@%s' % (username, options.value('external_upn_suffix', '')), password)
		except ldap.INVALID_CREDENTIALS as e:
			self._con.unbind_s()
			self._con = None
		except ldap.LDAPError as e:
			self._con = None

	def _find_member(self, group, recursive=False):
		"""Finds members of a group. If it is a group, find its members, etc."""
		if 'member' in group:
			for m in group['member']:
				s = self._con.search_s(m, ldap.SCOPE_BASE)[0][1]
				if 'group' in s['objectClass'] and recursive:
					self._find_member(s)
				elif 'user' in s['objectClass']:
					sAMAccountName = s['sAMAccountName'][0]
					if sAMAccountName not in self._members:
						self._members.update(
							{sAMAccountName: {'fullname': s.get('cn', [''])[0], 'email': s.get('mail', [''])[0]}})
				else:
					continue

	def _get_members(self):
		"""Returns members of the LDAP group"""
		if self._con:
			try:
				group = self._con.search_s(options.value('external_group_dn', ''), ldap.SCOPE_BASE)[0][1]
				self._find_member(group)
			except ldap.NO_SUCH_OBJECT as e:
				self._con.unbind_s()

		return self._members
	
	members = property(_get_members)
