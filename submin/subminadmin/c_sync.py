from submin.auth.external import external_sync
from submin.template.shortcuts import evaluate

class c_sync():
	'''Synchronize users with external group
Usage:
    sync         - synchronize users with external group, use it with cron
    sync verbose - synchronize and show errors, if any'''

	needs_env = True

	def __init__(self, sa, argv):
		self.sa = sa
		self.argv = argv

	def run(self):
		if len(self.argv) > 0 and self.argv[0] == 'verbose':		
			formatted = evaluate('external.sync.print', external_sync())
			print(formatted)
		else:
			external_sync()
