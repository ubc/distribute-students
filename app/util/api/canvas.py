from . import *
import os

url = {"prod":"https://ubc.instructure.com",
       "test":"https://ubc.test.instructure.com",
       "beta":"https://ubc.beta.instructure.com"}

class CanvasInstance(APIInstance):
    def __init__(self, env=None):
        if not env:
            from .. import _ENV
            env = _ENV
        _TOKEN = os.environ.get("TOKEN")
        _URL = os.environ.get("URL")
        if not _URL:
            _URL = url[env]
        APIInstance.__init__(self, bearer=_TOKEN, url=_URL)
        if  self._base_url and 'api/v1' not in self._base_url:
            self._base_url = self._base_url + "/api/v1"
        self._urlencode=True

    def call_api(self, url, is_url_absolute=False, method="GET", post_fields=None, all_pages=True, content_type="application/json"):
        response = super().call_api(url,None,is_url_absolute,method,post_fields,content_type)
        if response and all_pages and "Link" in response.headers:
            collector = []
            more_pages = True
            while more_pages:
                response_body = get_response_body(response)
                if isinstance(response_body, collections.OrderedDict):
                    response_body = [response_body]
                collector = collector + response_body      
                for link in response.headers.get("Link").split(','):
                    parts = link.split(";")
                    if parts[1].find('next') >= 0:
                        next_page = parts[0]
                        next_page = next_page.replace('<', '')
                        next_page = next_page.replace('>', '')
                        next_page = next_page.strip()
                        response = super().call_api(url=next_page,
                                                    on_behalf_of=None,
                                                    is_url_absolute=True,
                                                    method=method,
                                                    post_fields=post_fields,
                                                    content_type=content_type)
                        break
                else:
                    more_pages = False
     
            return collector
        else:
            return get_response_body(response)
