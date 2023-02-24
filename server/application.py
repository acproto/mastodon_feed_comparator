import os

from flask import Flask
from flask import request
from mastodon import Mastodon

from digest import fetch_digest
from renderer import render
from scorers import AllFactorsWeightedScorer
from thresholds import get_threshold_from_name


app = Flask(__name__)
mastodon_base_url = os.getenv("MASTODON_BASE_URL").strip().rstrip("/")
mst = Mastodon(
    access_token=os.getenv("MASTODON_TOKEN"),
    api_base_url=mastodon_base_url,
)

DEFAULT_HOURS = 12
DEFAULT_THRESHOLD = 'normal'
DEFAULT_TIMELINE = 'home'


@app.route('/')
def index():
    # TODO: send context to the homepage template for the first two default feeds
    # instead of hardcoding them in the client.
    return render({}, template='comparison.html.jinja')


@app.route('/feed/generate', methods=['POST'])
def get_feed():
    # POST data
    jdata = request.get_json()
    hours = int(jdata.get('hours')) or DEFAULT_HOURS
    scorer = AllFactorsWeightedScorer(
        favourites_weight=float(jdata.get('favourites_weight') or 0),
        reblogs_weight=float(jdata.get('reblogs_weight') or 0),
        replies_weight=float(jdata.get('replies_weight') or 0),
        inverse_follower_boost=bool(int(jdata.get('inverse_follower_boost') or 0)))
    threshold = get_threshold_from_name(jdata.get('threshold') or DEFAULT_THRESHOLD)
    timeline = jdata.get('timeline') or DEFAULT_TIMELINE
    digest_data = fetch_digest(mst, mastodon_base_url, hours, scorer, threshold, timeline, limit=5)
    # From args return feed HTML or JSON
    return render(digest_data, template='digest.html.jinja')
