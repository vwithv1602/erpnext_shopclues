from __future__ import unicode_literals
import frappe
from frappe import _
import requests.exceptions
# from .shopclues_requests import post_request, get_request
from .utils import make_shopclues_log
from vlog import vwrite

# def sync_customers():
# 	shopify_customer_list = []
# 	sync_shopify_customers(shopify_customer_list)
# 	frappe.local.form_dict.count_dict["customers"] = len(shopify_customer_list)
#
# 	sync_erpnext_customers(shopify_customer_list)
#
# def sync_shopify_customers(shopify_customer_list):
# 	for shopify_customer in get_shopify_customers():
# 		if not frappe.db.get_value("Customer", {"shopify_customer_id": shopify_customer.get('id')}, "name"):
# 			create_customer(shopify_customer, shopify_customer_list)

def create_customer(parsed_order, shopclues_customer_list):
	cust_id = parsed_order.get("customer_details").get("buyer_id")
	cust_name = parsed_order.get("customer_details").get("buyer_name")
	try:
		customer = frappe.get_doc({
			"doctype": "Customer",
			"name": cust_id,
			"customer_name" : cust_name,
			"shopclues_customer_id": cust_id,
			# "sync_with_shopify": 1,
			# "customer_group": shopclues_settings.customer_group,
			# "territory": frappe.utils.nestedset.get_root_of("Territory"),
			"customer_type": _("Individual")
		})
		customer.flags.ignore_mandatory = True
		customer.insert()
		if customer:
			create_customer_address(parsed_order, cust_id)
			create_customer_contact(parsed_order, cust_id)
		shopclues_customer_list.append(parsed_order.get("customer_details").get("buyer_id"))
		frappe.db.commit()

			
	except Exception, e:
		vwrite("Exception raised in create_customer")
		vwrite(e.message)
		vwrite(parsed_order)
		if e.args[0] and e.args[0].startswith("402"):
			raise e
		else:
			make_shopclues_log(title=e.message, status="Error", method="create_customer", message=frappe.get_traceback(),
				request_data=parsed_order.get("BuyerUserID"), exception=True)
		
def create_customer_address(parsed_order, shopclues_customer):
	if not parsed_order.get("customer_details").get("buyer_name"):
		make_shopclues_log(title=parsed_order.get("customer_details").get("buyer_email"), status="Error", method="create_customer_address", message="No shipping address found for %s" % parsed_order.get("customer_details").get("email"),
					  request_data=parsed_order.get("customer_details").get("buyer_email"), exception=True)
	else:
		try:
			# if shopclues_order.get("ShippingAddress").get("Street1"):
			# 	address_line1 = shopclues_order.get("ShippingAddress").get("Street1").replace("'", "")
			# else:
			# 	address_line1 = shopclues_order.get("ShippingAddress").get("Street1")
			# if shopclues_order.get("ShippingAddress").get("Street2"):
			# 	address_line2 = shopclues_order.get("ShippingAddress").get("Street2").replace("'", "")
			# else:
			# 	address_line2 = shopclues_order.get("ShippingAddress").get("Street2")
			if not frappe.db.get_value("Address",
									   {"shopclues_address_id": parsed_order.get("customer_details").get("buyer_email")}, "name"):
				frappe.get_doc({
					"doctype": "Address",
					"shopclues_address_id": parsed_order.get("customer_details").get("buyer_email"),
					"address_title": parsed_order.get("customer_details").get("buyer_name"),
					"address_type": "Shipping",
					# "address_line1": address_line1,
					# "address_line2": address_line2,
					"city": parsed_order.get("customer_details").get("buyer_city"),
					"state": parsed_order.get("customer_details").get("buyer_state"),
					"pincode": parsed_order.get("customer_details").get("buyer_zipcode"),
					# "country": shopclues_order.get("ShippingAddress").get("Country"),
					"country": None,
					"phone": "NA",
					"email_id": parsed_order.get("customer_details").get("buyer_email"),
					"links": [{
						"link_doctype": "Customer",
						# "link_name": shopclues_order.get("BuyerUserID")
						"link_name": parsed_order.get("customer_details").get("buyer_name")
					}]
				}).insert()
			else:
				frappe.db.sql(
					"""update tabAddress set address_title='%s',address_type='Shipping',address_line1='%s',address_line2='%s',city='%s',state='%s',pincode='%s',country='%s',phone='%s',email_id='%s' where shopclues_address_id='%s' """
					% (parsed_order.get("customer_details").get("buyer_name"), None,
					   None,
					   parsed_order.get("customer_details").get("buyer_city"),
					   parsed_order.get("customer_details").get("buyer_state"), parsed_order.get("customer_details").get("buyer_zipcode"),
					   "India",
					   "NA",
					   parsed_order.get("customer_details").get("buyer_email"),
					   parsed_order.get("customer_details").get("buyer_email")))
				frappe.db.commit()

		except Exception, e:
			vwrite('Exception raised in create_customer_address')
			vwrite(e.message)
			vwrite(parsed_order)
			make_shopclues_log(title=e.message, status="Error", method="create_customer_address",
						  message=frappe.get_traceback(),
						  request_data=shopclues_customer, exception=True)


