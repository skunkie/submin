from submin.dispatch.view import View
from submin.template.shortcuts import evaluate_main
from submin.dispatch.response import Response, XMLStatusResponse, XMLTemplateResponse
from submin.views.error import ErrorResponse
from submin.models import user
from submin.models import group
from submin.models.exceptions import GroupExistsError, MemberExistsError
from submin.models.exceptions import UnknownGroupError
from submin.auth.decorators import *
from submin.models import options

class Groups(View):
	@login_required
	def handler(self, req, path):
		localvars = {}

		if req.is_ajax():
			return self.ajaxhandler(req, path)

		if len(path) < 1:
			return ErrorResponse('Invalid path', request=req)

		if len(path) > 0:
			localvars['selected_type'] = 'groups'
		if len(path) > 1:
			localvars['selected_object'] = path[1]

		try:
			if path[0] == 'show':
				return self.show(req, path[1:], localvars)
			if path[0] == 'add':
				return self.add(req, path[1:], localvars)
		except Unauthorized:
			return Redirect(options.url_path('base_url_submin'), req)

		return ErrorResponse('Unknown path', request=req)

	def show(self, req, path, localvars):
		if len(path) < 1:
			return ErrorResponse('Invalid path', request=req)

		is_admin = req.session['user']['is_admin']
		try:
			g = group.Group(path[0])
		except (IndexError, UnknownGroupError):
			if not is_admin:
				return ErrorResponse('Not permitted', request=req)

			return ErrorResponse('This group does not exist.', request=req)

		if not is_admin and req.session['user']['name'] not in g.members():
			return ErrorResponse('Not permitted', request=req)

		localvars['group'] = g
		formatted = evaluate_main('groups.html', localvars, request=req)
		return Response(formatted)

	def showAddForm(self, req, groupname, errormsg=''):
		localvars = {}
		localvars['errormsg'] = errormsg
		localvars['groupname'] = groupname
		formatted = evaluate_main('newgroup.html', localvars, request=req)
		return Response(formatted)

	@admin_required
	def add(self, req, path, localvars):
		base_url = options.url_path('base_url_submin')
		groupname = ''

		if req.post and req.post['groupname']:
			import re

			groupname = req.post.get('groupname').strip()
			if re.findall('[^a-zA-Z0-9_-]', groupname):
				return self.showAddForm(req, groupname, 'Invalid characters in groupname')
			if groupname == '':
				return self.showAddForm(req, groupname, 'Groupname not supplied')

			url = base_url + '/groups/show/' + groupname

			try:
				group.add(groupname)
			except IOError:
				return ErrorResponse('File permission denied', request=req)
			except GroupExistsError:
				return self.showAddForm(req, groupname, 'Group %s already exists' % groupname)

			return Redirect(url, req)

		return self.showAddForm(req, groupname)

	def ajaxhandler(self, req, path):
		success = False
		error = ''
		response = None
		username = ''

		if len(path) < 2:
			return XMLStatusResponse('', False, 'Invalid Path')

		action = path[0]
		groupname = path[1]

		if action == 'delete':
			return self.removeGroup(groupname)

		if 'removeMember' in req.post:
			return self.removeMember(req, groupname)

		if 'addMember' in req.post:
			return self.addMember(req, groupname)

		if 'listGroupUsers' in req.post:
			return self.listGroupUsers(req, group.Group(groupname))

		return XMLStatusResponse('', False, 'Unknown command')

	def listGroupUsers(self, req, g):
		members = list(g.members())
		asking_user = user.User(req.session['user']['name'])
		if asking_user.is_admin:
			nonmembers = []
			usernames = user.list(asking_user)
			for username in usernames:
				if username not in members:
					nonmembers.append(username)

			return XMLTemplateResponse("ajax/groupmembers.xml",
					{"members": members, "nonmembers": nonmembers,
						"group": g.name})

		if asking_user.name not in g.members():
			return XMLStatusResponse('listGroupUsers', False,
				"You do not have permission to view this group.")

		return XMLTemplateResponse("ajax/groupmembers.xml",
				{"members": members, "nonmembers": [],
					"group": g.name})

	@admin_required
	def removeMember(self, req, groupname):
		g = group.Group(groupname)
		username = req.post.get('removeMember')
		success = True
		try:
			g.remove_member(user.User(username))
		except:
			success = False

		msgs = {True: 'User %s removed from group %s' % (username, groupname),
				False: 'User %s is not a member of group %s' % (username, groupname)}
		return XMLStatusResponse('removeMember', success, msgs[success])

	@admin_required
	def addMember(self, req, groupname):
		username = req.post.get('addMember')
		success = True
		try:
			group.Group(groupname).add_member(user.User(username))
		except MemberExistsError:
			success = False

		msgs = {True: 'User %s added to group %s' % (username, groupname),
				False: 'User %s already in group %s' % (username, groupname)}
		return XMLStatusResponse('addMember', success, msgs[success])

	@admin_required
	def removeGroup(self, groupname):
		try:
			g = group.Group(groupname)
			g.remove()
		except IOError:
			return XMLStatusResponse('removeGroup', False, 'File permisson denied')
		except UnknownGroupError:
			return XMLStatusResponse('removeGroup', False,
				'Group %s does not exist' % groupname)

		return XMLStatusResponse('removeGroup', True, 'Group %s deleted' % g)

