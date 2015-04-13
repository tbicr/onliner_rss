from functools import lru_cache
import logging

from flask import Flask, request, redirect, url_for, Response, render_template
from werkzeug.contrib.atom import AtomFeed

from parser import parse_topic, parse_icon


MAX_ITEMS = 50


app = Flask(__name__)
app.config.from_object(__name__)
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.INFO)


@app.route('/')
def home():
    if 'url' in request.args:
        return redirect(url_for('feed', url=request.args['url']))
    return render_template('home.html')


@app.route('/feed.atom')
def feed():
    title, messages = parse_topic(request.args.get('url'), MAX_ITEMS)
    feed = AtomFeed(title, feed_url=request.url, url=request.url_root, icon=url_for('favicon'))
    for message in messages:
        feed.add(**message)
    return feed.get_response()


@app.route('/favicon.ico')
@lru_cache()
def favicon():
    return Response(parse_icon(), mimetype='image/x-icon')
