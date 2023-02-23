import os

from flask import Flask
from flask import request
from mastodon import Mastodon

from digest import fetch_digest
from renderer import render
from scorers import get_scorers
from thresholds import get_threshold_from_name


app = Flask(__name__)
mastodon_base_url = os.getenv("MASTODON_BASE_URL").strip().rstrip("/")
mst = Mastodon(
    access_token=os.getenv("MASTODON_TOKEN"),
    api_base_url=mastodon_base_url,
)

DEFAULT_HOURS = 12
DEFAULT_SCORER = 'SimpleWeighted'
DEFAULT_THRESHOLD = 'normal'
DEFAULT_TIMELINE = 'home'
SCORERS = get_scorers()


@app.route('/')
def index():
    # Get feed data
    # TODO: two different feeds. Probably AJAX-y load them instead.
    # Render JINJA template
    return render({}, 'comparison')


@app.route('/feed/generate', methods=['POST'])
def get_feed():
    # POST data
    jdata = request.get_json()
    hours = int(jdata.get('hours')) or DEFAULT_HOURS
    scorer = SCORERS[jdata.get('scorer') or DEFAULT_SCORER]()
    threshold = get_threshold_from_name(jdata.get('threshold') or DEFAULT_THRESHOLD)
    timeline = jdata.get('timeline') or DEFAULT_TIMELINE
    digest_data = fetch_digest(mst, hours, scorer, threshold, mastodon_base_url, timeline)
    # From args return feed HTML or JSON
    return render(digest_data, 'simple')
