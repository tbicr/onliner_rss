import io
import logging.handlers
import urllib.parse
from traceback import TracebackException

from flask import Flask, request, redirect, url_for, render_template, Response
from flask.ext.cache import Cache
from werkzeug.contrib.atom import AtomFeed

from parser import parse_topic, parse_icon


class DetailedErrorApp(Flask):

    def log_exception(self, exc_info):
        self.logger.error('Exception on %s [%s]' % (
            request.url,
            request.method
        ), exc_info=exc_info)


app = DetailedErrorApp(__name__)
app.config.from_object('settings')
cache = Cache(app)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
app.logger.addHandler(stream_handler)


class DetailedErrorFormatter(logging.Formatter):

    def formatException(self, ei):
        sio = io.StringIO()
        tb = ei[2]

        etype, value, tb, limit, file, chain = ei[0], ei[1], tb, None, sio, True
        for line in TracebackException(type(value), value, tb, limit=limit, capture_locals=True).format(chain=chain):
            print(line, file=file, end='')

        s = sio.getvalue()
        sio.close()
        if s[-1:] == '\n':
            s = s[:-1]
        return s

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        exc_text = None
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
        if exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s

smtp_handler = logging.handlers.SMTPHandler(**app.config['ERROR_EMAIL'])
smtp_handler.setLevel(logging.ERROR)
smtp_handler.setFormatter(DetailedErrorFormatter())
app.logger.addHandler(smtp_handler)


def _args_cache_key():
    url = request.args.get('url')
    topic = url and urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('t', [None])[0]
    return 'view/{}/{}'.format(request.path, topic)


@app.route('/')
def home():
    if 'url' in request.args:
        return redirect(url_for('feed', url=request.args['url']))
    return render_template('home.html')


@app.route('/feed.atom')
@cache.cached(timeout=5 * 60, key_prefix=_args_cache_key)
def feed():
    title, messages = parse_topic(app.config.get('BASE'), request.args.get('url'), app.config.get('MAX_ITEMS'))
    feed = AtomFeed(title, feed_url=request.url, url=request.url_root, icon=url_for('favicon'))
    for message in messages:
        feed.add(**message)
    return feed.get_response()


@app.route('/favicon.ico')
@cache.cached(timeout=24 * 60 * 60)
def favicon():
    return Response(**parse_icon(app.config.get('BASE')))
