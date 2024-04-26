#!/usr/bin/python3

import argparse
import requests
import json
import os
import re
import datetime
import base64

WORKI_DIR  = os.path.dirname(os.path.realpath(__file__))
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0'
IS_DEBUG   = False

APIS = {
	"en": {
		"language": "en",
		"mediagen": "southpark.intl",
		"domain": "https://southparkstudios.com",
		"domapi": "https://southparkstudios.com",
		"uri": "/seasons/south-park/",
		"html_links": False,
		"has_ads": True,
	},
	"es": {
		"language": "es",
		"mediagen": "southpark.intl",
		"domain": "https://southparkstudios.com",
		"domapi": "https://southparkstudios.com",
		"uri": "/es/seasons/south-park/",
		"html_links": False,
		"has_ads": True,
	},
	"de": {
		"language": "de",
		"mediagen": "southpark.intl",
		"domain": "https://www.southpark.de",
		"domapi": "https://www.southpark.de",
		"uri": "/seasons/south-park/",
		"html_links": True,
		"has_ads": False,
	},
	"se": {
		"language": "se",
		"mediagen": "southpark.intl",
		"domain": "https://southparkstudios.nu",
		"domapi": "https://www.southparkstudios.nu",
		"uri": "/seasons/south-park/",
		"html_links": False,
		"has_ads": False,
	},
	"eu": {
		"language": "en",
		"mediagen": "southpark.intl",
		"domain": "https://www.southparkstudios.com",
		"domapi": "https://www.southparkstudios.com",
		"uri": "/seasons/south-park/",
		"html_links": False,
		"has_ads": False,
	},
	"br": {
		"language": "br",
		"mediagen": "southpark.intl",
		"domain": "https://www.southparkstudios.com.br",
		"domapi": "https://www.southparkstudios.com.br",
		"uri": "/seasons/south-park/",
		"html_links": True,
		"has_ads": False,
	},
	"lat": {
		"language": "lat",
		"mediagen": "southpark.intl",
		"domain": "https://www.southpark.lat",
		"domapi": "https://www.southpark.lat",
		"uri": "/seasons/south-park/",
		"html_links": True,
		"has_ads": False,
	}
}

def log_debug(msg):
	if IS_DEBUG:
		print("[D] {}".format(msg))

def log_struct(data):
	if IS_DEBUG:
		print(json.dumps(data, indent=4))

def _http_get(url, is_json=False, referer=None):
	if len(url) < 1:
		return None
	headers = {
		'User-Agent': USER_AGENT,
	}
	if referer:
		headers['Referer'] = referer
	resp = requests.get(url, headers=headers)
	log_debug("http get: {0}".format(url))
	if is_json:
		return resp.json()
	return resp.text

def write_data(path, data):
	with open(path,'w') as output:
		output.truncate()
		output.write(data)

def write_json(path, data):
	with open(path, 'w') as fp:
		fp.truncate()
		json.dump(data, fp, indent=4)

def read_json(path):
	with open(path, 'r') as fp:
		return json.load(fp)

def _dk(obj, keys, default=None):
	if not isinstance(obj, list) and not isinstance(obj, dict):
		return default
	for k in keys:
		if not isinstance(k, int) and "|" in k and isinstance(obj, list):
			t = k.split("|")
			found = None
			for o in obj:
				if t[0] not in o:
					return default
				elif o[t[0]] == t[1]:
					found = o
					break
			if found == None:
				log_debug("not found: {} -> {}".format(k, keys).replace("'", '"'))
				return default
			obj = found
		elif isinstance(obj, dict) and k not in obj:
			log_debug("not found: {} -> {}".format(k, keys).replace("'", '"'))
			return default
		elif isinstance(obj, list) and isinstance(k, int) and k >= len(obj):
			log_debug("not found: {} -> {}".format(k, keys).replace("'", '"'))
			return default
		else:
			obj = obj[k]
	return obj

