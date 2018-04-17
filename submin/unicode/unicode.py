# -*- coding: utf-8 -*-
"""Tools to convert from and to unicode"""

import re

def uc_str(obj, encoding='utf-8', errors='replace'):
	if isinstance(obj, str):
		return unicode(obj, encoding, errors)
	if isinstance(obj, unicode):
		return obj

	return unicode(str(obj), encoding, errors)

def _url_uc_to_uc_callback(matchobj):
	"""Convert characters to utf-8"""
	s = matchobj.group(0).encode('utf-8')
	u = s.replace("%", "\\")
	return unicode(u, 'unicode_escape')

def uc_url_decode(s):
	"""Convert expressions like '%uFFFF' to '\\uFFFF' and encode as unicode.
	This way of encoding unicode in urls is often used by javascript."""
	try:
		s = unicode(s, 'utf-8')
	except: # sometimes this happens... non-unicode encoded as unicode?
		s = unicode(s, 'unicode_escape')

	return re.sub('%u[a-zA-Z0-9]{4,4}', _url_uc_to_uc_callback, s)

def uc_from_svn(path):
	"""Copied from Trac"""
	return uc_str(path, 'utf-8')

def uc_to_svn(*args):
	"""Copied from Trac"""
	return '/'.join([p for p in [p.strip('/') for p in args] if p]) \
		.encode('utf-8')

