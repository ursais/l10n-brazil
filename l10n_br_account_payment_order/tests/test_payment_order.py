# @ 2018 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.exceptions import ValidationError
from odoo.tests import SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentOrder(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice_cheque = cls.env.ref(
            "l10n_br_account_payment_order.demo_invoice_payment_order_cheque"
        )

    def test_payment_mode_without_payment_order(self):
        """ Test Invoice when Payment Mode not generate Payment Order. """
        self.invoice_cheque._onchange_payment_mode_id()
        # I validate invoice by creating on
        self.invoice_cheque.action_invoice_open()
        # I check that the invoice state is "Open"
        self.assertEqual(self.invoice_cheque.state, "open")
        payment_order = self.env["account.payment.order"].search(
            [("payment_mode_id", "=", self.invoice_cheque.payment_mode_id.id)]
        )
        self.assertEqual(len(payment_order), 0)

    def test_bra_number_constrains(self):
        """ Test bra_number constrains. """
        self.banco_bradesco = self.env["res.bank"].search([("code_bc", "=", "033")])
        with self.assertRaises(ValidationError):
            self.env["res.partner.bank"].create(
                dict(
                    bank_id=self.banco_bradesco.id,
                    partner_id=self.ref("l10n_br_base.res_partner_akretion"),
                    bra_number="12345",
                )
            )
