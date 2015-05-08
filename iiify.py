#!/usr/bin/env python

from flask import Flask, send_file, jsonify, abort, request
from PIL import Image, ImageFilter
import StringIO, os, re, hashlib

app = Flask(__name__)

type_map = {
	'jpg': {'im': 'JPEG', 'mime' : 'image/jpeg'},
	'tif': {'im': 'TIFF', 'mime' : 'image/tiff'},
	'png': {'im': 'PNG', 'mime' : 'image/png'},
	'gif': {'im': 'GIF', 'mime' : 'image/gif'},
	'jp2': {'im': 'JPEG 2000', 'mime' : 'image/jp2'},
	'pdf': {'im': 'PDF', 'mime' : 'application/pdf'},
	'webp': {'im': 'WEBP', 'mime' : 'image/webp'},
}

# path to the parent directory of the iiify.py application
project_root = os.path.dirname(os.path.abspath(__file__))

# path to where media is stored - make it if it doesn't exist
media_root = os.path.join(project_root,'media')
if not os.path.exists(media_root):
    os.makedirs(media_root)

# path to where the disk cache is stored - make it if it doesn't exist
cache_root = os.path.join(project_root,'cache')
if not os.path.exists(cache_root):
    os.makedirs(cache_root)

# boxclamp accepts a four-tuple consisting of the four coordinates of a box 
# and a maximum w and h, and conforms the box to the max dimensions.
# boxclamp returns false if box values are impossible, eg. box[2] < box[0]
def boxclamp(box,w,h):
	# Stash tuple components in local variables, since tuples are immutable
	# and to keep statements somewhat readable
	a = box[0]
	b = box[1]
	c = box[2]
	d = box[3]

	if c < a:
		return False
	if d < b:
		return False

	# Clamp horizontal components to range of 0..w
	a = 0 if a < 0 else a
	a = w if a > w else a

	c = 0 if c < 0 else c
	c = w if c > w else c

	# Clamp vertical components to range of 0..h
	b = 0 if b < 0 else b
	b = h if b > h else b

	d = 0 if d < 0 else d
	d = h if d > h else d

	return (a,b,c,d)

# get_path_from takes an image identifier and returns an absolute path
# suitable for loading in Pillow or otherwise reading and writing
def get_path_from(identifier):	
	return os.path.join(media_root, identifier)

def handle_region(im, command):
	if command == 'full':
		# return without modifying im
		return im
	elif command.startswith('pct:'):
		# Not using regexes here - extracting decimals makes my head hurt.

		# split string into components using , as delimiter
		coords = command[4:].split(',')
		
		# expecting four components - if not four, abort 400
		if len(coords) != 4:
			abort(400)

		# stuff width and height into short vars for readability
		w = im.size[0]
		h = im.size[1]
	
		# Convert array of strings representing float percents into
		# four-tuple of integer pixel values for PIL cropping
		# On failure, abort 400
		try:
			box = (int(round(float(coords[0])/100 * w)), int(round(float(coords[1])/100 * h)),int(round(float(coords[0])/100 * w)) + int(round(float(coords[2])/100 * w)), int(round(float(coords[1])/100 * h))+ int(round(float(coords[3])/100 * h)))
			box = boxclamp(box,w,h)

			# if box fails boxclamp(), abort with 400
			if box is False:
				abort(400)

			im = im.crop(box)
			return im
		except:
			abort(400)

	else:
		# Not using regexes here - extracting decimals makes my head hurt.

		# split string into components using , as delimiter
		coords = command.split(',')

		# expecting four components - if not four, abort 400
		if len(coords) != 4:
			abort(400)

		# stuff width and height into short vars for readability
		w = im.size[0]
		h = im.size[1]

		# Convert array of strings representing x,y,w,h integers into
		# four-tuple of integer pixel values for PIL cropping
		# On failure, abort 400
		try:
			box = (int(coords[0]),int(coords[1]), int(coords[0]) + int(coords[2]), int(coords[1]) + int(coords[3]))
			box = boxclamp(box,w,h)

			# if box fails boxclamp(), abort with 400
			if box is False:
				abort(400)

			im = im.crop(box)
			return im
		except:
			abort(400)

	abort(400)

def handle_size(im, command):
	# stuff width and height into short vars for readability
	w = im.size[0]
	h = im.size[1]

	if command == 'full':
		# return without modifying im
		return im
	elif command.endswith(','):
		# scale to width, preserving aspect ratio
		try:
			width = int(command.split(',')[0])
			height = int(round(float(h) * float(width / float(w))))
			im = im.resize((width, height), Image.BICUBIC)
			return im
		except:
			abort(400)
	elif command.startswith(','):
		# scale to height, preserving aspect ratio
		try:
			height = int(command.split(',')[1])
			width = int(round(float(w) * float(height / float(h))))
			im = im.resize((width, height), Image.BICUBIC)
			return im
		except:
			abort(400)
	elif command.startswith('pct:'):
		# scale to percentage of original dimensions, preserving aspect ratio
		try:
			pct = float(command.split(':')[1])
			print pct
			width = int(round(w * pct / 100))
			height = int(round(h * pct / 100))
			im = im.resize((width, height), Image.BICUBIC)
			return im
		except:
			abort(400)
	elif command.startswith('!'):
		# scale to fit box, preserving aspect ratio
		try:
			coords = command[1:].split(',')
			width = int(coords[0])
			height = int(coords[1])
			im.thumbnail((width, height), Image.BICUBIC)
			return im
		except:
			abort(400)
	else:
		# scale to absolute dimensions, without preserving aspect ratio
		try:
			coords = command.split(',')
			width = int(coords[0])
			height = int(coords[1])
			im = im.resize((width, height), Image.BICUBIC)
			return im
		except:
			abort(400)

	abort(400)

