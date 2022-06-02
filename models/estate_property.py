from ast import Lambda
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class RecurringPlan(models.Model):
    _name = "estate.property"
    _inherit = [
        'mail.thread',
    ]
    _description = 'E-State Property'
    _order = 'id desc'
    _sql_constraints = [
        ('expected_price', 'CHECK(expected_price > 0)',
         'Expected price must be strictly positive'),
        ('selling_price', 'CHECK(selling_price > 0)',
         'Selling price must be positive'),
    ]

    name = fields.Char(
        required=True,
        string="Title",
        tracking=True
    )
    description = fields.Text(
        string='Description'
    )
    postcode = fields.Char(
        string='Postcode'
    )
    date_availability = fields.Date(
        copy=False,
        default=lambda self: fields.date.today()+timedelta(days=90),
        string="Available Form"
    )
    expected_price = fields.Float(
        required=True,
        string='Expected Price'
    )
    selling_price = fields.Float(
        readonly=True,
        copy=False,
        string='Selling Price'
    )
    bedrooms = fields.Integer(
        string='Bedrooms'
    )
    living_area = fields.Integer(
        string="Living Area(sqm)"
    )
    facades = fields.Integer(
        string='Facades'
    )
    garage = fields.Boolean(
        string='Garage'
    )
    garden = fields.Boolean(
        string='Garden'
    )
    garden_area = fields.Integer(
        string='Garden_area'
    )
    garden_orientation = fields.Selection(
        selection=[
            ('n', 'North'),
            ('s', 'South'),
            ('e', 'East'),
            ('w', 'West'),
        ]
    )

    last_seen = fields.Datetime(
        string="Last Seen",
        default=lambda self: fields.Datetime.now()
    )

    active = fields.Boolean(
        default=True
    )

    state = fields.Selection([
        ('new', 'New'),
        ('received', 'Received'),
        ('accepted', 'Accepted'),
        ('sold', 'Sold '),
        ('canceled', 'Canceled'),
    ],  required=True,
        copy=False,
        default='new',
        string='Status',
        tracking=True
    )

    partner_id = fields.Many2one(
        string='Buyer',
        comodel_name='res.partner',
        copy=False
    )

    user_id = fields.Many2one(
        string='Salesperson',
        comodel_name='res.users',
    )

    tax_ids = fields.Many2many(
        string='Tax Ids',
        comodel_name='account.tax',
    )

    offer_ids = fields.One2many(
        string='Offer',
        comodel_name='estate.property.offer',
        inverse_name='property_id',
    )

    total_area = fields.Integer(
        string='Total Area (sqm)',
        compute="_compute_total_area"
    )

    best_price = fields.Float(
        string="Best Offer",
        compute='_compute_best_price',
    )

    type_id = fields.Many2one(
        string='Type',
        comodel_name='estate.property.type',
    )

    tag_ids = fields.One2many(
        string='Tag',
        comodel_name='estate.property.tag',
        inverse_name='property_id',
    )

    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.user.company_id,
    )

    @api.onchange('garden')
    def onchange_garden(self):
        for record in self:
            if record.garden:
                record.garden_orientation = 'n'
                record.garden_area = 10

    @api.depends('offer_ids.price', 'offer_ids')
    def _compute_best_price(self):
        for record in self:
            record.best_price = max(record.offer_ids.mapped('price')+[0])

    @api.depends('garden_area', 'living_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = (record.garden_area or 0) + \
                (record.living_area or 0)

    @api.constrains("selling_price", "expected_price", )
    def _check_expected_price(self):
        for s in self:
            if s.selling_price < s.expected_price * 0.9 and s.offer_ids.filtered(lambda o: o.status == 'accepted'):
                raise ValidationError(
                    _('The selling price cannot be lower than 90' '%' ' of the expected price.'))

    @api.ondelete(at_uninstall=False)
    def _delete(self):
        for record in self:
            if record.state not in ["new", "canceled"]:
                raise UserError('you can only delete new or canceled ')

    def action_cancel(self):
        for record in self:
            if record.state == 'sold':
                raise UserError('A sold property cannot be canceled.')
            record.state = 'canceled'

    def action_sold(self):
        for record in self:
            if record.state == 'canceled':
                raise UserError('A canceled property cannot be set as sold.')
            record.state = 'sold'

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'received':
            return self.env.ref('estate.mt_state_change')
        return super(RecurringPlan, self)._track_subtype(init_values)

class PropertyType(models.Model):
    _name = "estate.property.type"
    _description = 'E-State Property Type'
    _order = 'name'
    _sql_constraints = [
        ('type_name', 'unique(name)', 'Name must be unique!'),
    ]
    name = fields.Char(
        required=True,
        string='Name'
    )

    property_ids = fields.One2many(
        string='Property',
        comodel_name='estate.property',
        inverse_name='type_id',
    )
    sequence = fields.Integer(
        string='Sequence'
    )

    offer_ids = fields.One2many(
        string='Offer',
        comodel_name='estate.property.offer',
        inverse_name='property_type_id',
    )

    offer_count = fields.Integer(
        string='Offer Count',
        compute='_compute_offers'
    )

    @api.depends('offer_ids')
    def _compute_offers(self):
        for record in self:
            record.offer_count = len(record.offer_ids)


class PropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = 'E-State Property Tag'
    _order = 'name'
    _sql_constraints = [
        ('tag_name', 'unique(name)', 'Name must be unique!'),
    ]
    name = fields.Char(
        required=True,
        string='Name'
    )
    color = fields.Integer(
        string='Color'
    )

    property_id = fields.Many2one(
        string='Property',
        comodel_name='estate.property',
    )


class PropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = 'E-State Property Offer'
    _order = 'price desc'
    _sql_constraints = [
        ('price', 'CHECK(price > 0)', 'Price must be positive'),
    ]

    price = fields.Float(
        string='Price',
    )
    status = fields.Selection([
        ('accepted', 'Accepted'),
        ('refused', 'Refused'),
    ],  copy=False,
        string='Status'
    )

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        required=True,
    )

    property_id = fields.Many2one(
        string='Property',
        comodel_name='estate.property',
    )

    validity = fields.Integer(
        default=7,
        string='Validity',
    )
    date_deadline = fields.Date(
        string='Date Deadline',
        compute='_compute_date_deadline')

    property_type_id = fields.Many2one(
        related='property_id.type_id',
        store=True,
    )

    @api.depends('validity', )
    def _compute_date_deadline(self):
        for record in self:
            record.date_deadline = (
                record.create_date or fields.Datetime.now()) + timedelta(days=record.validity)

    @api.constrains("property_id", "price")
    def _check_state(self):
        for record in self:
            if record.property_id.best_price != 0:
                if record.price < record.property_id.best_price:
                    raise ValidationError(
                        _("your price is lower than an existing offer price "))
                else:
                    record.property_id.state = "received"

    def action_accept(self):
        for record in self:
            if record.property_id.offer_ids.filtered(lambda o: o.status == 'accepted'):
                raise UserError('There\'s already offer accepted')
            else:
                record.status = 'accepted'
                record.property_id.selling_price = record.price
                record.property_id.partner_id = record.partner_id
                record.property_id.offer_ids.filtered(
                    lambda o: o.id != record.id).status = 'refused'

    def action_refuse(self):
        for record in self:
            record.status = 'refused'


class ResUsers(models.Model):
    _inherit = 'res.users'

    property_ids = fields.One2many(
        string='Property Ids',
        comodel_name='estate.property',
        inverse_name='user_id',
        domain=[('state', 'in', ['new', 'received'])]
    )
    