def _make_episode(data, season, episode, lang):
	has_ads  = APIS[lang]["has_ads"]
	domapi   = APIS[lang]["domapi"]
	mediagen = APIS[lang]["mediagen"]

	ep = {
		"image":   _dk(data, ["media", "image", "url"], ""),
		"uuid":    _dk(data, ["id"], ""),
		"details": _dk(data, ["meta", "description"], ""),
		"date":    _dk(data, ["meta", "date"], ""),
		"title":   _dk(data, ["meta", "subHeader"], ""),
		"url":     _dk(data, ["url"], ""),
		"season":  "{}".format(season  + 1),
		"episode": "{}".format(episode + 1),
		"mediagen": []
	}

	try:
		args = "uri=mgid:arc:episode:{mediagen}:{uuid}&configtype=edge&ref={dom}{ref}".format(mediagen=mediagen, uuid=ep["uuid"], dom=domapi, ref=ep["url"])
		url  = "https://media.mtvnservices.com/pmt/e1/access/index.html?{args}".format(args=args)
		service = _http_get(url, True)
		items = _dk(service, ["feed", "items"], [])
		i = 0
		urls = []
		for url in items:
			items[i] = _dk(url, ["group", "content"], "").replace("&device={device}", "") + "&format=json&acceptMethods=hls"
			i += 1
		if len(items) > 0:
			urls = items
		ep["mediagen"] = urls
	except Exception as e:
		log_debug("http get: {0} {1}".format(url, e))

	ep["mediagen"] = list(filter(None, ep["mediagen"]))

	print("s{:<2}e{:<2} len:{}: {}".format(ep["season"], ep["episode"], len(ep["mediagen"]), ep["title"]))
	i = 0
	for url in ep["mediagen"]:
		ep["mediagen"][i] = base64.b64encode(url.encode('ascii')).decode('ascii')
		i += 1
	log_struct(ep)

	return ep

def _has_extra(x):
	return "loadMore" in x and x["loadMore"] != None and "type" in x and x["type"] == "video-guide"

def _unique_episodes(eps):
	res = []
	hasep = []
	for ep in eps:
		title = _dk(ep, ["meta", "subHeader"], None),
		if title is None or title in hasep:
			continue
		hasep.append(title)
		res.append(ep)
	return res

def _parse_episodes(data, season, lang, inverted, referer_url):
	domapi = APIS[lang]["domapi"]
	print("parsing episodes from season", season + 1)
	extra = []
	lists = _dk(data,["children", "type|MainContainer", "children"], [])
	if lang in ["en", "es", "eu"]:
		lists = list(filter(lambda x: "type" in x and x["type"] == "LineList", lists))
		extra = list(filter(lambda x: _has_extra(x), [ _dk(s, ["props"], []) for s in lists ]))
		lists = list(filter(lambda x: len(x) > 0 and "url" in x[0], [ _dk(s, ["props", "items"], []) for s in lists ]))[0]
	elif lang in ["se", "de", "br", "lat"]:
		lists = list(filter(lambda x: "type" in x and x["type"] == "LineList" and "type" in x["props"] and x["props"]["type"] == "video-guide", lists))
		if _dk(lists[0], ["props", "loadMore", "url"], "") != "":
			extra.append(_dk(lists[0], ["props"], {}))
		lists = _dk(lists[0], ["props", "items"], [])
		if len(lists) > 0 and _dk(lists[0], ["meta", "subHeader"], None) == None:
			return []
	else:
		return []

	lists = _unique_episodes(lists)
	n_episodes = len(lists)
	lists = [_make_episode(lists[i], season, n_episodes - i - 1 if inverted else i, lang) for i in range(0, len(lists))]

	if len(extra) > 0:
		url = _dk(extra[0], ["loadMore", "url"], "")
		if len(url) > 0:
			extra = _http_get(domapi + url.replace(':', '%3A'), True, referer_url)
			if extra != None:
				n_extras = len(extra["items"])
				lists.extend([_make_episode(extra["items"][i], season, (n_extras - i - 1 if inverted else i) + n_episodes, lang) for i in range(0, n_extras)])
		else:
			raise Exception("Cannot fetch all episodes")

	if inverted:
		lists.reverse()

	return lists

