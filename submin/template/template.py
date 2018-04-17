import re
import os
import sys
import string

from submin.unicode import uc_str
from .library import Library

class UnknownCommandError(Exception):
	pass

class TemplateKeyError(Exception):
	pass

class InvalidKeyError(Exception):
	pass

class Node(object):
	"""Represents a piece of template-text.
	This is the most basic node and basically does not convey meaning."""
	
	def __init__(self, type, previous_node, line):
		self.type = type
		self.previous_node = previous_node
		self.line = line
		
		self.nodes = []
		self.suppress_newline = False
	
	def evaluate(self, template=None):
		"""Even the most basic node has a evaluate function, although it 
		returns an empty string.
		Subclasses of Node must implement their own evaluate function, to 
		ensure a template is evaluated completely"""
		return ''
		
	def __str__(self):
		return '<%s>' % (self.type)
	
	def __repr__(self):
		return str(self)

class TextNode(Node):
	"""Represents only text, usually HTML."""
	def __init__(self, content, previous_node, line):
		super(TextNode, self).__init__('text', previous_node, line)
		self.content = content
	
	def evaluate(self, template=None):
		content = self.content
		pn = self.previous_node
		newline = len(content) and content[0] == '\n'
		if pn and pn.suppress_newline and newline:
			content = content[1:]

		return unicode(content)
	
	def __str__(self):
		return '<text %r>' % self.content

class CommandNode(Node):
	"""Represents a command.
	A command can have arguments and/or input-text (both optional). 
	The syntax is: [command:arguments input-text].
	The input-text can also contain commands, which are not evaluated unless
	the corresponding command does so.
	"""
	def __init__(self, command, previous_node, line):
		super(CommandNode, self).__init__('command', previous_node, line)
		self.command = command
		self.arguments = ''
	
	def evaluate(self, template):
		library = Library()
		if library.has_command(self.command):
			try:
				value = library.execute(self, template)
			except TemplateKeyError:
				raise InvalidKeyError('Invalid key at %s:%s node %s' %
							(template.filename, self.line, str(self)))

			# int/bool/float values can't be joined with unicode strings, so coerce
			# to str (faster than unicode and gives no problems with encoding)
			if hasattr(value, '__int__'):
				return str(value)
			# coerce anything else to unicode
			try:
				return unicode(value)
			except UnicodeDecodeError:
				return unicode(value, 'utf-8')
		raise UnknownCommandError(self.command)
	
	def __str__(self):
		if self.arguments:
			return '<cmd %s(%s)>' % (self.command, self.arguments)
		return '<cmd %s>' % (self.command)

