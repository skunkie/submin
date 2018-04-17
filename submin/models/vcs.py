from submin.bootstrap import fimport

class VCSException(Exception):
	pass

def get(vcstype, model):
	"""Gets the vcs-plugin for a certain type and model."""
	try:
		vcs_plugin = fimport("submin.plugins.vcs.%s.%s" % (vcstype, model),
			       "submin.plugins.vcs.%s" % vcstype)
	except ImportError as e:
		raise VCSException(e)

	return vcs_plugin

def export_auth_user():
	"""Export vcs-specific authorization/authentication information.
	For example, regenerate authz file for subversion HTTP access."""
	for vcstype in list():
		export_auth(vcstype, "user")

def export_auth_group():
	"""Export vcs-specific authorization/authentication information.
	For example, regenerate authz file for subversion HTTP access."""
	for vcstype in list():
		export_auth(vcstype, "group")

def export_auth_repository(vcstype):
	"""Export vcs-specific authorization/authentication information.
	For example, regenerate authz file for subversion HTTP access."""
	export_auth(vcstype, "repository")
	
def export_auth(vcstype, authtype):
	#try:
	vcs_plugin = fimport("submin.plugins.vcs.%s.%s" % (vcstype, "export"),
			   "submin.plugins.vcs.%s" % vcstype)
	#except ImportError as e:
	#	raise VCSException(e)

	vcs_plugin.export_auth(authtype)
