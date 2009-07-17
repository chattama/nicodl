# NicoNicoDouga download sample script

###############################################################################
# settings
mail		= ''
password	= ''

savedir 	= 'C:/temp/'

user_agent	= None
#user_agent	= 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)'

proxies 	= None
#proxies 	= {'http':'http://127.0.0.1:8080/', 'https':'http://127.0.0.1:8080/'}

###############################################################################
import os
import re
import imp
import sys
import string
import urllib
import UserDict

pys60 = False
try:
	fp, path, desc = imp.find_module("e32")
	sys.setdefaultencoding('utf-8')
	pys60 = True
except:
	sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])) + '/lib')
	pys60 = False

# cgi.py porting
def parse_qsl(qs, keep_blank_values=0, strict_parsing=0):
	pairs = [s2 for s1 in string.split(qs, '&') for s2 in string.split(s1, ';')]
	r = []
	for name_value in pairs:
		if not name_value and not strict_parsing:
			continue
		nv = string.split(name_value, '=', 1)
		if len(nv[1]) or keep_blank_values:
			name	= urllib.unquote(string.replace(nv[0], '+', ' '))
			value = urllib.unquote(string.replace(nv[1], '+', ' '))
			r.append((name, value))
	return r

def parse_qs(qs, keep_blank_values=0, strict_parsing=0):
	dict = {}
	for name, value in parse_qsl(qs, keep_blank_values, strict_parsing):
		if name in dict:
			dict[name].append(value)
		else:
			dict[name] = [value]
	return dict


###############################################################################
class NicoOpener(urllib.URLopener):

	URL_TOP	= 'http://www.nicovideo.jp/'
	URL_LOGIN = 'https://secure.nicovideo.jp/secure/login?site=niconico'
	
	def __init__(self, mail=None, password=None, ua=None, proxies=None):
		if ua:
			self.version = ua
		urllib.URLopener.__init__(self)
		self.mail = mail
		self.password = password
		self.proxies = proxies
		self.nicohistory = None
		self.user_session = None

	def open(self, fullurl, data=None, headers=[]):
		self.addheaders = []
		self.addheader('User-Agent', self.version)
		self.addheader('Cache-Control', 'no-cache')
		for h in headers:
			self.addheader(h[0], h[1])
		return urllib.URLopener.open(self, fullurl, data)

	def http_error_default(self, url, fp, errcode, errmsg, headers):
		if errcode == 302:
			return urllib.addinfourl(fp, headers, 'http:' + url)
		return urllib.URLopener.http_error_default(self, url, fp, errcode, errmsg, headers)

	def get_cookie(self, response, attr, search_re):
		if not hasattr(self, attr):
			return
		setattr(self, attr, None)
		for c in response.headers.getheaders('Set-Cookie'):
			m = re.compile(search_re).match(c)
			if m:
				setattr(self, attr, m.group())

	def login(self):
		post_data = urllib.urlencode({'next_url':'', 'mail':self.mail, 'password':self.password})
		response = self.open(self.URL_LOGIN, post_data)
		self.get_cookie(response, 'user_session', 'user_session=user_session([0-9_]+)')
		if not self.user_session:
			raise LoginError
		return response

	def watch(self, id):
		response = self.open_login_page(self.URL_TOP + 'watch/' + id)
		self.get_cookie(response, 'nicohistory', 'nicohistory=([^;]+)')
		if not self.nicohistory:
			raise LoginError
		return response

	def open_login_page(self, url):
		if not self.user_session:
			self.login()
		r = self.open(url, headers=[('Cookie', self.user_session)])
		if r.headers['x-niconico-authflag'] == '0':
			self.login()
			return self.open(url, headers=[('Cookie', self.user_session)])
		return r

	def open_comment_page(self, url, flvinfo, data=None):
		self.watch(flvinfo.id)
		return self.open(url, data=data, headers=[('Cookie', '%s; %s' % (self.user_session, self.nicohistory))])

	def open_video_page(self, url, flvinfo, data=None):
		self.watch(flvinfo.id)
		return self.open(url, data=data, headers=[('Cookie', '%s; %s' % (self.user_session, self.nicohistory))])

	def page_nicovideo_top(self):
		return self.open_login_page(self.URL_TOP)

	def page_category_top(self, category):
		return self.open_login_page(self.URL_TOP + '?g=' + category)

	def page_my(self):
		return self.open_login_page(self.URL_TOP + 'my')

	def page_mylist(self, id):
		return self.open_login_page(self.URL_TOP + 'mylist/' + id)

	def page_getheadline(self):
		return self.open(self.URL_TOP + 'api/getheadline')

	def page_getflv(self, id):
		return self.open_login_page(self.URL_TOP + 'api/getflv/' + id)

	def page_getthumbinfo(self, id):
		return self.open(self.URL_TOP + 'api/getthumbinfo/' + id)

	def download_thumb(self, url):
		return self.open(url)

	def download_flv(self, flvinfo):
		return self.open_video_page(flvinfo['url'], flvinfo=flvinfo)

	def download_comment(self, flvinfo, res=-100):
		post_data = '<thread version="20061206" res_from="%d" user_id="%s" thread="%s" />' % (res, flvinfo['user_id'], flvinfo['thread_id'])
		return self.open_comment_page(flvinfo['ms'], data=post_data, flvinfo=flvinfo)

	def is_error_getthumbinfo(self, content):
		if re.compile('<nicovideo_thumb_response status="fail">', re.S).findall(content):
			return True
		return False

	def is_error_getflv(self, content):
		if re.compile('closed=1&done=true', re.S).findall(content):
			return True
		if re.compile('error=invalid_thread&done=true', re.S).findall(content):
			return True
		return False


