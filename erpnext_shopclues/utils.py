from __future__ import unicode_literals
import frappe
import json

# from .shopclues_requests import get_request
from vlog import vwrite
from bs4 import BeautifulSoup
import types

def disable_shopclues_sync_for_item(item, rollback=False):
    """Disable Item if not exist on shopclues"""
    if rollback:
        frappe.db.rollback()

    item.sync_with_shopclues = 0
    item.sync_qty_with_shopclues = 0
    item.save(ignore_permissions=True)
    frappe.db.commit()

def disable_shopclues_sync_on_exception():
	frappe.db.rollback()
	frappe.db.set_value("Shopclues Settings", None, "enable_shopclues", 0)
	frappe.db.commit()


def make_shopclues_log(title="Sync Log", status="Queued", method="sync_shopclues", message=None, exception=False,
                     name=None, request_data={}):
    make_log_flag = True
    # log_message = message if message else frappe.get_traceback()
    # log_query = """select name from `tabShopclues Log` where title = '%s' and message='%s' and method='%s' and status='%s' and request_data='%s'""" %(title[0:140],log_message,method,status,json.dumps(request_data))
    log_query = """select name from `tabShopclues Log` where title = '%s' and method='%s' and request_data='%s'""" % (
    title[0:140].replace("'","''"), method, json.dumps(request_data))
    if status!="Queued" and title!="Sync Completed":
        if len(frappe.db.sql(log_query, as_dict=1)) > 0:
            make_log_flag = False
    if make_log_flag:
        if not name:
            name = frappe.db.get_value("Shopclues Log", {"status": "Queued"})

            if name:
                """ if name not provided by log calling method then fetch existing queued state log"""
                log = frappe.get_doc("Shopclues Log", name)

            else:
                """ if queued job is not found create a new one."""
                log = frappe.get_doc({"doctype": "Shopclues Log"}).insert(ignore_permissions=True)

            if exception:
                frappe.db.rollback()
                log = frappe.get_doc({"doctype": "Shopclues Log"}).insert(ignore_permissions=True)

            log.message = message if message else frappe.get_traceback()
            log.title = title[0:140]
            log.method = method
            log.status = status
            log.request_data = json.dumps(request_data)

            log.save(ignore_permissions=True)
            frappe.db.commit()