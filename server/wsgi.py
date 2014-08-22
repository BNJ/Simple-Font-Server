#!/usr/bin/env python
import os, sys
appdir = os.path.join(
	os.path.dirname(
		os.path.dirname(
			os.path.abspath(
				__file__
			)
		)
	),
	'server'
)
envdir = os.path.join(
	os.path.dirname(
		os.path.dirname(
			os.path.abspath(
				__file__
			)
		)
	),
	'env'
)
activate_this = os.path.join(envdir, 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__ = activate_this) )

import flask
from yaml import load
from urlparse import urlparse

with open( os.path.join( appdir, 'config.yaml'), 'rb' ) as yfile:
	font_config = load( yfile )
application = flask.Flask(__name__)

class OriginException(Exception):
	def __init__(self, reason, code):
		self.code = code
		self.reason = reason

	def make_response(self, request):
		if request.method == 'HEAD':
			return flask.make_response('', self.code)
		return flask.make_response(self.reason, self.code)

def vet_origin(request, fdir):
	origin = None
	if 'origin' in request.headers:
		origin = request.headers['origin']
	elif 'referer' in request.headers:
		uparts = urlparse(request.headers['referer'])
		origin = "%s://%s" % (uparts.scheme, uparts.netloc)

	if origin is not None and origin not in fdir['domains'] and '*' not in fdir['domains']:
		raise OriginException("Origin not allowed.", 403)

	if origin is None and 'default_domain' not in fdir:
		raise OriginException("No default domain specified.", 403)

	allowed_origin = origin
	if allowed_origin is None:
		allowed_origin = fdir['default_domain']

	return allowed_origin

def create_stylesheet(root, fdir):
	body = ''
	for face, formats in fdir['fonts'].items():
		body += '@font-face\n{\n'
		body += '  font-family: \'%s\';\n' % face.replace("'",r"\'")
		srces = []
		if 'eot' in formats:
			body += "  src: url('%s%s'); /* IE9 Compat Modes */\n" % (root, formats['eot'])
			srces.append(("url('%s%s?#iefix') format('embedded-opentype')" % (root, formats['eot']), 'IE6-8'))
		if 'woff' in formats:
			srces.append(("url('%s%s') format('woff')" % (root, formats['woff']), 'Modern Browsers'))
		if 'ttf' in formats:
			srces.append(("url('%s%s') format('truetype')" % (root, formats['ttf']), 'Safari, Android, iOS'))
		if 'otf' in formats:
			srces.append(("url('%s%s') format('opentype')" % (root, formats['otf']), 'I dunno. Mac OSX?'))
		if 'svg' in formats:
			srces.append(("url('%s%s#%s') format('svg')" % ( root, formats['svg'], face ), 'Legacy iOS' ))
		body += "  src: "
		for url, comment in srces[:-1]:
			body += "%s, /* %s */\n       " % ( url, comment)
		url, comment = srces[-1]
		body += "%s; /* %s */\n" % (url, comment)
		body += "}\n\n"
	return body


@application.route('/<path:directory>/<filename>', methods=('HEAD','GET'))
def get_stylesheet(directory, filename):
	if directory not in font_config:
		if request.method == "HEAD":
			return flask.make_response("", 404)
		return flask.make_response("Directory Not Found", 404)

	fdir = font_config.get(directory)
	request = flask.request

	try:
		allowed_origin = vet_origin(request, fdir)
	except OriginException as oe:
		return oe.make_response(request)

	body = ''
	contenttype = 'text/plain'
	if request.method == 'GET':
		root = request.url_root + directory + '/'
		filepath = os.path.join(
				appdir, 
				'fonts',
				fdir['sourcedir'],
				filename
			)
		if filename == 'fonts.css':
			body = create_stylesheet(root, fdir)
			contenttype = 'text/css'
		elif os.path.exists(filepath):
			with open(filepath, 'rb') as fontfile:
				body = fontfile.read()
			base, ext = os.path.splitext(filename)
			contenttype = {
				'.svg' : 'image/svg+xml',
				'.ttf' : 'application/x-font-ttf',
				'.otf' : 'application/x-font-opentype',
				'.woff': 'application/font-woff',
				'.eot' : 'application/vnd.ms-fontobject'
			}.get(ext,'application/octet-stream')


	resp = flask.make_response(body)
	resp.headers['Access-Control-Allow-Origin'] = allowed_origin
	if request.method != 'GET':
		resp.headers['Access-Control-Allow-Methods'] = 'GET'
	resp.headers['Content-Type'] = contenttype
	return resp

if __name__ == '__main__':
	application.config['TESTING'] = True
	application.config['DEBUG'] = True
	app = application.test_client()
	resp = app.head('/bnj/fonts.css', headers=[('Origin','http://www.bnj.com')])
	print repr(resp.headers)
	resp = app.head('/bnj/fonts.css', headers=[('Origin','https://www.bnj.com')])
	print repr(resp.headers)
	resp = app.head('/bnj/fonts.css', headers=[('Referer','http://bnj.com/some/page.html')])
	print repr(resp.headers)

	resp = app.get('/bnj/fonts.css', headers=[('Origin','http://www.bnj.com')])
	print repr(resp.headers)
	print resp.data

	resp = app.get('/bnj/xeroxsans-bold-webfont.woff', headers=[('Origin','http://www.bnj.com')])
	print repr(resp.headers)

