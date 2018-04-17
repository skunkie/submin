# -*- coding: utf-8 -*-

"""The templates use unicode internally, so everything is first converted
to unicode (if it is not already unicode). When pushed to the browser, it
can be converted to the right locale (but currently it is just converted
to utf-8)"""

import os
from types import * # for ikey/ival

from .library import Library
from .template import Template
commands = Library()

class ElseError(Exception):
	pass

class VariableNotIterable(Exception):
	pass

class UnknownTemplateError(Exception):
	pass

class MissingRequiredArguments(Exception):
	pass
	
class DotInLocalVariable(Exception):
	pass

class IteratingIkey(Exception):
	pass

class IvalOutsideIter(Exception):
	pass

class IkeyOutsideIter(Exception):
	pass

@commands.register('set')
def set(node, tpl):
	"""Sets a variable to a value, local to the template.
	Don't use a period (.) in your variable-name, because the [val] tag will
	not like that."""
	text = ''.join([x.evaluate(tpl) for x in node.nodes])
	args = node.arguments
	if not args:
		raise MissingRequiredArguments(
			"Missing required argument variable at file %s, line %d" %
			(tpl.filename, node.line))
	
	if '.' in args:
		raise DotInLocalVariable(
			"You cannot use a . when setting local variables (file %s, line %d)" %
			(tpl.filename, node.line))
	tpl.variables[args] = text
	return ''

@commands.register('val')
def val(node, tpl):
	if not node.nodes:
		raise MissingRequiredArguments(
			"Missing required argument variable at file %s, line %d" %
			(tpl.filename, node.line))

	# evaluate always returns a string (possibly empty), or raises an Exception
	text = node.nodes[0].evaluate()
	value = tpl.variable_value(text)

	if not value is None:
		return value
	return ''

@commands.register('include')
def include(node, tpl):
	to_include = ''
	for n in node.nodes:
		to_include += n.evaluate(tpl)

	if not os.path.exists(to_include):
		raise UnknownTemplateError("Could not find '%s' (file %s, line %d)" %
		(to_include, tpl.filename, node.line))
	oldcwd = os.getcwd()
	if os.path.dirname(to_include):
		os.chdir(os.path.dirname(to_include))
	
	fp = open(os.path.basename(to_include), 'r')
	evaluated_string = ''
	if fp:
		new_tpl = Template(fp, tpl.variables)
		evaluated_string = new_tpl.evaluate()
		
		fp.close()
	if os.path.dirname(to_include):
		os.chdir(oldcwd)
	return evaluated_string
	
@commands.register('iter')
def iter(node, tpl):
	if not node.arguments:
		raise MissingRequiredArguments(
			"Missing required argument variable at file %s, line %d" %
			(tpl.filename, node.line))
	
	if 'ival' not in tpl.node_variables:
		tpl.node_variables['ival'] = []
	if 'iindex' not in tpl.node_variables:
		tpl.node_variables['iindex'] = []
	if 'iseq' not in tpl.node_variables:
		tpl.node_variables['iseq'] = []
	if 'ikey' not in tpl.node_variables:
		tpl.node_variables['ikey'] = []
	tpl.node_variables['ival'].append(None)
	tpl.node_variables['iindex'].append(None)
	tpl.node_variables['iseq'].append(None)
	tpl.node_variables['ikey'].append(None)
	
	value = ''
	if node.arguments.startswith('ival'):
		if node.arguments == 'ival':
			value = tpl.node_variables['ival'][-2]
		else:
			# take from ival.foo.bar the foo.bar part
			args = node.arguments.split('.', 1)[1]
			if len(tpl.node_variables['ival']) >= 1:
				value = tpl.variable_value('', args, tpl.node_variables['ival'][-2])
	elif node.arguments == 'ikey':
		# iterable objects cannot be used as key in python
		raise IteratingIkey(
			"Cannot iterate over ikey at file %s, line %d" %
			(tpl.filename, node.line))
	else:
		value = tpl.variable_value(node.arguments)
	if not value:
		return ''
	tpl.node_variables['iseq'][-1] = value
	
	# check if variable is iterable
	try:
		import __builtin__ # we need this because this function is also called 'iter'
		it = __builtin__.iter(value)
	except TypeError:
		raise VariableNotIterable(
			'Variable "%s" not iterable in template "%s", at line %d' %
				(node.arguments, tpl.filename, node.line))

	evals = []
	for index, item in enumerate(value):
		tpl.node_variables['iindex'][-1] = index
		tpl.node_variables['ikey'][-1] = item
		if not isinstance(value, DictType):
			tpl.node_variables['ival'][-1] = item
		else:
			tpl.node_variables['ival'][-1] = value[item]

		evals.append(''.join([x.evaluate(tpl) for x in node.nodes]))

	tpl.node_variables['ival'].pop()
	tpl.node_variables['iindex'].pop()
	tpl.node_variables['iseq'].pop()
	tpl.node_variables['ikey'].pop()
	return ''.join(evals)

