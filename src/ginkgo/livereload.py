# Some implements ref from Mkdocs(https://github.com/mkdocs/mkdocs/)

import io
import mimetypes
import posixpath
import re
import traceback
from typing import Callable, Dict, Iterable
import urllib.parse
import wsgiref.simple_server
import wsgiref.util
import socketserver
import logging
import threading
import time
import urllib
import string

from pathlib import Path

import watchdog.events
import watchdog.events
import watchdog.observers
import watchdog.observers.polling

logger = logging.getLogger(__name__)

# this javascript script copy from Mkdocs(https://github.com/mkdocs/mkdocs/)
_SCRIPT_TEMPLATE_STR = """
var livereload = function(epoch, requestId) {
    var req, timeout;

    var poll = function() {
        req = new XMLHttpRequest();
        req.onloadend = function() {
            if (parseFloat(this.responseText) > epoch) {
                location.reload();
            } else {
                timeout = setTimeout(poll, this.status === 200 ? 0 : 3000);
            }
        };
        req.open("GET", "/livereload/" + epoch + "/" + requestId);
        req.send();
    }

    var stop = function() {
        if (req) {
            req.abort();
        }
        if (timeout) {
            clearTimeout(timeout);
        }
        req = timeout = undefined;
    };

    window.addEventListener("load", function() {
        if (document.visibilityState === "visible") {
            poll();
        }
    });
    window.addEventListener("visibilitychange", function() {
        if (document.visibilityState === "visible") {
            poll();
        } else {
            stop();
        }
    });
    window.addEventListener("beforeunload", stop);

    console.log('Enabled live reload');
}
livereload(${epoch}, ${request_id});
"""
_SCRIPT_TEMPLATE = string.Template(_SCRIPT_TEMPLATE_STR)


