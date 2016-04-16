import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.httpclient
import tornado.gen
import tornado.options
import tornado.escape
import hmac
import hashlib

try:
    import settings
except ImportError:
    import settings_local as settings


class BaseHandler(tornado.web.RequestHandler):

    def settings_get(self, name, default=None):
        has_name = name in self.settings.keys()
        return self.settings[name] if has_name else default

    def headers_get(self, name, default=None):
        try:
            return self.request.headers[name]
        except KeyError:
            return default

    def _create_signature(self, secret, *parts):
        hash_fn = hmac.new(secret, digestmod=hashlib.sha256)
        for part in parts:
            hash_fn.update(part)
        return hash_fn.hexdigest()

    def _verify_signature(self, payload, signature):
        secret = self.settings_get("secret")
        _signature = self._create_signature(secret, payload)
        return hmac.compare_digest(signature, _signature)

    def get_current_user(self):
        payload_body = self.request.body
        signature = self.headers_get("X-Hub-Signature")
        if not signature:
            return None
        return self._verify_signature(payload_body, signature)

    def set_default_headers(self):
        self.set_header("Server", "Tornado+/%s" % tornado.version)


class MirrorsHandler(BaseHandler):

    @tornado.gen.coroutine
    def fetch_data(self, url):
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = yield http_client.fetch(url)
        raise tornado.gen.Return(response.body)

    @tornado.gen.coroutine
    def post_data(self, request):
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = yield http_client.fetch(request)
        raise tornado.gen.Return(response)

    @tornado.gen.coroutine
    @tornado.web.authenticated
    def post(self, *args, **kwargs):
        event = self.headers_get("X-GitHub-Event")
        if event != "push":
            self.finish("`push` expected but got `{}`".format(event))
        mirrors_data_url = "https://raw.githubusercontent.com/cqumirrors" \
                           "/bubbles/master/mirrors.json"
        data_fetched = yield self.fetch_data(mirrors_data_url)
        mirrors_json = tornado.escape.json_decode(data_fetched)
        # post to capacitor
        post_request_url = "http://dev.mirrors.lanunion.org/api/mirrors"
        post_request_headers = {
            "Access-Token": self.settings_get("access_token"),
            "Content-Type": "application/json"
        }
        post_request_params = dict(
            url=post_request_url,
            method="POST",
            headers=post_request_headers,
            body=tornado.escape.json_encode(dict(targets=mirrors_json)))
        post_request = tornado.httpclient.HTTPRequest(**post_request_params)
        response = yield self.post_data(post_request)
        self.finish(response.body)


class NoticesHandler(BaseHandler):

    @tornado.web.authenticated
    def post(self, *args, **kwargs):
        pass


def make_app():
    handlers = [
        ("/api/p/mirrors", MirrorsHandler),
        ("/api/p/notices", NoticesHandler)]
    _settings = dict(
        secret=settings.SECRET_KEY,
        access_token=settings.ACCESS_TOKEN,
        debug=settings.DEBUG,)

    return tornado.web.Application(handlers, **_settings)


if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(settings.PORT, address=settings.HOST)
    tornado.ioloop.IOLoop.current().start()
