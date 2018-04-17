import cgi # for cgi.FieldStorage/parse_qs etc.

from Cookie import SimpleCookie

# to convert javascript URL encoding to Unicode
from submin.unicode import uc_url_decode

class Request(object):
	"""Provide a consistent way to treat a Request."""

	def __init__(self):
		self.post = {}
		self.get = {}
		self.url = ''
		self.path_info = ''
		self.remote_address = ''
		self.remove_base_url = False # needed for WSGI
		self.headers = {'Content-Type': 'text/html'}

		self._incookies = SimpleCookie()
		self._outcookies = SimpleCookie()

	def setHeader(self, header, value):
		if not hasattr(self, 'headers'):
			self.headers = dict()
		self.headers[header] = value

	def setHeaders(self, headers={}):
		for header, value in headers.iteritems():
			self.setHeader(header, value)

	def cookieHeaders(self):
		for name in self._outcookies.keys():
			path = self._outcookies[name].get('path')
			if path:
				path = path.replace(' ', '%20') \
						.replace(';', '%3B') \
						.replace(',', '%3C')
			self._outcookies[name]['path'] = path

		cookies = self._outcookies.output(header='')
		for cookie in cookies.splitlines():
			self.setHeader('Set-Cookie', cookie.strip())
		# XXX overwrite header 'Set-Cookie' :S

		return self.headers['Set-Cookie']

	def write(self, content):
		raise NotImplementedError

	def writeResponse(self, response):
		self.write('Status: %d\r\n' % response.status_code)
		for header, value in response.headers.iteritems():
			self.write('%s: %s\r\n' % (header, value))
		self.write('\r\n')
		self.write(response.content)

	def setCookie(self, key, value, path='/', expires=None):
		self._outcookies[key] = value
		# make sure path does not contain trailing slash (#334)
		if path != '/':
			path = path.rstrip('/')

		self._outcookies[key]['path'] = path
		if expires:
			self._outcookies[key]['expires'] = expires

	def getCookie(self, key, default=None):
		try:
			value = self._incookies[key]
		except KeyError:
			return default
			
		if not value.value:
			return default
		
		return value.value

	def is_ajax(self):
		return 'ajax' in self.post or 'ajax' in self.get

class NoneObject:
	pass

class GetVariables(object):
	"""Provide a consistent way to access the GET variables."""
	
	def __init__(self, query_string=''):
		"""This is the method that needs to be overridden in CGIGet and 
		ModPythonGet. Each uses a different way to parse the query string"""
		self.variables = [query_string]
	
	def get(self, item, default=NoneObject):
		"""Return just one item from the query string (the last), 
		instead of a list with all the variables"""
		value = self.variables.get(item, [default])
		if value == [NoneObject]:
			raise KeyError(item)
		return value[-1]
	
	def __getitem__(self, item):
		return self.get(item)
	
	def getall(self, item):
		return self.variables.get(item)

class CGIGet(GetVariables):
	def __init__(self, query_string):
		self.variables = {}

		if query_string:
			self.variables = cgi.parse_qs(query_string, keep_blank_values=True)
	
	def __contains__(self, key):
		return key in self.variables

class CGIFieldStorage(cgi.FieldStorage):
	"""Provide a consistent way to access the POST variables."""
	
	def get(self, name, default=None):
		value = cgi.FieldStorage.getvalue(self, name, default)
		return uc_url_decode(value)

	def __setitem__(self, name, value):
		if name in self:
			del self[name]
		self.list.append(cgi.MiniFieldStorage(name, value))

	def __delitem__(self, name):
		if name not in self:
			raise KeyError(name)
		self.list = filter(lambda x, name=name: x.name != name, self.list)