class LiveReloadServer(socketserver.ThreadingMixIn, wsgiref.simple_server.WSGIServer):
    daemon_threads = True
    
    def __init__(
        self,
        root: str|Path,
        host: str,
        port: int,
        builder: Callable[[], None],
        watch_interval: float = 0.5,
        shutdown_delay: float = 0.5,
        builder_interval: float = 0.5,
        builder_debounce_interval: float = 0.5
    ):  
        if not isinstance(root, Path):
            root = Path(root)

        self.root = root
        self.builder = builder
        self.url = f'http://{host}:{port}'
        
        super().__init__((host, port), _Handler, bind_and_activate=False)
        self.set_app(self.server_request)

        self._wanted_version = _get_timestamp()
        self._available_version = self._wanted_version
        self._update_cond = threading.Condition()

        self._wanted_rebuild = False
        self._rebuild_cond = threading.Condition()

        self.observer = watchdog.observers.polling.PollingObserver(timeout=watch_interval)
        self.server_thread = threading.Thread(
            target=lambda: self.serve_forever(shutdown_delay)
        )

        self._watched_paths: Dict[str, int] = {}

        self._shutdown = False
        self._builder_interval = builder_interval
        self._builder_delay = builder_debounce_interval

        self._poll_response_timeout = 60

    def watch(
        self,
        path: str|Path,
        recursive: bool = True
    ):
        """Append the watch task to watchdog observer schedule"""
        if not isinstance(path, Path):
            path = Path(path)

        path = path.resolve()

        if path in self._watched_paths:
            self._watched_paths[path] += 1
            return 

        self._watched_paths[path] = 1

        # If files change, it will notice builder to build new site/
        def callback(event):
            if event.is_directory:
                return
            
            logger.debug(str(event))
            with self._rebuild_cond:
                self._wanted_rebuild = True
                self._rebuild_cond.notify_all()

        handler = watchdog.events.FileSystemEventHandler()
        handler.on_any_event = callback
        self.observer.schedule(handler, path, recursive=recursive)
        logger.debug(f'Watching "{path}" now...')

    def _build_loop(self):
        while True:
            with self._rebuild_cond:
                while not self._rebuild_cond.wait_for(
                    lambda: self._wanted_rebuild or self._shutdown,
                    timeout=self._builder_interval
                ):
                    pass
                
                if self._shutdown:
                    break

                logger.info('Files change!')
                logger.info('LiveloadServer Builder running...')

                while self._rebuild_cond.wait(timeout=self._builder_delay):
                    # wait file change events stopping
                    pass

                self._wanted_version = _get_timestamp()
                self._wanted_rebuild = False

            try:
                self.builder()
            except Exception as e:
                if isinstance(e, SystemExit):
                    logger.error(f'{e}')
                else:
                    traceback.print_exc()

                logger.error(
                    'An error happened unexpectedly when rebuild site/. The server will be stuck!'
                )

                continue

            # notice server to response broswer to update content
            with self._update_cond:
                logger.info('Reloading broswer...')
                self._available_version = self._wanted_version
                self._update_cond.notify_all()

    def server(self):
        """Start Server"""
        # manual init and start wsgiserver
        self.server_bind()
        self.server_activate()

        # start watchdog
        if self._watched_paths:
            self.observer.start()
            logger.info(f'{', '.join(str(path) for path in self._watched_paths)}')

        logger.info(f'Availble at {self.url}...')
        logger.info(f'You can copy it and open in your broswer.')

        # server in another thread, and builder in main thread
        self.server_thread.start()
        self._build_loop()

    def shutdown(self):
        self.observer.stop()
        
        with self._rebuild_cond:
            self._shutdown = True
            self._rebuild_cond.notify_all()

        if self.server_thread.is_alive():
            super().shutdown()

        self.server_close()
        self.server_thread.join()
        self.observer.join()

    def server_request(self, environ, start_response)->Iterable[bytes]:
        # https://bugs.python.org/issue16679
        # https://github.com/bottlepy/bottle/blob/f9b1849db4/bottle.py#L984
        path: str = environ["PATH_INFO"].encode("latin-1").decode("utf-8", "ignore")
        pattern = r'/livereload/([0-9]+)/[0-9]+'

        # Broswer want to check whether we have new content
        # Kaguya-sama: Love Is War ?
        if path.startswith('/livereload/'):
            res = re.fullmatch(pattern, path)
            
            if res:
                version = int(res[1])
                start_response(
                    '200 OK',
                    [('Content-Type', 'text/plain')]
                )

                def condition():
                    return self._available_version > version

                # respond broswer as soon as builder update site/
                # else wait for update until 60s over.
                with self._update_cond:
                    self._update_cond.wait_for(condition, timeout=self._poll_response_timeout)
                    return [b"%d" % self._available_version]

        if path == '/':
            start_response(
                '302 Found',
                [('Location', urllib.parse.quote('/index.html'))]
            )
            return []
        elif path.startswith('/'):
            rel_filepath = path.lstrip('/')

            # defense path traversal
            rel_filepath = posixpath.normpath(f'/{rel_filepath}').lstrip('/')
            filepath = self.root / rel_filepath
        else:
            # 404 Not Found
            start_response(
                "404 Not Found",
                [("Content-Type", "text/plain")]
            )
            return [b"404 Not Found"]

        with self._update_cond:
            self._update_cond.wait_for(lambda: self._wanted_version == self._available_version)
            version = self._available_version

        try:
            with open(filepath, 'rb') as f:
                content = f.read()
        except OSError as e:
            # 404 Not Found
            start_response(
                "404 Not Found",
                [("Content-Type", "text/plain")]
            )
            return [b"404 Not Found"]

        # Inject the refresh script into html
        if self._watched_paths and filepath.suffix == ".html":
            content = self._inject_js_into_html(content, version)

        content_length = len(content)

        content_type, _ = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = "application/octet-stream"
        
        start_response(
            "200 OK", [("Content-Type", content_type), ("Content-Length", str(content_length))]
        )
        return wsgiref.util.FileWrapper(io.BytesIO(content))

    # this func is copy from Mkdocs(https://github.com/mkdocs/mkdocs/)
    def _inject_js_into_html(self, content, epoch):
        try:
            body_end = content.rindex(b"</body>")
        except ValueError:
            body_end = len(content)
        
        # The page will reload if the livereload poller returns a newer version than what it knows.
        # The other timestamp becomes just a unique identifier for the initiating page.
        script = _SCRIPT_TEMPLATE.substitute(epoch=epoch, request_id=_get_timestamp())
        return b"%b<script>%b</script>%b" % (
            content[:body_end],
            script.encode(),
            content[body_end:],
        )


class _Handler(wsgiref.simple_server.WSGIRequestHandler):
    def log_request(self, code = "-", size = "-"):
        level = logging.DEBUG if str(code) == '200' else logging.WARNING
        logger.log(level, f'{self.requestline} code {code}')

    def log_message(self, format, *args):
        logger.debug(format, *args)

def _get_timestamp():
    return round(time.monotonic() * 1000)