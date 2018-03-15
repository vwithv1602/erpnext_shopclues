// Copyright (c) 2018, vavcoders and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shopclues Settings', {
	refresh: function(frm) {
		if(!frm.doc.__islocal && frm.doc.enable_shopclues === 1){
            frm.add_custom_button(__('Sync Shopclues'), function() {
                frappe.call({
                    method:"erpnext_shopclues.api.sync_shopclues",
                })
            }).addClass("btn-primary");
        }
        frm.add_custom_button(__("Shopclues Log"), function(){
            frappe.set_route("List", "Shopclues Log");
        })
	}
});