@commands.register('ival')
def ival(node, tpl):
	args = node.arguments
	if not args:
		args = None
	if 'ival' in tpl.node_variables and len(tpl.node_variables['ival']) >= 1:
		return tpl.variable_value('', args, tpl.node_variables['ival'][-1])
	raise IvalOutsideIter(
		"Ival without enclosing iter at file %s, line %d" %
		(tpl.filename, node.line))

@commands.register('ikey')
def ikey(node, tpl):
	args = node.arguments
	if not args:
		args = None
	if 'ikey' in tpl.node_variables and len(tpl.node_variables['ikey']) >= 1:
		return tpl.variable_value('', args, tpl.node_variables['ikey'][-1])
	raise IkeyOutsideIter(
		"Ikey without enclosing iter at file %s, line %d" %
		(tpl.filename, node.line))

def ilast(tpl):
	if tpl.node_variables['iindex'][-1] \
			>= len(tpl.node_variables['iseq'][-1]) - 1:
		return True
	return False

def testTrue(node, tpl):
	if not node.arguments:
		raise MissingRequiredArguments(
			"Missing required argument variable at file %s, line %d" %
			(tpl.filename, node.line))
	negation = False
	args = node.arguments
	if args.startswith('!'):
		negation = True
		args = args[1:]

	if args == 'ilast':
		value = ilast(tpl)
	else:
		value = tpl.variable_value(args)

	expression = value is None or not value
	if negation:
		return expression
	return not expression
	#return value is not None and not not value

def testEquals(node, tpl):
	if not node.arguments:
		raise MissingRequiredArguments(
			"Missing required argument variable at file %s, line %d" %
			(tpl.filename, node.line))
	args = node.arguments.split(':')

	value1 = tpl.variable_value(args[0])
	value2 = tpl.variable_value(args[1])
	return value1 == value2

@commands.register('equals')
def equals(node, tpl):
	args = node.arguments
	value = testEquals(node, tpl)
	if not value:
		return ''
	return ''.join([x.evaluate(tpl) for x in node.nodes])

@commands.register('test')
def test(node, tpl):
	value = testTrue(node, tpl)
	if not value: # value is None or not value:
		return ''
	return ''.join([x.evaluate(tpl) for x in node.nodes])

@commands.register('else')
def else_tag(node, tpl):
	prev = node.previous_node
	while prev and prev.type == 'text':
		prev = prev.previous_node
	if not prev or prev.type != 'command' or (prev.command != 'test' and 
			prev.command != 'equals'):
		raise ElseError(
			'Previous node to else was not a test-node (file %s, line %d, node %s)' %
			(tpl.filename, node.line, str(prev)))

	if prev.command == 'test':
		value = testTrue(prev, tpl)
		if not value:
			return ''.join([x.evaluate(tpl) for x in node.nodes])
		return ''

	if prev.command == 'equals':
		value = testEquals(prev, tpl)
		if not value:
			return ''.join([x.evaluate(tpl) for x in node.nodes])
		return ''
