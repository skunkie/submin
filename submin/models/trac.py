import os
import errno
import subprocess

from submin.models import options
from submin.models.exceptions import MissingConfig
from submin.common.execute import check_output
from submin.common.osutils import mkdirs

class TracAdminError(Exception):
	def __init__(self, cmd, exitstatus, outtext):
		self.cmd = cmd
		self.exitstatus = exitstatus
		self.outtext = outtext
		Exception.__init__(self,
				"trac-admin '%s' exited with exit status %d. Output from the command: %s" % \
				(cmd, exitstatus, outtext))

def create(vcs_type, reposname, adminUser):
	from submin.models.repository import directory as repodir
	basedir = options.env_path('trac_dir')
	mkdirs(str(basedir))

	tracenv = basedir + reposname
	projectname = reposname
	vcsdir = repodir(vcs_type, reposname)

	admin_command(tracenv,
			['initenv', projectname, 'sqlite:db/trac.db', vcs_type, vcsdir])
	admin_command(tracenv, ['permission', 'add', adminUser.name, "TRAC_ADMIN"])

	components = [
		'tracopt.ticket.commit_updater.*',
		'tracopt.versioncontrol.%s.*' % vcs_type
	]

	for component in components:
		admin_command(tracenv,
			['config', 'set', 'components', component, 'enabled'])

	admin_command(tracenv, ['config', 'set', 'header_logo', 'alt', 'Trac'])
	admin_command(tracenv, ['config', 'set', 'header_logo', 'height', '61'])
	admin_command(tracenv, ['config', 'set', 'header_logo', 'link', "%s/%s" % (options.value('base_url_trac'), reposname)])
	admin_command(tracenv, ['config', 'set', 'header_logo', 'src', 'trac_banner.png'])
	admin_command(tracenv, ['config', 'set', 'header_logo', 'width', '214'])
	admin_command(tracenv, ['config', 'set', 'project', 'descr', 'Repository %s' % reposname])
	admin_command(tracenv, ['config', 'set', 'svn', 'authz_file', options.env_path('svn_authz_file')])
	admin_command(tracenv, ['config', 'set', 'svn', 'authz_module_name', reposname])
	admin_command(tracenv, ['config', 'set', 'trac', 'authz_file', options.env_path('svn_authz_file')])
	permission_policies = admin_command(tracenv, ['config', 'get', 'trac', 'permission_policies'])
	admin_command(tracenv, ['config', 'set', 'trac', 'permission_policies', 'AuthzSourcePolicy,' + permission_policies])
	admin_command(tracenv, ['config', 'set', 'trac', 'repository_dir', vcsdir])

def admin_command(trac_dir, args):
	"""trac_dir is the trac env dir, args is a list of arguments to trac-admin"""
	cmd = ['trac-admin', trac_dir]
	cmd.extend(args)
	path = options.value('env_path', "/bin:/usr/bin:/usr/local/bin:/opt/local/bin")
	env_copy = os.environ.copy()
	env_copy['PATH'] = path

	try:
		return check_output(cmd, stderr=subprocess.STDOUT, env=env_copy)
	except subprocess.CalledProcessError as e:
		raise TracAdminError(' '.join(cmd), e.returncode, e.output)

def has_trac_admin():
	try:
		admin_command('/tmp', ['help'])
	except OSError as e:
		if e.errno == errno.ENOENT: # could not find executable
			return False
		raise

	return True

def exists(name):
	try:
		return os.path.isdir(str(options.env_path('trac_dir') + name))
	except UnknownKeyError as e:
		raise MissingConfig('Please make sure "trac_dir" is set in the config')
