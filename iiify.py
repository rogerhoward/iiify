#!/usr/bin/env python

import os.path
from flask import Flask, send_file, jsonify, abort, request
from flask.ext.cors import CORS
from iiif2 import iiif, web
from configs import options, cors, cache_root, media_root, cache_expr

app = Flask(__name__)
cors = CORS(app) if cors else None


def resolve(identifier):
    """Resolves a iiif identifier to the resource's path on disk."""
    return os.path.join(media_root, identifier)


@app.route('/<identifier>/info.json')
def image_info(identifier):
    try:
        return jsonify(web.info(request.url, resolve(identifier), identifier))
    except:
        abort(400)


@app.route('/<identifier>/<region>/<size>/<rotation>/<quality>.<fmt>')
def image_processor(identifier, **kwargs):
    cache_path = os.path.join(cache_root, web.urihash(request.path))

    if os.path.exists(cache_path):
        mime = iiif.type_map[kwargs.get('fmt')]['mime']
        return send_file(cache_path, mimetype=mime)

    try:
        params = web.Parse.params(identifier, **kwargs)
        tile = iiif.IIIF.render(resolve(identifier), **params)
        tile.save(cache_path, tile.mime)
        return send_file(tile, mimetype=tile.mime)
    except:
        abort(400)


@app.after_request
def add_header(response):
    response.cache_control.max_age = cache_expr  # minutes
    return response

if __name__ == '__main__':
    app.run(**options)
