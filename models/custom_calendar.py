from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class CustomCalendarReport(models.Model):
    _name = 'custom.calendar.report'
    _description = 'Custom Calendar Report'
    _rec_name = 'product_id'

    date = fields.Date(string='Date', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    sale_order_quantity = fields.Float(string='Sale Order Quantity', compute='_compute_sale_order_quantity', store=True)
    purchase_order_quantity = fields.Float(string='Purchase Order Quantity', compute='_compute_purchase_order_quantity', store=True)
    stock_on_hand = fields.Float(string='Stock on Hand', compute='_compute_stock_on_hand', store=True)
    being_manufactured = fields.Float(string='Being Manufactured', compute='_compute_being_manufactured', store=True)
    reserved_quantity = fields.Float(string='Reserved Quantity', compute='_compute_reserved_quantity', store=True)
    bom_quantity = fields.Float(string='BoM Quantity', compute='_compute_bom_quantity', store=True)
    forecast_quantity = fields.Float(string='Forecast Quantity', compute='_compute_forecast_quantity', store=True)
    today_current_stock = fields.Float(string='Current Stock\'s Left', compute='_compute_today_current_stock', store=True)    
    sale_order_refs = fields.Many2many('sale.order', string='Sale Orders', compute='_compute_sale_order_quantity', store=True)
    purchase_order_refs = fields.Many2many('purchase.order', string='Purchase Orders', compute='_compute_purchase_order_quantity', store=True)
    manufacturing_order_refs = fields.Many2many('mrp.production', string='Manufacturing Orders', compute='_compute_being_manufactured', store=True)
    bom_refs = fields.Many2many('mrp.bom', string='BoMs', compute='_compute_bom_quantity', store=True)
    used_in_refs = fields.Many2many('product.product', string='Used In Products', compute='_compute_used_in_refs', store=True)

    @api.depends('product_id', 'date')
    def _compute_sale_order_quantity(self):
        for record in self:
            start_of_day = datetime.combine(record.date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)

            _logger.info('Computing sale_order_quantity for product_id: %s on date: %s', record.product_id.id, record.date)

            pickings = self.env['stock.picking'].search([
                ('move_lines.product_id', '=', record.product_id.id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('scheduled_date', '>=', start_of_day),
                ('scheduled_date', '<', end_of_day),
                ('state', '!=', 'cancel')
            ])

            _logger.info('Found %d pickings for sale orders', len(pickings))
            
            sale_order_lines = pickings.mapped('move_lines.sale_line_id')
            record.sale_order_quantity = sum(line.product_uom_qty for line in sale_order_lines) or 0.0
            record.sale_order_refs = [(6, 0, sale_order_lines.mapped('order_id').ids)]

            _logger.info('Computed sale_order_quantity: %s', record.sale_order_quantity)
            _logger.info('Sale order references: %s', record.sale_order_refs)

    @api.depends('product_id', 'date')
    def _compute_purchase_order_quantity(self):
        for record in self:
            start_of_day = datetime.combine(record.date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)

            _logger.info('Computing purchase_order_quantity for product_id: %s on date: %s', record.product_id.id, record.date)

            pickings = self.env['stock.picking'].search([
                ('move_lines.product_id', '=', record.product_id.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('scheduled_date', '>=', start_of_day),
                ('scheduled_date', '<', end_of_day),
                ('state', '!=', 'cancel')
            ])

            _logger.info('Found %d pickings for purchase orders', len(pickings))
            
            purchase_order_lines = pickings.mapped('move_lines.purchase_line_id')
            record.purchase_order_quantity = sum(line.product_qty for line in purchase_order_lines) or 0.0
            record.purchase_order_refs = [(6, 0, purchase_order_lines.mapped('order_id').ids)]

            _logger.info('Computed purchase_order_quantity: %s', record.purchase_order_quantity)
            _logger.info('Purchase order references: %s', record.purchase_order_refs)
            
    @api.depends('product_id', 'date')
    def _compute_stock_on_hand(self):
        for record in self:
            product = record.product_id
            record.stock_on_hand = product.qty_available or 0.0
            _logger.info('Computed stock_on_hand: %s for product_id: %s on date: %s', record.stock_on_hand, record.product_id.id, record.date)


    @api.depends('product_id', 'date')
    def _compute_being_manufactured(self):
        for record in self:
            start_of_day = datetime.combine(record.date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)

            _logger.info('Computing being_manufactured for product_id: %s on date: %s', record.product_id.id, record.date)

            productions = self.env['mrp.production'].search([
                ('product_id', '=', record.product_id.id),
                ('date_planned_start', '>=', start_of_day),
                ('date_planned_start', '<', end_of_day)
            ])

            _logger.info('Found %d manufacturing orders', len(productions))

            # New logic: Sum of product_qty for the manufacturing orders
            record.being_manufactured = sum(production.product_qty for production in productions) or 0.0
            record.manufacturing_order_refs = [(6, 0, productions.ids)]

            _logger.info('Computed being_manufactured: %s', record.being_manufactured)

    @api.depends('product_id', 'date')
    def _compute_reserved_quantity(self):
        for record in self:
            start_of_day = datetime.combine(record.date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)

            _logger.info('Computing reserved quantity for product_id: %s on date: %s', record.product_id.id, record.date)

            # Find relevant stock moves for calculating reserved quantity
            reserved_moves = self.env['stock.move'].search([
                ('product_id', '=', record.product_id.id),
                ('state', '=', 'assigned'),  # Modify state to 'assigned' for reserved quantities
                ('date_deadline', '>=', start_of_day),
                ('date_deadline', '<', end_of_day),
            ])

            _logger.info('Found %d stock moves for reserved quantity', len(reserved_moves))

            # Calculate and store the reserved quantity
            record.reserved_quantity = sum(move.product_uom_qty for move in reserved_moves) or 0.0

            _logger.info('Computed reserved quantity: %s', record.reserved_quantity)

    
    @api.depends('product_id')
    def _compute_bom_quantity(self):
        for record in self:
            _logger.info('Computing bom_quantity for product_id: %s', record.product_id.id)

            boms = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', record.product_id.product_tmpl_id.id)
            ])

            bom_quantity = sum(bom.product_qty for bom in boms) or 0.0
            record.bom_quantity = bom_quantity
            record.bom_refs = [(6, 0, boms.ids)]

            _logger.info('Computed bom_quantity: %s', record.bom_quantity)
            _logger.info('BoM references: %s', record.bom_refs)

    @api.depends('product_id')
    def _compute_used_in_refs(self):
        for record in self:
            _logger.info('Computing used_in_refs for product_id: %s', record.product_id.id)

            used_in = self.env['mrp.bom.line'].search([
                ('product_id', '=', record.product_id.id)
            ]).mapped('bom_id.product_tmpl_id.product_variant_id')

            record.used_in_refs = [(6, 0, used_in.ids)]

            _logger.info('Used In references: %s', record.used_in_refs)

    @api.depends('product_id', 'date')
    def _compute_forecast_quantity(self):
        for record in self:
            if not record.product_id or not record.date:
                record.forecast_quantity = 0.0
                _logger.info("Computed forecast_quantity: 0.0 for product_id: %s on date: %s (product_id or date missing)", record.product_id.id, record.date)
                continue

            # Forecast based on virtual available
            record.forecast_quantity = record.product_id.virtual_available or 0.0

            _logger.info("Computed forecast_quantity: %s for product_id: %s on date: %s", record.forecast_quantity, record.product_id.id, record.date)
    
    @api.depends('date', 'stock_on_hand', 'purchase_order_quantity', 'sale_order_quantity', 'being_manufactured')
    def _compute_today_current_stock(self):
        for record in self:
            stock_on_hand = record.stock_on_hand
            purchase = record.purchase_order_quantity
            sale = record.sale_order_quantity
            being_manufactured = record.being_manufactured

            # Compute today's current stock
            record.today_current_stock = stock_on_hand + purchase - sale + being_manufactured

            _logger.info('Computed today_current_stock: %s for product_id: %s on date: %s', record.today_current_stock, record.product_id.id, record.date)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create(self, vals):
        # Create the StockPicking record first
        record = super(StockPicking, self).create(vals)
        _logger.info('Stock Picking created with ID: %s and values: %s', record.id, vals)
        
        # Immediately update the custom calendar report using the scheduled date
        if record.scheduled_date:
            _logger.info('Scheduled date set for Stock Picking ID: %s on creation: %s', record.id, record.scheduled_date)
            record._update_custom_calendar_report()  # Trigger report update on creation
        
        return record

    def write(self, vals):
        old_dates = {record.id: record.scheduled_date.date() if record.scheduled_date else False for record in self}
        res = super(StockPicking, self).write(vals)
        _logger.info('Stock Picking with ID: %s updated with values: %s', self.id, vals)
        
        if 'scheduled_date' in vals:
            for record in self:
                old_date = old_dates.get(record.id)
                new_date = record.scheduled_date.date() if record.scheduled_date else False
                
                # Log when a scheduled date is added
                if not old_date and new_date:
                    _logger.info('Scheduled date added for Picking ID: %s: %s', record.id, new_date)
                
                # Log if the scheduled date has changed
                elif old_date and old_date != new_date:
                    _logger.info('Scheduled date changed for Picking ID: %s from %s to %s', record.id, old_date, new_date)
                    record._remove_old_custom_calendar_report(old_date)
        
        # Always update the custom calendar report after write
        self._update_custom_calendar_report()
        return res

    def unlink(self):
        for record in self:
            _logger.info('Stock Picking with ID: %s being unlinked.', record.id)
            record._update_custom_calendar_report(remove=True)
        result = super(StockPicking, self).unlink()
        _logger.info('Stock Pickings unlinked.')
        return result

    def action_confirm(self):
        """Confirm the stock picking, update stock quantities, and handle custom calendar reports."""
        res = super(StockPicking, self).action_confirm()

        for picking in self:
            _logger.info('Confirming Stock Picking(s): %s', picking.name)

            # Update stock quantities for each move line
            for move in picking.move_lines:
                product = move.product_id
                if picking.picking_type_id.code == 'incoming':
                    # For incoming pickings (e.g., receipt), increase stock
                    product.with_company(picking.company_id).qty_available += move.product_qty
                    _logger.info('Received product: %s, quantity received: %s, new quantity: %s', product.name, move.product_qty, product.qty_available)
                elif picking.picking_type_id.code == 'outgoing':
                    # For outgoing pickings (e.g., delivery), decrease stock
                    product.with_company(picking.company_id).qty_available -= move.product_qty
                    _logger.info('Shipped product: %s, quantity shipped: %s, new quantity: %s', product.name, move.product_qty, product.qty_available)

            # Update custom calendar report
            picking._update_custom_calendar_report()

        return res
    
    def _update_custom_calendar_report(self, remove=False):
        for picking in self:
            for move in picking.move_lines:
                product_id = move.product_id.id
                
                # Ensure the scheduled date is set, default to today if missing
                scheduled_date = picking.scheduled_date.date() if picking.scheduled_date else False
                if not scheduled_date:
                    scheduled_date = fields.Date.today()
                    _logger.info('Scheduled date was missing, defaulting to today: %s', scheduled_date)

                if scheduled_date:
                    if remove:
                        old_reports = self.env['custom.calendar.report'].search([
                            ('product_id', '=', product_id),
                            ('date', '=', scheduled_date)
                        ])
                        for report in old_reports:
                            _logger.info('Removing quantities for report ID %s on date %s for product %s', report.id, scheduled_date, product_id)

                            # Update quantities
                            report.sale_order_quantity -= move.sale_line_id.product_uom_qty if move.sale_line_id else 0.0
                            report.purchase_order_quantity -= move.purchase_line_id.product_qty if move.purchase_line_id else 0.0

                            # Update references
                            if move.sale_line_id:
                                report.sale_order_refs = [(3, move.sale_line_id.order_id.id)]
                            if move.purchase_line_id:
                                report.purchase_order_refs = [(3, move.purchase_line_id.order_id.id)]

                            # Unlink the report if all quantities are zero
                            if not any([
                                report.sale_order_quantity,
                                report.purchase_order_quantity
                            ]):
                                _logger.info('Unlinking report ID %s as all quantities are zero', report.id)
                                report.unlink()
                            else:
                                _logger.info('Updated report ID %s with remaining quantities', report.id)
                    else:
                        report = self.env['custom.calendar.report'].search([
                            ('product_id', '=', product_id),
                            ('date', '=', scheduled_date)
                        ], limit=1)
                        
                        if not report:
                            # Create a new report entry if it doesn't exist
                            report = self.env['custom.calendar.report'].create({
                                'product_id': product_id,
                                'date': scheduled_date,
                                'sale_order_quantity': move.sale_line_id.product_uom_qty if move.sale_line_id else 0.0,
                                'purchase_order_quantity': move.purchase_line_id.product_qty if move.purchase_line_id else 0.0,
                                'sale_order_refs': [(4, move.sale_line_id.order_id.id)] if move.sale_line_id else [],
                                'purchase_order_refs': [(4, move.purchase_line_id.order_id.id)] if move.purchase_line_id else [],
                            })
                            _logger.info('Created new report ID %s for product %s on date %s', report.id, product_id, scheduled_date)
                        else:
                            _logger.info('Updating existing report ID %s for product %s on date %s', report.id, product_id, scheduled_date)
                            
                            # Update quantities in the existing report
                            report.sale_order_quantity += move.sale_line_id.product_uom_qty if move.sale_line_id else 0.0
                            report.purchase_order_quantity += move.purchase_line_id.product_qty if move.purchase_line_id else 0.0

                            # Add references to the report
                            if move.sale_line_id:
                                report.sale_order_refs = [(4, move.sale_line_id.order_id.id)]
                            if move.purchase_line_id:
                                report.purchase_order_refs = [(4, move.purchase_line_id.order_id.id)]

    def _remove_old_custom_calendar_report(self, old_date):
        for picking in self:
            for move in picking.move_lines:
                product_id = move.product_id.id
                if old_date:
                    old_reports = self.env['custom.calendar.report'].search([
                        ('product_id', '=', product_id),
                        ('date', '=', old_date)
                    ])
                    for report in old_reports:
                        _logger.info('Processing old report ID %s for product %s on date %s', report.id, product_id, old_date)
                        report.sale_order_quantity -= move.sale_line_id.product_uom_qty if move.sale_line_id else 0.0
                        report.purchase_order_quantity -= move.purchase_line_id.product_qty if move.purchase_line_id else 0.0

                        if move.sale_line_id:
                            report.sale_order_refs = [(3, move.sale_line_id.order_id.id)]
                        if move.purchase_line_id:
                            report.purchase_order_refs = [(3, move.purchase_line_id.order_id.id)]

                        if not any([
                            report.sale_order_quantity,
                            report.purchase_order_quantity
                        ]):
                            _logger.info('Unlinking report ID %s for product %s on old date %s as quantities are zero', report.id, product_id, old_date)
                            report.unlink()
                        else:
                            _logger.info('Updated old report ID %s with remaining quantities', report.id)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def create(self, vals):
        """Create a new manufacturing order and update the custom calendar report."""
        record = super(MrpProduction, self).create(vals)
        _logger.info('Manufacturing Order created with ID: %s and values: %s', record.id, vals)
        # Update custom calendar report
        record._update_custom_calendar_report()
        return record

    def write(self, vals):
        """Update an existing manufacturing order and handle changes to the planned start date."""
        # Capture old dates before update
        old_dates = {record.id: record.date_planned_start.date() if record.date_planned_start else False for record in self}
        res = super(MrpProduction, self).write(vals)
        _logger.info('Manufacturing Order with ID: %s updated with values: %s', self.id, vals)

        # Process date changes
        if 'date_planned_start' in vals:
            for record in self:
                old_date = old_dates.get(record.id)
                new_date = record.date_planned_start.date() if record.date_planned_start else False
                if old_date and old_date != new_date:
                    _logger.info('Planned start date changed for Manufacturing Order ID: %s from %s to %s', record.id, old_date, new_date)
                    record._remove_old_custom_calendar_report(old_date)
                    record._update_custom_calendar_report()  # Update with new date
        return res

    def unlink(self):
        """Unlink (delete) manufacturing orders and update the custom calendar report."""
        for record in self:
            _logger.info('Manufacturing Order with ID: %s being unlinked.', record.id)
            record._update_custom_calendar_report(remove=True)
        result = super(MrpProduction, self).unlink()
        _logger.info('Manufacturing Orders unlinked.')
        return result

    def action_confirm(self):
        """Confirm the manufacturing order, update stock quantities, and handle custom calendar reports."""
        # Call the original action_confirm method
        res = super(MrpProduction, self).action_confirm()

        for production in self:
            _logger.info('Confirming Manufacturing Order(s): %s', production.name)

            # Update raw materials
            for move in production.move_raw_ids:
                product = move.product_id
                product.with_company(production.company_id).qty_available -= move.product_uom_qty
                _logger.info('Consumed raw material: %s, quantity consumed: %s, new quantity: %s', product.name, move.product_uom_qty, product.qty_available)

            # Update finished products
            for move in production.move_finished_ids:
                product = move.product_id
                product.with_company(production.company_id).qty_available += move.product_uom_qty
                _logger.info('Produced finished product: %s, quantity produced: %s, new quantity: %s', product.name, move.product_uom_qty, product.qty_available)

            # Update custom calendar report
            production._update_custom_calendar_report()

        return res

    
    def _update_custom_calendar_report(self, remove=False):
        """Update or remove entries in the custom calendar report based on the manufacturing order."""
        for production in self:
            product_id = production.product_id.id
            planned_start_date = production.date_planned_start.date() if production.date_planned_start else False
            if planned_start_date:
                if remove:
                    # Remove or update existing report entries
                    old_reports = self.env['custom.calendar.report'].search([
                        ('product_id', '=', product_id),
                        ('date', '=', planned_start_date)
                    ])
                    for report in old_reports:
                        _logger.info('Removing quantities from report ID %s for product %s on date %s', report.id, product_id, planned_start_date)
                        report.being_manufactured -= production.product_qty
                        if not report.being_manufactured:
                            report.manufacturing_order_refs = [(3, production.id)]  # Remove reference
                        if not any([
                            report.sale_order_quantity,
                            report.purchase_order_quantity,
                            report.being_manufactured
                        ]):
                            _logger.info('Unlinking report ID %s as all quantities are zero', report.id)
                            report.unlink()  # Delete the report if no relevant data
                        else:
                            _logger.info('Updated report ID %s with remaining quantities', report.id)
                else:
                    # Create or update report entry
                    report = self.env['custom.calendar.report'].search([
                        ('product_id', '=', product_id),
                        ('date', '=', planned_start_date)
                    ], limit=1)
                    if not report:
                        # Create new report
                        report = self.env['custom.calendar.report'].create({
                            'product_id': product_id,
                            'date': planned_start_date,
                            'being_manufactured': production.product_qty,
                            'manufacturing_order_refs': [(4, production.id)]  # Add reference
                        })
                        _logger.info('Created new report ID %s for product %s on date %s', report.id, product_id, planned_start_date)
                    else:
                        # Update existing report
                        _logger.info('Updating existing report ID %s for product %s on date %s', report.id, product_id, planned_start_date)
                        report.being_manufactured += production.product_qty
                        if production.id not in report.manufacturing_order_refs.ids:
                            report.manufacturing_order_refs = [(4, production.id)]  # Add reference

                    # Remove reference and quantity from the old report (if date changed)
                    old_report = self.env['custom.calendar.report'].search([
                        ('product_id', '=', product_id),
                        ('date', '=', production.date_planned_start.date() if production.date_planned_start else False)  # Use original planned_start_date
                    ], limit=1)
                    if old_report and old_report.id != report.id:  # Avoid removing from the current report
                        _logger.info('Updating old report ID %s for product %s on old date %s', old_report.id, product_id, production.date_planned_start.date())
                        old_report.being_manufactured -= production.product_qty
                        old_report.manufacturing_order_refs = [(3, production.id)]
                        if not any([
                            old_report.sale_order_quantity,
                            old_report.purchase_order_quantity,
                            old_report.being_manufactured
                        ]):
                            _logger.info('Unlinking old report ID %s as all quantities are zero', old_report.id)
                            old_report.unlink()  # Delete the report if no relevant data
                        else:
                            _logger.info('Updated old report ID %s with remaining quantities', old_report.id)

    def _remove_old_custom_calendar_report(self, old_date):
        """Remove or update custom calendar report entries associated with the old date."""
        for production in self:
            product_id = production.product_id.id
            if old_date:
                old_reports = self.env['custom.calendar.report'].search([
                    ('product_id', '=', product_id),
                    ('date', '=', old_date)
                ])
                for report in old_reports:
                    _logger.info('Processing old report ID %s for product %s on date %s', report.id, product_id, old_date)
                    report.being_manufactured -= production.product_qty
                    if not report.being_manufactured:
                        report.manufacturing_order_refs = [(3, production.id)]  # Remove reference
                    if not any([
                        report.sale_order_quantity,
                        report.purchase_order_quantity,
                        report.being_manufactured
                    ]):
                        _logger.info('Unlinking old report ID %s as all quantities are zero', report.id)
                        report.unlink()  # Delete the report if no relevant data



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        # Call the original confirmation method
        res = super(PurchaseOrder, self).button_confirm()

        for order in self:
            _logger.info('Confirming Purchase Order(s): %s', order.mapped('name'))
            for picking in order.picking_ids:
                # Update stock on hand for each picking in the purchase order
                for move_line in picking.move_lines:
                    product = move_line.product_id
                    product.with_company(order.company_id).qty_available += move_line.product_qty
                    _logger.info('Updated stock on hand for product: %s, new quantity: %s', product.name, product.qty_available)
                
                # Trigger the update of the custom calendar report
                picking._update_custom_calendar_report()

        return res



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        _logger.info('Confirming Sale Order(s): %s', self.mapped('name'))
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            for line in order.order_line:
                product = line.product_id
                product.with_company(order.company_id).qty_available -= line.product_uom_qty
                _logger.info('Updated stock on hand for product: %s, new quantity: %s', product.name, product.qty_available)
        return res