def _download_data(url, html_links):
	webpage = _http_get(url)
	if IS_DEBUG:
		write_data("debug-data.html", webpage)

	if "window.__DATA__" in webpage:
		dataidx  = webpage.index("window.__DATA__")
		data     = webpage[dataidx:]
		endidx   = data.index("};")
		equalidx = data.index("=")
		data     = data[equalidx + 1:endidx + 1].strip()
		data     = json.loads(data, strict=False)

		if IS_DEBUG:
			write_json("debug-data.json", data)

		if html_links:
			links = re.findall(r"href=\"/seasons/south-park/[\w]+/[\w]+-\d+", webpage, flags=re.M)
			links = [x.split('"')[1] for x in links]
			data["links_found"] = [None]
			data["links_found"].extend(links)
		return data
	return None

def generate_data(lang, old_data):
	domain     = APIS[lang]["domain"]
	uri        = APIS[lang]["uri"]
	html_links = APIS[lang]["html_links"]

	data = _download_data(domain + uri, html_links)
	main = _dk(data,["children", "type|MainContainer", "children"])
	seasons_urls = []
	if "links_found" in data:
		log_debug("using links")
		seasons_urls = data["links_found"]
	else:
		seasons_urls = [ _dk(s, ["url"]) for s in _dk(main, ["type|SeasonSelector", "props", "items"], [])]

	log_debug("seasons: {}".format(len(seasons_urls)))

	seasons = []

	index = 0
	for url in seasons_urls:
		index += 1
		referer = None
		if url != None:
			referer = domain + url
			data = _download_data(domain + url, False)
		lists = _parse_episodes(data, index - 1, lang, False, referer)
		if len(lists) < 1 and len(seasons) < 1:
			continue
		seasons.append(lists)
		if old_data:
			break

	return {
		"created": "{}".format(datetime.datetime.now()),
		"seasons": seasons
	}	

def generate_file(lang, only_last_season):
	old_data = None
	if only_last_season:
		old_data = read_json("addon-data-{}.json".format(lang))
	data = generate_data(lang, old_data)
	write_json("addon-data-{}.json".format(lang), data)

def main():
	global IS_DEBUG

	parser = argparse.ArgumentParser()
	parser.add_argument('--debug', action='store_true', default=False, help='enable debug')
	parser.add_argument('--only-last-season', action='store_true', default=False, help='updates only the last season')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('--en', action='store_true', default=False, help='language english (north america)')
	group.add_argument('--es', action='store_true', default=False, help='language spanish (north america)')
	group.add_argument('--de', action='store_true', default=False, help='language german (germany)')
	group.add_argument('--se', action='store_true', default=False, help='language swedish (sweden)')
	group.add_argument('--eu', action='store_true', default=False, help='language english (europe)')
	group.add_argument('--br', action='store_true', default=False, help='language portuguese (brazil)')
	group.add_argument('--lat', action='store_true', default=False, help='language spanish (latin america)')
	args = parser.parse_args()

	os.chdir(WORKI_DIR)

	IS_DEBUG = args.debug

	if args.en:
		generate_file("en", args.only_last_season)
	elif args.es:
		generate_file("es", args.only_last_season)
	elif args.de:
		generate_file("de", args.only_last_season)
	elif args.se:
		generate_file("se", args.only_last_season)
	elif args.eu:
		generate_file("eu", args.only_last_season)
	elif args.br:
		generate_file("br", args.only_last_season)
	elif args.lat:
		generate_file("lat", args.only_last_season)
	else:
		print("nothing was selected..")

if __name__ == '__main__':
	main()
