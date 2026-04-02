from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase

from common.tests.helpers import create_bidder, create_document, create_process
from documents.models import DocumentVersion
from finance.models import FinancialAssessment, FinancialInputVersion


class FinancialConstraintTests(TransactionTestCase):
    def test_only_one_draft_input_per_bidder(self):
        process = create_process()
        bidder = create_bidder(process=process)
        FinancialInputVersion.objects.create(
            process=process,
            bidder=bidder,
            source_label="Area financiera",
            source_date="2026-03-21",
            assets_value="100",
            liabilities_value="10",
            operating_income_value="50",
            status="draft",
        )

        with self.assertRaises(IntegrityError):
            FinancialInputVersion.objects.create(
                process=process,
                bidder=bidder,
                source_label="Area financiera 2",
                source_date="2026-03-22",
                assets_value="120",
                liabilities_value="20",
                operating_income_value="60",
                status="draft",
            )

    def test_only_one_assessment_used_in_consolidation_per_bidder(self):
        process = create_process()
        bidder = create_bidder(process=process)
        input_1 = FinancialInputVersion.objects.create(
            process=process,
            bidder=bidder,
            source_label="Area financiera",
            source_date="2026-03-21",
            assets_value="100",
            liabilities_value="10",
            operating_income_value="50",
            status="submitted",
        )
        input_2 = FinancialInputVersion.objects.create(
            process=process,
            bidder=bidder,
            source_label="Area financiera 2",
            source_date="2026-03-22",
            assets_value="120",
            liabilities_value="20",
            operating_income_value="60",
            status="submitted",
            version_no=2,
        )
        FinancialAssessment.objects.create(
            process=process,
            bidder=bidder,
            financial_input_version=input_1,
            result_code="meets",
            status="confirmed",
            used_in_consolidation=True,
        )

        with self.assertRaises(IntegrityError):
            FinancialAssessment.objects.create(
                process=process,
                bidder=bidder,
                financial_input_version=input_2,
                result_code="meets",
                status="confirmed",
                used_in_consolidation=True,
                version_no=2,
            )


class FinancialCleanTests(TestCase):
    def test_financial_assessment_requires_same_process_and_bidder_as_input(self):
        process_1 = create_process(code="PROC-1")
        process_2 = create_process(code="PROC-2", name="Proceso 2")
        bidder_1 = create_bidder(process=process_1, identification_number="900000001")
        bidder_2 = create_bidder(process=process_2, identification_number="900000002", name="Proponente 2")
        input_version = FinancialInputVersion.objects.create(
            process=process_1,
            bidder=bidder_1,
            source_label="Area financiera",
            source_date="2026-03-21",
            assets_value="100",
            liabilities_value="10",
            operating_income_value="50",
            status="submitted",
        )

        assessment = FinancialAssessment(
            process=process_2,
            bidder=bidder_2,
            financial_input_version=input_version,
            result_code="meets",
            status="confirmed",
        )

        with self.assertRaises(ValidationError):
            assessment.full_clean()
