from submin.template.shortcuts import evaluate_main
from submin.dispatch.response import Response
from submin.dispatch.view import View
from submin.auth.decorators import *
from submin.models import options

class Intro(View):
	@login_required
	def handler(self, req, path):
		localvars = {}

		if not req.session['user']['is_admin']:
			base_url = options.url_path('base_url_submin')
			username = req.session['user']['name']
			return Redirect(base_url + '/users/show/' + username, req)

		formatted = evaluate_main('intro.html', localvars, request=req)
		return Response(formatted)
