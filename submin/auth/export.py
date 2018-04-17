import os

from submin.models import options
from submin.models import user
from submin.models.user import FakeAdminUser
from submin.models.exceptions import UnknownKeyError

def export_htpasswd(*args, **kwargs):
	try:
		htpasswd_file = options.env_path("htpasswd_file")
	except UnknownKeyError:
		return

	if not os.path.exists(htpasswd_file.dirname()):
		return

	with open(htpasswd_file, "w+") as htpasswd:
		for username in user.list(FakeAdminUser()):
			u = user.User(username)
			encoded_username = username.encode('utf-8')
			encoded_password = u.get_password_hash().encode('utf-8')
			htpasswd.write("%s:%s\n" % (encoded_username, encoded_password))

	os.chmod(htpasswd_file, 0o600)
