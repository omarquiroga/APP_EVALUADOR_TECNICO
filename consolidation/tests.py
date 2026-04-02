from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase

from bidders.models import Bidder
from common.tests.helpers import create_bidder, create_process
from consolidation.models import BidderConsolidatedResult, ConsolidatedMatrixSnapshot
from normative.models import DocumentTypeFamily, DocumentTypeVersion, NormativeSnapshot, NormativeSource


class ConsolidatedMatrixSnapshotConstraintTests(TransactionTestCase):
    def test_only_one_current_snapshot_per_process(self):
        process = create_process()
        source = NormativeSource.objects.create(code="CCE-CONS", name="Colombia Compra")
        family = DocumentTypeFamily.objects.create(source=source, code="DT-CONS", name="Doc tipo consolidacion")
        version = DocumentTypeVersion.objects.create(family=family, version_label="v1")
        normative_snapshot = NormativeSnapshot.objects.create(
            process=process,
            document_type_version=version,
            snapshot_label="norma",
            payload={},
            checksum="norma-1",
            is_current=True,
        )
        ConsolidatedMatrixSnapshot.objects.create(
            process=process,
            normative_snapshot=normative_snapshot,
            snapshot_label="matriz-1",
            data_fingerprint="fp-1",
            serialized_matrix_payload={},
            is_current=True,
        )

        with self.assertRaises(IntegrityError):
            ConsolidatedMatrixSnapshot.objects.create(
                process=process,
                normative_snapshot=normative_snapshot,
                snapshot_label="matriz-2",
                data_fingerprint="fp-2",
                serialized_matrix_payload={},
                is_current=True,
                version_no=2,
            )


class BidderConsolidatedResultTests(TestCase):
    def setUp(self):
        self.process = create_process()
        self.other_process = create_process(code="PROC-002", name="Proceso 2")
        self.bidder = create_bidder(process=self.process)
        self.other_bidder = create_bidder(
            process=self.other_process,
            identification_number="900000099",
            name="Proponente 2",
        )
        source = NormativeSource.objects.create(code="CCE-CONS2", name="Colombia Compra 2")
        family = DocumentTypeFamily.objects.create(source=source, code="DT-CONS2", name="Doc tipo consolidacion 2")
        version = DocumentTypeVersion.objects.create(family=family, version_label="v1")
        self.normative_snapshot = NormativeSnapshot.objects.create(
            process=self.process,
            document_type_version=version,
            snapshot_label="norma",
            payload={},
            checksum="norma-2",
            is_current=True,
        )
        self.matrix_snapshot = ConsolidatedMatrixSnapshot.objects.create(
            process=self.process,
            normative_snapshot=self.normative_snapshot,
            snapshot_label="matriz",
            data_fingerprint="fp-ok",
            serialized_matrix_payload={},
            is_current=True,
        )

    def test_valid_bidder_consolidated_result(self):
        result = BidderConsolidatedResult(
            process=self.process,
            bidder=self.bidder,
            matrix_snapshot=self.matrix_snapshot,
            trace_payload={"source": "test"},
        )
        result.full_clean()
        result.save()
        self.assertEqual(BidderConsolidatedResult.objects.count(), 1)

    def test_rejects_bidder_from_other_process(self):
        result = BidderConsolidatedResult(
            process=self.process,
            bidder=self.other_bidder,
            matrix_snapshot=self.matrix_snapshot,
            trace_payload={"source": "test"},
        )
        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_rejects_matrix_snapshot_from_other_process(self):
        other_source = NormativeSource.objects.create(code="CCE-CONS3", name="Colombia Compra 3")
        other_family = DocumentTypeFamily.objects.create(source=other_source, code="DT-CONS3", name="Doc tipo 3")
        other_version = DocumentTypeVersion.objects.create(family=other_family, version_label="v1")
        other_normative_snapshot = NormativeSnapshot.objects.create(
            process=self.other_process,
            document_type_version=other_version,
            snapshot_label="norma-otra",
            payload={},
            checksum="norma-3",
            is_current=True,
        )
        other_matrix_snapshot = ConsolidatedMatrixSnapshot.objects.create(
            process=self.other_process,
            normative_snapshot=other_normative_snapshot,
            snapshot_label="matriz-otra",
            data_fingerprint="fp-other",
            serialized_matrix_payload={},
            is_current=True,
        )
        result = BidderConsolidatedResult(
            process=self.process,
            bidder=self.bidder,
            matrix_snapshot=other_matrix_snapshot,
            trace_payload={"source": "test"},
        )
        with self.assertRaises(ValidationError):
            result.full_clean()
