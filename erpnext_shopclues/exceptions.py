from __future__ import unicode_literals
import frappe

class ShopcluesError(frappe.ValidationError): pass
class ShopcluesSetupError(frappe.ValidationError): pass