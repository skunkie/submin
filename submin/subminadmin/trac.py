import errno
from submin.models import trac

def trac_admin_command(trac_dir, args):
	try:
		trac.admin_command(trac_dir, args)
	except trac.TracAdminError as e:
		print "Trac command '%s' failed with exitcode %s" % (e.cmd, e.exitstatus)
		print 'Error message:'
		print e.outtext
		raise

def deploy(trac_dir, deploy_dir):
	trac_admin_command(trac_dir, ['deploy', deploy_dir])

def exists():
	return trac.has_trac_admin()

def initenv(trac_dir, trac_name, vcs_type, vcs_path):
	trac_admin_command(trac_dir, ['initenv', trac_name,
		'sqlite:db/trac.db', vcs_type, vcs_path
	])
