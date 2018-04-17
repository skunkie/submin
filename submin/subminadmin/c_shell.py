from submin.models.exceptions import StorageError

class c_shell():
	'''Use Python shell
Usage:
    shell - use Python shell for submin2-admin'''

	needs_env = False

	def __init__(self, sa, argv):
		self.sa = sa
		self.argv = argv

	def run(self):
		try:
			self.sa.ensure_storage()
		except StorageError:
			print "This module needs a submin environment"
			return
		import code
		import readline
		variables = globals().copy()
		variables.update(locals())
		shell = code.InteractiveConsole(variables)
		if len(self.argv) > 0:
			shell.runcode(self.argv[0])
		else:
			shell.interact(banner="Welcome to Python shell for submin2-admin")
