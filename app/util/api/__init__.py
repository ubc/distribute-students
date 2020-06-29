import base64
import re, json, collections
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import urllib, urllib.error
import logging
from configparser import ConfigParser

# Some regexes for dealing with HTTP responses from API
CHARSET_PATTERN = re.compile(r'charset=(.+?)(;|$)')

def check_JSON(response):
    '''checks whether a response is JSON'''
    content = response.headers.get('Content-Type')
    return "json" in content

def get_Charset(response):
    '''Gets the charset of an API response'''
    content = response.headers.get('Content-Type')
    if content is None:
        return None
    groups = CHARSET_PATTERN.search(content)
    if groups is None:
        return"utf-8"
    return groups.group(1)

def get_token(username, password):
    en = bytes("{}:{}".format(username, password), encoding="utf-8")
    ba = base64.b64encode(en)
    return ba.decode("utf-8")

def get_response_body(response):
    '''Converts an API response into a readable format'''
    if response is None:
        return ""
    charset = get_Charset(response)
    response_body = response.readline().decode(charset)
    is_JSON = check_JSON(response)
    if is_JSON and response_body:
        response_body = json.loads(response_body, object_pairs_hook=collections.OrderedDict)
    return response_body

def get_url_and_token(filename, environment):
    config = ConfigParser()
    config.read(filename)
    if not environment:
        envs = []
        for section in config.sections():
            envs.append(section)
        for i in range(len(envs)):
            print("{i}: {env}".format(i=i,env=envs[i]))
        try:
            env = int(input("? "))
        except ValueError as e:
            logging.error("ValueError: {}".format(e))
            env = 0
        try:
            environment = envs[env]
        except IndexError as e:
            logging.error("IndexError: {}".format(e))
    try:
        url = config[environment]['url']
        token = config[environment]['token']
    except KeyError as e:
        logging.error("invalid environment: {}".format(e))
        url = None
        token = None
    return url, token

class APIInstance:

    @property
    def url(self):
        return self._base_url
        
    def __init__(self, *args, **kwargs):
        try:
            if 'filename' in kwargs and 'env' in kwargs:
                config = ConfigParser()
                config.read(kwargs['filename'])
                self._set_auth(**config[kwargs['env']])
            else:
                self._set_auth(**kwargs)
        except KeyError as e:
            logging.error("Environment missin from config file: {}".format(e))
            self._set_auth()

        self._urlencode=False

    def _set_auth(self, **kwargs):        
        if 'url' in kwargs:
            self._base_url = kwargs['url']
        else:
            self._base_url = None
                
        if 'username' in kwargs and 'password' in kwargs:
            self._set_auth_basic(kwargs['username'], kwargs['password'])
        elif 'bearer' in kwargs:
            self._set_auth_bearer(kwargs['bearer'])
        elif 'token' in kwargs:
            self._set_auth_token(kwargs['token'])
        else:
            self._token = None
            self._auth = None

    def _set_auth_basic(self, username, password):
        self._token = get_token(username, password)
        self._auth = "Basic"

    def _set_auth_bearer(self, bearer):
        self._token = bearer
        self._auth = "Bearer"

    def _set_auth_token(self, token):
        self._token = 'token="{}"'.format(token)
        self._auth = "Token"

    def call_api(self, url, on_behalf_of=None, is_url_absolute=False, method="GET", post_fields=None, content_type="application/json"):
        try:
            request = self._build_request(url, on_behalf_of, is_url_absolute, method, post_fields, content_type)
        except ValueError as e:
            logging.error(e)
            logging.warning("course not make request")
            return
        if post_fields:
            logging.debug("{method} {url} {post_fields}".format(method=request.method, url=request.full_url, post_fields=post_fields))
        else:
            logging.debug("{method} {url}".format(method=request.method, url=request.full_url))
        try:
            response = urlopen(request)
            logging.debug("HTTP {code} {reason}".format(code=response.code, reason=response.reason, url=request.full_url))
            return response
        except urllib.error.HTTPError as e:
            logging.debug("HTTP {code} {reason}".format(code=e.code, reason=e.reason, url=request.full_url))
            return e
        except Exception as e:
            logging.error("Unexpected error occured: {}:{}".format(type(e).__name__, e))
            logging.warning("could not make request")

    def _build_request(self, url, on_behalf_of=None, is_url_absolute=False, method="GET", post_fields=None, content_type="application/json"):
        if is_url_absolute:
            urlstr = url
        else:
            urlstr = "{}/{}".format(self._base_url, url)
        request = Request(urlstr)
        if not self._urlencode:
            request.add_header('Content-Type', content_type)
        if on_behalf_of:
            request.add_header("X-On-Behalf-Of", on_behalf_of)
        if self._auth and self._token:
            request.add_header('Authorization', '{auth} {token}'.format(auth=self._auth, token=self._token))
        request.method = method
        if post_fields:
            if self._urlencode:
                request.data = urlencode(post_fields).encode()
            else:
                request.data = json.dumps(post_fields).encode()
        return request

    def get_body(self, response):
        return get_response_body(response)
