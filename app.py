import re, os, sys, binascii
from datetime import datetime
import flask
from flask import Flask, request, json, render_template, redirect, url_for, abort, session
from flask.ext.babel import Babel
from werkzeug.routing import BaseConverter
import collections
import requests

TRANSLATIONS = ['en-US', 'en_US']

def getConfig():
    dir  = os.path.dirname(__file__)
    file = 'config.json'
    json_data = open(os.path.join(dir, file))
    data      = json.load(json_data)
    return data

class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

def createapp():
  demo = '-d' in sys.argv
  app = Flask(__name__)
  if '--debug' in sys.argv:
    app.debug = True
  app.url_map.converters['regex'] = RegexConverter
  babel = Babel(app)

  def get_supported_locales():
    langs = {}
    for b in babel.list_translations():
      if not demo and str(b) not in TRANSLATIONS:
        #print str(b)," is not in ",TRANSLATIONS
        continue
      if b.territory:
        langs["%s-%s" % (b.language, b.territory)] = b.display_name
      else:
        langs[b.language] = b.display_name
    return langs

  @babel.localeselector
  def get_locale():
    print [str(b) for b in babel.list_translations()]
    lang = request.path[1:].split('/', 1)[0].replace('-', '_')
    langs = {}
    for b in babel.list_translations():
      if not demo and str(b) not in TRANSLATIONS:
        continue
      if b.territory:
        langs["%s_%s" % (b.language, b.territory)] = str(b)
      else:
        langs[b.language] = str(b)
    #print lang, langs
    if lang in langs.keys():
      return lang
    else:
      return 'en_US'

  def renderTemplate(template, locale, path=None):
    locales = get_supported_locales()
    #if locale not in locales:
    #  abort(404)

    data = getConfig()
    data["production"] = not demo
    basehref = ""
    if locale:
      basehref = locale + '/'
    # add localized strings
    data["locale"] = locale

    data["basehref"] = basehref
    data['translations'] = get_supported_locales()
    data['current_year'] = datetime.now().year
    return render_template(template, **data)

  # # support for persona if we use it 
  # @app.route('/auth/login', methods=['POST'])
  # def login():
  #   if 'assertion' not in request.form:
  #       abort(400)
  # 
  #   assertion_info = {'assertion': request.form['assertion'],
  #                       'audience': 'localhost:8888' } # window.location.host
  #   resp = requests.post('https://verifier.login.persona.org/verify',
  #                       data=assertion_info, verify=True)
  # 
  #   if not resp.ok:
  #       abort(500)
  # 
  #   data = resp.json()
  #   print "", data
  #   if data['status'] == 'okay':
  #       session.update({'email': data['email']})
  #       return resp.content
  # 
  # @app.route('/auth/logout', methods=['POST'])
  # def logout():
  #   session.pop('email', None)
  #   return redirect('/')

  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/downloads/')
  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/downloads/<path:path>')
  def app_desktop_downloads(locale=None, path=None):
    return renderTemplate("downloads.html", locale, path)

  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/desktop/')
  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/desktop/<path:path>')
  def app_desktop(locale=None, path=None):
    return renderTemplate("desktop.html", locale, path)

  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/android/')
  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/android/<path:path>')
  def app_android(locale=None, path=None):
    return renderTemplate("android.html", locale, path)

  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/<path:path>')
  def static_proxy(locale=None, path=None):
    # if root is locale, capture that, but use the same local file paths
    try:
      root, path = path.split('/', 1)
    except ValueError, e:
      root = locale
    # send_static_file will guess the correct MIME type
    if root in ["css", "images", "fonts", "js"]:
      return app.send_static_file(os.path.join(root, path))
    return renderTemplate(path, locale, path)

  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/<path>')
  def app_static_proxy(locale=None, path=None):
    return static_proxy(locale, path)

  @app.route('/<path:path>')
  def static_files(path=None):
    if not path:
      return redirectpage()
    return app.send_static_file(path)

  @app.route('/<regex("\w{2}(?:-\w{2})?"):locale>/')
  def app_index(locale):
    return renderTemplate('index.html', locale)

  @app.route("/")
  def root(base=None):
    # the server should handle a redirect. Since the frozen static pages will be
    # served on github pages for testing, we have a redirect located in the top
    # level index page.  We use that here to ensure that works as well.
    return app.send_static_file("index.html")

  return app


if __name__ == '__main__':
  app = createapp()
  app.secret_key = binascii.b2a_hex(os.urandom(30))
  app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8888)))
