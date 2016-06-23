import logging.handlers
import urllib.parse

from flask import Flask, request, redirect, url_for, render_template, Response
from flask.ext.cache import Cache
from werkzeug.contrib.atom import AtomFeed

from parser import parse_topic, parse_icon


app = Flask(__name__)
app.config.from_object('settings')
cache = Cache(app)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
app.logger.addHandler(stream_handler)

smtp_handler = logging.handlers.SMTPHandler(**app.config['ERROR_EMAIL'])
smtp_handler.setLevel(logging.ERROR)
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
