# -*- coding: utf-8 -*-
# pylint: disable=C0326
from odoo.tests import tagged
from odoo import fields

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAccountReports(TestAccountReportsCommon):
    @classmethod
    def _reconcile_on(cls, lines, account):
        lines.filtered(lambda line: line.account_id == account and not line.reconciled).reconcile()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.liquidity_journal_1 = cls.company_data['default_journal_bank']
        cls.liquidity_account = cls.liquidity_journal_1.default_account_id
        cls.receivable_account_1 = cls.company_data['default_account_receivable']
        cls.revenue_account_1 = cls.company_data['default_account_revenue']

        # Invoice having two receivable lines on the same account.

        invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 345.0,     'credit': 0.0,      'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 805.0,     'credit': 0.0,      'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 1150.0,   'account_id': cls.revenue_account_1.id}),
            ],
        })
        invoice.action_post()

        # First payment (20% of the invoice).

        payment_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': cls.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 230.0,    'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 230.0,     'credit': 0.0,      'account_id': cls.liquidity_account.id}),
            ],
        })
        payment_1.action_post()

        cls._reconcile_on((invoice + payment_1).line_ids, cls.receivable_account_1)

        # Second payment (also 20% but will produce two partials, one on each receivable line).

        payment_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-03-01',
            'journal_id': cls.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 230.0,    'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 230.0,     'credit': 0.0,      'account_id': cls.liquidity_account.id}),
            ],
        })
        payment_2.action_post()

        cls._reconcile_on((invoice + payment_2).line_ids, cls.receivable_account_1)

    def test_general_ledger_cash_basis(self):
        # Check the cash basis option.
        self.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['report_cash_basis'] = True

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                            Debit       Credit      Balance
            [   0,                              4,          5,          6],
            [
                # Accounts.
                ('101404 Bank',                 460.0,      '',     460.0),
                ('121000 Account Receivable',   460.0,      460.0,    0.0),
                ('400000 Product Sales',        '',         460.0, -460.0),
                # Report Total.
                ('Total',                       920.0,      920.0,    0.0),
            ],
        )

        # Mark the '101200 Account Receivable' line to be unfolded.
        line_id = lines[2]['id'] # Index 2, because there is the total line for bank in position 1
        options['unfolded_lines'] = [line_id]
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Name                                    Date            Debit           Credit          Balance
            [   0,                                      1,                    4,             5,             6],
            [
                # Account.
                ('101404 Bank',                         '',              460.00,            '',        460.00),
                ('121000 Account Receivable',           '',              460.00,        460.00,          0.00),
                # Account Move Lines.from unfolded account
                ('MISC/2016/01/0001',                   '02/01/2016',     69.00,            '',         69.00),
                ('MISC/2016/01/0001',                   '02/01/2016',    161.00,            '',        230.00),
                ('BNK1/2016/00001',                     '02/01/2016',        '',        230.00,          0.00),
                ('MISC/2016/01/0001',                   '03/01/2016',     69.00,            '',         69.00),
                ('MISC/2016/01/0001',                   '03/01/2016',    161.00,            '',        230.00),
                ('BNK1/2016/00002',                     '03/01/2016',        '',        230.00,          0.00),
                # Account Total.
                ('Total 121000 Account Receivable',     '',              460.00,        460.00,          0.00),
                ('400000 Product Sales',                '',                  '',        460.00,       -460.00),
                # Report Total.
                ('Total',                               '',              920.00,        920.00,          0.00),
            ],
        )

    def test_balance_sheet_cash_basis(self):
        # Check the cash basis option.
        report = self.env.ref('account_reports.balance_sheet')
        options = self._generate_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['report_cash_basis'] = True

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      460.0),
                ('Current Assets',                              460.0),
                ('Bank and Cash Accounts',                      460.0),
                ('Receivables',                                 ''),
                ('Current Assets',                              ''),
                ('Prepayments',                                 ''),
                ('Total Current Assets',                        460.0),
                ('Plus Fixed Assets',                           ''),
                ('Plus Non-current Assets',                     ''),
                ('Total ASSETS',                                460.0),

                ('LIABILITIES',                                 ''),
                ('Current Liabilities',                         ''),
                ('Current Liabilities',                         ''),
                ('Payables',                                    ''),
                ('Total Current Liabilities',                   ''),
                ('Plus Non-current Liabilities',                ''),
                ('Total LIABILITIES',                           ''),

                ('EQUITY',                                      460.0),
                ('Unallocated Earnings',                        460.0),
                ('Current Year Unallocated Earnings',           460.0),
                ('Current Year Earnings',                       460.0),
                ('Current Year Allocated Earnings',             ''),
                ('Total Current Year Unallocated Earnings',     460.0),
                ('Previous Years Unallocated Earnings',         ''),
                ('Total Unallocated Earnings',                  460.0),
                ('Retained Earnings',                           ''),
                ('Total EQUITY',                                460.0),

                ('LIABILITIES + EQUITY',                        460.0),
            ],
        )

    def test_cash_basis_payment_in_the_past(self):
        self.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False

        payment_date = fields.Date.from_string('2010-01-01')
        invoice_date = fields.Date.from_string('2011-01-01')

        invoice = self.init_invoice('out_invoice', amounts=[100.0], partner=self.partner_a, invoice_date=invoice_date, post=True)
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'payment_date': payment_date,
        })._create_payments()

        # Check the impact in the reports: the invoice date should be the one the invoice appears at, since it greater than the payment's
        report = self.env.ref('account_reports.general_ledger_report')

        options = self._generate_options(report, payment_date, payment_date)
        options['cash_basis'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       4,              5,              6],
            [
                # Accounts.
                ('101402 Outstanding Receipts',        115,             '',            115),
                ('121000 Account Receivable',           '',            115,           -115),
                # Report Total.
                ('Total',                              115,            115,             0),
            ],
        )

        options = self._generate_options(report, invoice_date, invoice_date)
        options['cash_basis'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                                     Debit           Credit          Balance
            [   0,                                       4,              5,              6],
            [
                # Accounts.
                ('101402 Outstanding Receipts',        115,             '',            115),
                ('121000 Account Receivable',          115,            115,              0),
                ('251000 Tax Received',                 '',             15,            -15),
                ('400000 Product Sales',                '',            100,           -100),
                # Report Total.
                ('Total',                              230,            230,             0),
            ],
        )
