from submin.models import options

from .common import apache_modules, ApacheCtlError
from .common import add_labels

fails = ['external_settings_ok', 'external_apache_modules_ok', 'external_apache_modules_exec_ok']
warnings = ['enabled_external']

def diagnostics():
	results = {}
	results['enabled_external'] = options.value('enabled_external', 'no') != 'no'

	if not results['enabled_external']:
		results['enabled_external_label'] = 'disabled'
		results['external_all_label'] = 'disabled'
		return results

	found_mods = {}
	amods = []
	required_mods = ['authnz_ldap', 'ldap']
	try:
		amods = apache_modules()
	except ApacheCtlError as e:
		results['external_apache_modules_ok'] = False
		results['external_apache_modules_exec_ok'] = False
		results['external_apache_modules_errmsg'] = str(e)
	else:
		results['external_apache_modules_exec_ok'] = True

	for mod in required_mods:
		found_mods.update({mod: mod in amods})

	results['external_apache_modules'] = found_mods
	results['external_apache_modules_ok'] = False not in found_mods.values()

	results['external_settings_ok'] = True
	results['external_settings'] = {
		'external_server': [False, 'ldaps://example.net'],
		'external_base_dn': [False, 'DC=example,DC=net'],
		'external_group_dn': [False, 'CN=SVN,OU=SVN,DC=example,DC=net'],
		'external_user': [False, 'user'],
		'external_passwd': [False, 'secret'],
		'external_upn_suffix': [False, 'example.net']}

	for setting in results['external_settings']:
		if not options.value(setting, ''):
			results['external_settings_ok'] = False
		else:
			results['external_settings'][setting][0] = True

	return add_labels(results, 'external_all', warnings, fails)