class FlvInfo(UserDict.UserDict):

	def __init__(self, dict=None, content=None, id=None):
		UserDict.UserDict.__init__(self, dict)
		self.id = id
		if content:
			self.data = parse_qs(content)

	def __getitem__(self, key):
		try:
			return UserDict.UserDict.__getitem__(self, key)[0]
		except IndexError:
			return None
		except KeyError:
			return None


class LoginError(Exception):
	pass


class PageError(Exception):
	pass



def save_video(id, response):
	fmt = '%s %d/%d'
	out = sys.stdout
	
	fp = open(savedir + id + '.flv', 'wb')
	
	total = int(response.headers['Content-Length'])
	size = 0
	
	text = fmt % (id, 0, total)
	if pys60:
		appuifw.app.body = appuifw.Text(unicode(text))
	else:
		out.write(text + '\r')
	
	bs = 1024 * 8
	
	while True:
		data = response.read(bs)
		size = size + len(data)
		
		text = fmt % (id, size, total)
		if pys60:
			appuifw.app.body = appuifw.Text(unicode(text))
		else:
			out.write(text + '\r')
			
		if data == '':
			break
		fp.write(data)
	
	text = fmt % (id, size, total)
	if pys60:
		appuifw.app.body = appuifw.Text(unicode(text + '\r\ncomplete'))
	else:
		out.write(text + '\r\ncomplete')
		
	fp.close()


def download(id):
	opener = NicoOpener(mail=mail, password=password, ua=user_agent, proxies=proxies)
	
	print 'connect niconico'
	response = opener.page_getflv(id)
	html = response.read()
	if opener.is_error_getflv(html):
		print 'login error'
		return
	
	flvinfo = FlvInfo(id=id, content=html)
	
	print 'start download'
	response = opener.download_flv(flvinfo)
	
	save_video(id, response)


###############################################################################
# win32 console
if __name__ == '__main__':
	if not pys60:
		download(sys.argv[1])
		sys.exit()


###############################################################################
import e32
import socket
import appuifw
import traceback


class UI:

	def __init__(self):
		appuifw.app.exit_key_handler = self.exit
		appuifw.app.menu = [(u"Exit",self.exit)]
		
	def run(self):
		self.start()
		e32.Ao_lock().wait()
		
	def start(self):
		try:
			self.apid = socket.select_access_point()
			self.ap = socket.access_point(self.apid)
			socket.set_default_access_point(self.ap)
			
			id = appuifw.query(u'DOUGA-ID', 'text')
			if not id:
				self.exit()
			
			download(unicode(id).encode('utf-8'))
			
		except Exception, e:
			traceback.print_exc()
		
	def exit(self):
		appuifw.app.exit_key_handler = None
		sys.exit()
		

# pys60 run script
if __name__ == '__main__':
	UI().run()