# create_customer_contact() will create customer contact in tabContact which is used in sending email
# to customer after creation of sales order. Stores firstname,lastname,emailID in tabContact
def create_customer_contact(parsed_order, shopclues_customer):
	cust_name = parsed_order.get("customer_details").get("buyer_name")
	email_id = parsed_order.get("customer_details").get("buyer_email")
	if not cust_name:
		make_shopclues_log(title=email_id, status="Error", method="create_customer_contact", message="Contact not found for %s" % email_id,
					  request_data=email_id, exception=True)
	else:
		try :
			if not frappe.db.get_value("Contact", {"first_name": shopclues_customer}, "name"):
				frappe.get_doc({
					"doctype": "Contact",
					"first_name": shopclues_customer,
					"email_id": email_id,
					"links": [{
						"link_doctype": "Customer",
						# "link_name": shopclues_order.get("BuyerUserID")
						"link_name": cust_name
					}]
				}).insert()
			# else:
			# 	frappe.get_doc({
			# 		"doctype": "Contact",
			# 		"first_name": shopclues_customer,
			# 		"email_id": email_id,
			# 		"links": [{
			# 			"link_doctype": "Customer",
			# 			# "link_name": shopclues_order.get("BuyerUserID")
			# 			"link_name": shopclues_order.get("ShippingAddress").get("Name")
			# 		}]
			# 	}).save()
		except Exception, e:
			vwrite("Exception raised in create_customer_contact")
			vwrite(e.message)
			vwrite(parsed_order)
			make_shopclues_log(title=e.message, status="Error", method="create_customer_contact", message=frappe.get_traceback(),
				request_data=email_id, exception=True)

def get_address_title_and_type(customer_name, index):
	address_type = _("Billing")
	address_title = customer_name
	if frappe.db.get_value("Address", "{0}-{1}".format(customer_name.strip(), address_type)):
		address_title = "{0}-{1}".format(customer_name.strip(), index)
		
	return address_title, address_type 
	
def sync_erpnext_customers(shopify_customer_list):
	shopify_settings = frappe.get_doc("Shopify Settings", "Shopify Settings")
	
	condition = ["sync_with_shopify = 1"]
	
	last_sync_condition = ""
	if shopify_settings.last_sync_datetime:
		last_sync_condition = "modified >= '{0}' ".format(shopify_settings.last_sync_datetime)
		condition.append(last_sync_condition)
	
	customer_query = """select name, customer_name, shopify_customer_id from tabCustomer 
		where {0}""".format(" and ".join(condition))
		
	for customer in frappe.db.sql(customer_query, as_dict=1):
		try:
			if not customer.shopify_customer_id:
				create_customer_to_shopify(customer)
			
			else:
				if customer.shopify_customer_id not in shopify_customer_list:
					update_customer_to_shopify(customer, shopify_settings.last_sync_datetime)
			
			frappe.local.form_dict.count_dict["customers"] += 1
			frappe.db.commit()
		except Exception, e:
			make_shopclues_log(title=e.message, status="Error", method="sync_erpnext_customers", message=frappe.get_traceback(),
				request_data=customer, exception=True)

def create_customer_to_shopify(customer):
	shopify_customer = {
		"first_name": customer['customer_name'],
	}
	
	shopify_customer = post_request("/admin/customers.json", { "customer": shopify_customer})
	
	customer = frappe.get_doc("Customer", customer['name'])
	customer.shopify_customer_id = shopify_customer['customer'].get("id")
	
	customer.flags.ignore_mandatory = True
	customer.save()
	
	addresses = get_customer_addresses(customer.as_dict())
	for address in addresses:
		sync_customer_address(customer, address)

def sync_customer_address(customer, address):
	address_name = address.pop("name")

	shopify_address = post_request("/admin/customers/{0}/addresses.json".format(customer.shopify_customer_id),
	{"address": address})
		
	address = frappe.get_doc("Address", address_name)
	address.shopify_address_id = shopify_address['customer_address'].get("id")
	address.save()
	
def update_customer_to_shopify(customer, last_sync_datetime):
	shopify_customer = {
		"first_name": customer['customer_name'],
		"last_name": ""
	}
	
	try:
		put_request("/admin/customers/{0}.json".format(customer.shopify_customer_id),\
			{ "customer": shopify_customer})
		update_address_details(customer, last_sync_datetime)
		
	except requests.exceptions.HTTPError, e:
		if e.args[0] and e.args[0].startswith("404"):
			customer = frappe.get_doc("Customer", customer.name)
			customer.shopify_customer_id = ""
			customer.sync_with_shopify = 0
			customer.flags.ignore_mandatory = True
			customer.save()
		else:
			raise
			
def update_address_details(customer, last_sync_datetime):
	customer_addresses = get_customer_addresses(customer, last_sync_datetime)
	for address in customer_addresses:
		if address.shopify_address_id:
			url = "/admin/customers/{0}/addresses/{1}.json".format(customer.shopify_customer_id,\
			address.shopify_address_id)
			
			address["id"] = address["shopify_address_id"]
			
			del address["shopify_address_id"]
			
			put_request(url, { "address": address})
			
		else:
			sync_customer_address(customer, address)
			
def get_customer_addresses(customer, last_sync_datetime=None):
	conditions = ["dl.parent = addr.name", "dl.link_doctype = 'Customer'",
		"dl.link_name = '{0}'".format(customer['name'])]
	
	if last_sync_datetime:
		last_sync_condition = "addr.modified >= '{0}'".format(last_sync_datetime)
		conditions.append(last_sync_condition)
	
	address_query = """select addr.name, addr.address_line1 as address1, addr.address_line2 as address2,
		addr.city as city, addr.state as province, addr.country as country, addr.pincode as zip,
		addr.shopify_address_id from tabAddress addr, `tabDynamic Link` dl
		where {0}""".format(' and '.join(conditions))
			
	return frappe.db.sql(address_query, as_dict=1)