from __future__ import unicode_literals
import frappe
from frappe import _
import json, math, time, pytz
from .exceptions import ShopcluesError
from frappe.utils import get_request_session, get_datetime, get_time_zone
from vlog import vwrite

def check_api_call_limit(response):
	"""
		This article will show you how to tell your program to take small pauses
		to keep your app a few API calls shy of the API call limit and
		to guard you against a 429 - Too Many Requests error.

		ref : https://docs.shopclues.com/api/introduction/api-call-limit
	"""
	if response.headers.get("HTTP_X_SHOPCLUES_SHOP_API_CALL_LIMIT") == 39:
		time.sleep(10)    # pause 10 seconds

def get_shopclues_settings():
	d = frappe.get_doc("Shopclues Settings")
	
	if d.shopclues_url:
		if d.app_type == "Private" and d.password:
			d.password = d.get_password()
		return d.as_dict()
	else:
		frappe.throw(_("Shopclues store URL is not configured on Shopclues Settings"), ShopcluesError)

def get_request(path, settings=None):
	if not settings:
		settings = get_shopclues_settings()

	s = get_request_session()
	url = get_shopclues_url(path, settings)
	r = s.get(url, headers=get_header(settings))
	check_api_call_limit(r)
	r.raise_for_status()
	return r.json()


def post_request(path, settings, params=None):
	shopclues_settings = settings.__dict__
	import dateutil.parser
	last_sync_datetime = dateutil.parser.parse(shopclues_settings.get("last_sync_datetime"))
	from datetime import datetime
	epoch = datetime(1970,1,1)
	curr_time = datetime.now()
	time_from = int((last_sync_datetime - epoch).total_seconds())
	time_to = int((curr_time - epoch).total_seconds())
	def get_shopclues_url(route_name,params=None):
		url = ""
		routes = {
			"get_all_orders": "http://developer.shopclues.com/api/v1/order",
			"get_order_by_id": "http://developer.shopclues.com/api/v1/order"
		}
		if route_name == "get_all_orders":
			url = routes.get(route_name)
			url = "%s?time_from=%s&time_to=%s" % (url,time_from,time_to)
		if params:
			if route_name == 'get_order_by_id':
				url = "%s/%s" % (url,params.get('order_id'))
		return url

	shopclues_url = get_shopclues_url(path,params)
	# >> getting oAuth token
	s = get_request_session()
	url = "https://auth.shopclues.com/loginToken.php"
	password = shopclues_settings.get("password")
	import hashlib
	md5pwd = hashlib.md5(password.encode("utf")).hexdigest()
	credentials = {
			"username":shopclues_settings.get("email"),
			# "password":"ea85d75bc4f647a4b50c05d95ba42f1f",
			'password':md5pwd,
			"client_id":shopclues_settings.get("client_id"),
			"client_secret":shopclues_settings.get("client_secret"),
			"grant_type":"password"
			}
	r = s.post(url, data=json.dumps(credentials), headers={'Content-Type': 'application/json'})
	r.raise_for_status()
	# << getting oAuth token
	try:
		auth_tok = "%s" % r.json().get("access_token")
		result = s.get(shopclues_url, headers = {'Authorization':auth_tok,'Content-Type': 'application/json'})
	except Exception, e:
		vwrite("in exception ")
		vwrite(e)
	result.raise_for_status()
	return result.json()
# def post_request(path, data):
# 	settings = get_shopclues_settings()
# 	s = get_request_session()
# 	url = get_shopclues_url(path, settings)
# 	r = s.post(url, data=json.dumps(data), headers=get_header(settings))
# 	check_api_call_limit(r)
# 	r.raise_for_status()
# 	return r.json()

def put_request(path, data):
	settings = get_shopclues_settings()
	s = get_request_session()
	url = get_shopclues_url(path, settings)
	r = s.put(url, data=json.dumps(data), headers=get_header(settings))
	check_api_call_limit(r)
	r.raise_for_status()
	return r.json()

def delete_request(path):
	s = get_request_session()
	url = get_shopclues_url(path)
	r = s.delete(url)
	r.raise_for_status()

def get_shopclues_url(path, settings):
	if settings['app_type'] == "Private":
		return 'https://{}:{}@{}/{}'.format(settings['api_key'], settings['password'], settings['shopclues_url'], path)
	else:
		return 'https://{}/{}'.format(settings['shopclues_url'], path)

def get_header(settings):
	header = {'Content-Type': 'application/json'}

	if settings['app_type'] == "Private":
		return header
	else:
		header["X-Shopclues-Access-Token"] = settings['access_token']
		return header

def get_filtering_condition():
	shopclues_settings = get_shopclues_settings()
	if shopclues_settings.last_sync_datetime:

		last_sync_datetime = get_datetime(shopclues_settings.last_sync_datetime)
		timezone = pytz.timezone(get_time_zone())
		timezone_abbr = timezone.localize(last_sync_datetime, is_dst=False)

		return 'updated_at_min="{0} {1}"'.format(last_sync_datetime.strftime("%Y-%m-%d %H:%M:%S"), timezone_abbr.tzname())
	return ''

def get_total_pages(resource, ignore_filter_conditions=False):
	filter_condition = ""

	if not ignore_filter_conditions:
		filter_condition = get_filtering_condition()
	
	count = get_request('/admin/{0}&{1}'.format(resource, filter_condition))
	return int(math.ceil(count.get('count', 0) / 250))

def get_country():
	return get_request('/admin/countries.json')['countries']

def get_shopclues_items(ignore_filter_conditions=False):
	shopclues_products = []

	filter_condition = ''
	if not ignore_filter_conditions:
		filter_condition = get_filtering_condition()

	for page_idx in xrange(0, get_total_pages("products/count.json?", ignore_filter_conditions) or 1):
		shopclues_products.extend(get_request('/admin/products.json?limit=250&page={0}&{1}'.format(page_idx+1,
			filter_condition))['products'])

	return shopclues_products

def get_shopclues_item_image(shopclues_product_id):
	return get_request("/admin/products/{0}/images.json".format(shopclues_product_id))["images"]

def get_shopclues_orders(ignore_filter_conditions=False):
	shopclues_orders = []

	filter_condition = ''

	if not ignore_filter_conditions:
		filter_condition = get_filtering_condition()

	for page_idx in xrange(0, get_total_pages("orders/count.json?status=any", ignore_filter_conditions) or 1):
		shopclues_orders.extend(get_request('/admin/orders.json?status=any&limit=250&page={0}&{1}'.format(page_idx+1,
			filter_condition))['orders'])
	return shopclues_orders

def get_shopclues_customers(ignore_filter_conditions=False):
	shopclues_customers = []

	filter_condition = ''

	if not ignore_filter_conditions:
		filter_condition = get_filtering_condition()

	for page_idx in xrange(0, get_total_pages("customers/count.json?", ignore_filter_conditions) or 1):
		shopclues_customers.extend(get_request('/admin/customers.json?limit=250&page={0}&{1}'.format(page_idx+1,
			filter_condition))['customers'])
	return shopclues_customers
