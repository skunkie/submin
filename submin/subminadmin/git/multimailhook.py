import os
import sys
import re

from submin.models import storage
from submin.models.user import User
from submin.models import options

# add to python_path so we can import git_multimail
LIBDIR = os.path.join(options.lib_path(), 'static/hooks/git')
sys.path.append(LIBDIR)

import git_multimail

FOOTER_TEMPLATE = """

--
This message was sent by Submin through git_multimail.
To unsubscribe from this commit list, please login to {http_vhost}{base_url} and change your preferences.
"""

class Config(git_multimail.Config):
	"""Allow overrides without having to write them everytime to git config"""
	overrides = {}

	def set_override(self, var, val):
		self.overrides[var] = val

	def get(self, var, *args, **kwargs):
		if var in self.overrides:
			return self.overrides[var]

		return super(Config, self).get(var, *args, **kwargs)


class SubminEnvironment(git_multimail.GenericEnvironment):
	def __init__(self, *args, **kwargs):
		storage.open()
		self._config = self._get_config()

		super(SubminEnvironment, self).__init__(config=self._config, *args, **kwargs)

	def __del__(self):
		storage.close()

	def _get_submin_vars(self):
		self.display_name = None
		self.email_address = None
		self.username = os.environ.get('SUBMIN_USERNAME')
		if not self.username:
			return

		user = User(self.username)
		self.email_address = user.email.encode('utf-8')
		self.display_name = user.fullname.encode('utf-8')

	def _get_config(self):
		self._get_submin_vars()
		config = Config('multimailhook')
		commit_email_from = options.value('commit_email_from',
				'please_configure_commit_email_from@example.org')
		if '<' in commit_email_from:
			commit_email_from = re.sub('.*<([^>]+)>', '\\1', commit_email_from)

		display_name = self.get_pusher()
		email = '{} <{}>'.format(display_name, commit_email_from)
		reply_to = '{} <{}>'.format(display_name, self.email_address)
		overrides = (
			('envelopesender', email),
			('from', email),
			('replyToRefchange', reply_to),
		)
		for var, val in overrides:
			config.set_override(var, val)

		return config

	def _set_footer():
		git_multimail.FOOTER_TEMPLATE = FOOTER_TEMPLATE.format(
			http_vhost=options.http_vhost(),
			base_url=options.url_path("base_url_submin"),
		)
		git_multimail.REVISION_FOOTER_TEMPLATE = git_multimail.FOOTER_TEMPLATE

	def get_pusher(self):
		return self.display_name or self.username

	def run(self):
		# If no e-mail recipients are configured, no need to continue. So ...
		if not self._config.get('mailinglist'):
			# ... either configure mailinglist ...
			if not self._config.get('refchangelist') or not config.get('commitlist'):
				# ... or both refchangelist and commitlist.
				return

		mailer = git_multimail.choose_mailer(self._config, self)
		git_multimail.run_as_post_receive_hook(self, mailer)


def run():
	SubminEnvironment().run()

