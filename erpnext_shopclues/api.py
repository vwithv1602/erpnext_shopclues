from __future__ import unicode_literals
import frappe
from frappe import _
from .sync_orders import sync_orders
from .utils import disable_shopclues_sync_on_exception, make_shopclues_log
from frappe.utils.background_jobs import enqueue
from datetime import datetime,timedelta
from .vlog import vwrite

@frappe.whitelist()
def sync_shopclues():
    enqueue("erpnext_shopclues.api.sync_shopclues_resources", queue='long')
    frappe.msgprint(_("Queued for syncing. It may take a few minutes to an hour if this is your first sync."))

@frappe.whitelist()
def sync_shopclues_resources():
    "Enqueue longjob for syncing shopify"
    shopclues_settings = frappe.get_doc("Shopclues Settings")
    make_shopclues_log(title="Shopclues Sync Job Queued", status="Queued", method=frappe.local.form_dict.cmd,
                     message="Shopclues Sync Job Queued")
    if(shopclues_settings.enable_shopclues):
        try:
            now_time = frappe.utils.now()
            validate_shopclues_settings(shopclues_settings)
            frappe.local.form_dict.count_dict = {}
            # sync_products(shopclues_settings.price_list, shopclues_settings.warehouse)
            sync_orders()
            frappe.db.set_value("Shopclues Settings", None, "last_sync_datetime", now_time)

            make_shopclues_log(title="Sync Completed", status="Success", method=frappe.local.form_dict.cmd,
                             message="Shopify sync successfully completed")
        except Exception, e:
            if e.args[0] and hasattr(e.args[0], "startswith") and e.args[0].startswith("402"):
                make_shopclues_log(title="Shopclues has suspended your account", status="Error",
                                 method="sync_shopclues_resources", message=_("""Shopclues has suspended your account till
            		you complete the payment. We have disabled ERPNext Shopclues Sync. Please enable it once
            		your complete the payment at Shopclues."""), exception=True)

                disable_shopclues_sync_on_exception()

            else:
                make_shopclues_log(title="sync has terminated", status="Error", method="sync_shopclues_resources",
                                 message=frappe.get_traceback(), exception=True)
    elif frappe.local.form_dict.cmd == "erpnext_shopclues.api.sync_shopclues":
        make_shopclues_log(
            title="Shopclues connector is disabled",
            status="Error",
            method="sync_shopclues_resources",
            message=_(
                """Shopclues connector is not enabled. Click on 'Connect to Shopclues' to connect ERPNext and your Shopclues store."""),
            exception=True)

def validate_shopclues_settings(shopclues_settings):
	"""
		This will validate mandatory fields and access token or app credentials
		by calling validate() of shopclues settings.
	"""
	try:
		shopclues_settings.save()
	except Exception, e:
		disable_shopclues_sync_on_exception()
