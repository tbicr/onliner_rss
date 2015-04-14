import logging

from flask import Flask, request, redirect, url_for, render_template, Response
from flask.ext.cache import Cache
from werkzeug.contrib.atom import AtomFeed

from parser import parse_topic, parse_icon


BASE = 'http://forum.onliner.by'
MAX_ITEMS = 20
CACHE_TYPE = 'simple'


app = Flask(__name__)
app.config.from_object(__name__)
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.INFO)
cache = Cache(app)


def _args_cache_key():
    return 'view/{}/{}'.format(request.path, request.args.get('url'))


@app.route('/')
def home():
    if 'url' in request.args:
        return redirect(url_for('feed', url=request.args['url']))
    return render_template('home.html')


@app.route('/feed.atom')
@cache.cached(timeout=5 * 60, key_prefix=_args_cache_key)
def feed():
    title, messages = parse_topic(BASE, request.args.get('url'), MAX_ITEMS)
    feed = AtomFeed(title, feed_url=request.url, url=request.url_root, icon=url_for('favicon'))
    for message in messages:
        feed.add(**message)
    return feed.get_response()


@app.route('/favicon.ico')
@cache.cached(timeout=24 * 60 * 60)
def favicon():
    return Response(**parse_icon(BASE))
