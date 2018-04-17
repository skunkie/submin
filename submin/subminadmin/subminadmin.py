import sys
import os
import os.path

from submin.path.path import Path
from submin.models import storage
from submin import __version__ as submin_version

from .common import SubminAdminCmdException

import code
_has_readline = True
try:
	import readline
except ImportError:
	_has_readline = False
import atexit
import os
import time

class HistoryConsole(code.InteractiveConsole):
    global _has_readline
    def __init__(self, locals=None, filename="<console>",
                 histfile=os.path.expanduser("~/.submin2-admin-history")):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.init_history(histfile)

    def init_history(self, histfile):
        if not _has_readline:
            return

        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        if not _has_readline:
            return

        readline.write_history_file(histfile)

class SubminAdmin:
	def __init__(self, argv):
		self.argv = argv
		self.prompt_fmt = "Submin [%s]> "
		self.prompt = ""
		self.quit = False
		self.cmd_aliases = [('?', 'help'), ('exit', 'quit')]
		self.storage_opened = False
		self._set_systemdirs()
		self.hc = HistoryConsole

	def __del__(self):
		if self.storage_opened:
			try:
				storage.close()
			except storage.StorageError:
				pass # this only happens if initenv is not called yet

	def ensure_storage(self):
		if not self.storage_opened:
			storage.open()
			self.storage_opened = True

	def run(self):
		if len(self.argv) < 2:
			self.usage()
			return False

		if self.argv[1] == 'help' and len(self.argv) == 2:
			self.argv.insert(1, '/')
			print("""
WARNING: assuming that 'help' is not the path to a submin environment. If
this is incorrect, please supply the full path name and retry. Continueing
with the help command for now.
""")
			self.usage()
			time.sleep(2)

		self.env = os.path.realpath(self.argv[1])
		if self.env[0] != os.path.sep:
			self.env = os.path.join(os.getcwd(), self.env)

		self.prompt = self.prompt_fmt % self.env

		# setup storage plugins
		os.environ['SUBMIN_ENV'] = self.env

		if len(self.argv) < 3:
			return self.interactive()

		return self.execute(self.argv[2:])

	def interactive(self):
		print '''Welcome to submin2-admin - Submin %s
Interactive Submin administration console.

Use '?' or 'help' for help on commands.
''' % (submin_version,)
		while not self.quit:
			try:
				argv = raw_input(self.prompt).split()
			except (EOFError, KeyboardInterrupt):
				print
				return

			try:
				self.execute(argv)
			except SubminAdminCmdException as e:
				# print the error and continue (interactive mode)
				print >>sys.stderr, str(e)

		return True

	def cmd_instance(self, cmd, argv, print_error=True):
		objname = "c_" + cmd
		try:
			X = __import__(objname, globals())
			instance = getattr(X, objname)(self, argv)
			return instance
		except (ImportError, AttributeError) as e:
			if print_error:
				print "Error while executing command %s:" % cmd, str(e)
			return None

	def commands(self):
		import glob
		import inspect
		import re

		basefile = inspect.getmodule(self).__file__
		basedir = os.path.dirname(basefile)
		pat = re.compile('c_(.*).py')
		cmds = []
		for f in glob.glob('%s/c_*.py' % basedir):
			fname = os.path.basename(f)
			cmd = re.search(pat, fname)
			cmds.append(cmd.group(1))

		cmds.sort()
		return cmds

	def cmd_alias(self, cmd):
		for tup in self.cmd_aliases:
			if tup[0] == cmd:
				return tup[1]

		return cmd

	def execute(self, argv):
		if len(argv) < 1:
			return False

		cmd = self.cmd_alias(argv[0])
		Class = self.cmd_instance(cmd, argv[1:])
		if not Class:
			print "Unknown command: %s" % ' '.join(argv)
			return False

		if not self.storage_opened:
			if not hasattr(Class, "needs_env") or Class.needs_env:
				if not os.path.exists(self.env):
					print 'environment does not exist, use initenv'
					return True

				self.ensure_storage()

		rc = Class.run()

		return rc

	def _set_systemdirs(self):
		basefile = Path(__file__)
		if not basefile.absolute:
			basefile = Path(os.getcwd()) + basefile
		# Basefile will contain <basedir>/lib/subminadmin/__init__.py
		subminadmin_basedir = basefile.dirname()
		basedir_lib = os.path.dirname(subminadmin_basedir)
		basedir = Path(basedir_lib) + 'static'
		basedir_www = basedir + 'www'
		self.basedir = basedir
		self.basedir_lib = Path(basedir_lib)
		self.basedir_www = basedir_www

	def usage(self):
		print("Submin %s" % (submin_version,))
		print "Usage: %s </path/to/projenv> [command [subcommand] [option]]" \
				% self.argv[0]