def handle_rotation(im, command):

	# If demanded, flip about verticle axis, and then strip ! from command
	if command.startswith('!'):
		im = im.transpose(Image.FLIP_LEFT_RIGHT)
		command = command[1:]

	# If rotation value is in range 0..360, rotate image, otherwise abort with 400
	try:
		rotation_value = int(command)
		if rotation_value >= 0 and rotation_value <= 360:
			im = im.rotate( rotation_value, resample = Image.BICUBIC, expand=1 )
		else:
			abort(400)
	except:
		abort(400)

	return im

def handle_quality(im, command):
	try:
		if command == 'color':
			im = im.convert('RGB')
			return im
		elif command == 'gray':
			im = im.convert('L')
			return im
		elif command == 'bitonal':
			im = im.convert('1')
			return im
		elif command == 'default':
			return im
		else:
			abort(400)
	except:
		abort(400)

	abort(400)

def cache_entry(path):
	path_hash = hashlib.md5(path.encode('utf-8')).hexdigest()
	cache_path = os.path.join(cache_root, path_hash)
	return cache_path

def add_to_cache(path):
	path_hash = hashlib.md5(path.encode('utf-8')).hexdigest()
	cache_path = os.path.join(cache_root, path_hash)
	if os.path.exists(cache_path):
		return cache_path
	else:
		return False

# http://127.0.0.1:5000/g9_20090806_0143.jpg/info.json
@app.route('/<identifier>/info.json')
def image_info(identifier):
	try:
		this_file = get_path_from(identifier)
		im = Image.open(this_file)
	except:
		abort(400)

	this_info_dict = {}

	this_info_dict['@id'] = '%s%s' % (request.url_root, identifier)
	this_info_dict['@context'] = 'http://iiif.io/api/image/2/context.json'
	this_info_dict['protocol'] = 'http://iiif.io/api/image'
	this_info_dict['width'] = im.size[0]
	this_info_dict['height'] = im.size[1]
	this_info_dict['profile'] = [ 'http://iiif.io/api/image/2/level2.json' ]
	this_info_dict['tiles'] = [ {"width" : 512, "scaleFactors" : [1,2,4,8,16]} ]

	# Should implement the sizes parameter in conjunction with caching layer
	# this_info_dict['sizes'] = [{'width' : im.size[0], 'height' : im.size[1]}]

	return jsonify(this_info_dict)


# http://127.0.0.1:5000/g9_20090806_0143.jpg/full/600,/!90/80.jpg
@app.route('/<identifier>/<region>/<size>/<rotation>/<quality>.<format>')
def image_processor(identifier, region, size, rotation, quality, format):

	# Abort early with a 400 if format requested isn't supported
	if format not in type_map:
		abort(400)

	cache_path = cache_entry(request.path)

	# Check cache
	if os.path.exists(cache_path):
		# If result has already been cached, serve from cache
		print 'cached: %s' % (cache_path)
		return send_file(cache_path, mimetype=type_map[format]['mime'])

	else:
		# If result isn't in cache, create result
		print 'not cached: %s' % (cache_path)

		# Load source file into Pillow object, or error 400
		try:
			this_file = get_path_from(identifier)
			im = Image.open(this_file)
		except:
			abort(400)

		# Process Image object step-by-step
		im = handle_region(im, region)
		im = handle_size(im, size)
		im = handle_rotation(im, rotation)
		im = handle_quality(im, quality)

		# Unsharp Mask to increase local contrast in the image
		im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=3))

		# Saving for later - using StringIO to write directly to http result
		# img_io = StringIO.StringIO()	
		# im.save(img_io, type_map[format]['im'])
		# img_io.seek(0)
		# return send_file(img_io, mimetype=type_map[format]['mime'])

		# Revisit this for optimizations
		# Appears to cause an unnecessary read from disk, 
		# but may be handled automagically by mmap
		im.save(cache_path, type_map[format]['im'])
		return send_file(cache_path, mimetype=type_map[format]['mime'])

@app.after_request
def add_header(response):
	# Force upstream caches to refresh at 100 minute intervals
    response.cache_control.max_age = 100

    # Enable CORS to allow cross-domain loading of tilesets from this server
    # Especially useful for SeaDragon viewers running locally
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response

if __name__ == '__main__':
	app.debug = True
	app.run()