ESCAPE, COMMAND, ARGUMENTS = range(3)
class Parser(object):
	"""A Parser takes a template-string and creates a tree of nodes.
	"""
	def __init__(self, template):
		self.template = template
		self.stack = []
		self.open_cmds = 0
		self.state = None
		self.data = ''
		self.lines = 1

	def parse(self):
		previous_node = None
		for ch in self.template:
			if self.state == ESCAPE:
				# always leave ESCAPE state the next character
				self.state = prev_state
				self.data += ch
			elif ch == '\\' and self.state != ESCAPE:
				prev_state = self.state
				self.state = ESCAPE
			elif ch == '[':
				# Add new CommandNode to the stack

				if not self.state and self.data:
					# But first, do some text cleaning-up!
					text = TextNode(self.data, previous_node, self.lines)
					previous_node = text
					self.data = ''
					if self.open_cmds:
						self.stack[-1].nodes.append(text)
					else:
						self.stack.append(text)

				self.state = COMMAND
				cmd = CommandNode('', previous_node, self.lines)
				self.stack.append(cmd)
				self.open_cmds += 1
				previous_node = cmd
			elif (ch.isspace() or ch in (':', '.')) and self.state == COMMAND:
				# Represents the end of the command-section. Set the node's
				# command-name.
				# The : and . characters also represent the beginning of the
				# argument-section of the command.
				command = self.data
				if len(command) > 0 and command[0] == '@':
					command = command[1:]
					self.stack[-1].suppress_newline = True
				self.stack[-1].command = command
				self.data = ''
				if ch in (':', '.'):
					self.state = ARGUMENTS
				else:
					self.state = None
			elif ch == '.' and self.state == ARGUMENTS:
				# Ignore subsequent dots, add them to the arguments
				self.data += ch
			elif ch.isspace() and self.state == ARGUMENTS:
				# End of the arguments section, fill in the arguments of the
				# node
				self.stack[-1].arguments = self.data
				self.data = ''
				self.state = None
			elif ch == ']':
				# The end of a command. Now there is some heavy stuff that 
				# needs to be done:
				if self.data and not self.state == COMMAND \
						and not self.state == ARGUMENTS:
					# Add a TextNode to the CommandNode with the remaining
					# character-data
					text = TextNode(self.data, previous_node, self.lines)
					previous_node = text
					self.data = ''
					self.stack[-1].nodes.append(text)

				if self.state == COMMAND:
					# The command has no character-data, but we need to
					# finish the command-section
					self.stack[-1].command = self.data
					self.data = ''
				elif self.state == ARGUMENTS:
					# The command has no character data, but we need to
					# finish the arguments-section
					self.stack[-1].arguments = self.data
					self.data = ''

				self.open_cmds -= 1

				if self.open_cmds:
					# The current CommandNode is embedded in another command.
					# We need to add this node to the other Node.
					node = self.stack.pop()

					# Fix the previous node in embedded context.
					if self.stack[-1].nodes:
						node.previous_node = self.stack[-1].nodes[-1]
					else:
						node.previous_node = self.stack[-1]

					# Add the node to the other's node-stack
					self.stack[-1].nodes.append(node)
					previous_node = node
				else:
					previous_node = self.stack[-1]

				self.state = None
			else:
				# Just character data!
				self.data += ch

			if ch == '\n':
				# Keep track of where we are in the file!
				self.lines += 1
	
		if self.data:
			# If we have some data left at the end of the template, create
			# a TextNode for it.
			self.stack.append(TextNode(self.data, previous_node, self.lines))
		return self.stack

class Template(object):
	def __init__(self, template, variables={}):
		if hasattr(template, 'readlines'):
			self.template_string = uc_str(''.join(template.readlines()), 'utf-8')
			self.filename = template.name
		else:
			self.template_string = template
			self.filename = 'string'
		self.variables = variables.copy()
		self.node_variables = {}
		
		parser = Parser(self.template_string)
		self.nodes = parser.parse()
	
	def __del__(self):
		self.template_string = None
		self.variables = None
		self.node_variables = None
		self.nodes = None
	
	def parse_tree(self):
		"""Returns the parse tree as a string"""
		return '\n'.join([str(x) for x in self.nodes])

	def evaluate(self):
		"""Returns the evaluated template as a string"""
		return ''.join([node.evaluate(self) for node in self.nodes])

	def variable_value(self, key='', attr=None, variable=None, recursing=False):
		"""Looks up a key in a variable.
		If the variable is not provided, it is found in self.variables
		if key is in the form of key.attribute, the attribute value of key is 
		returned. 
		
		It first tries if attribute is a function and returns the return value
		of that function. Secondly it tries if attribute is a dictionary key
		and returns it's value. Thirdly it tries if attribute is a data-member
		and returns it. Next it checks if attribute is a digit, for a 
		list-lookup.
		If that that all fails, it returns None.
		"""
		if '.' in key:
			key, attr = key.split('.', 1)
		if variable is None or recursing:
			if variable is None:
				variable = self.variables
			if key not in variable and key not in self.node_variables:
				return None
			if key in self.node_variables:
				variable = self.node_variables[key][-1]
			else:
				variable = variable.get(key, None)
		
		# No attribute, just return the variable
		if not attr:
			return variable
		
		if '.' in attr:
			# recurse until we have it all broken down!
			return self.variable_value(key=attr, variable=variable, recursing=True)
		
		# Do all the checks
		if hasattr(variable, attr):
			attr = getattr(variable, attr)
			if hasattr(attr, '__call__'):
				return attr()
			return attr
		try:
			return variable[attr]
		except (TypeError, KeyError, IndexError):
			# not iterable, or does not exist, try next
			pass

		if attr.isdigit():
			if len(variable) <= int(attr):
				return None
			try:
				return variable[int(attr)]
			except KeyError as e:
				raise TemplateKeyError(e)
		
		return None
