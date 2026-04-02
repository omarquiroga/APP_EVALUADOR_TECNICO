from django.db import IntegrityError
from django.test import TransactionTestCase

from common.tests.helpers import create_process
from normative.models import DocumentTypeFamily, DocumentTypeVersion, NormativeSnapshot, NormativeSource


class NormativeSnapshotConstraintTests(TransactionTestCase):
    def test_only_one_current_snapshot_per_process(self):
        process = create_process()
        source = NormativeSource.objects.create(code="CCE", name="Colombia Compra")
        family = DocumentTypeFamily.objects.create(source=source, code="DT-1", name="Doc tipo")
        version = DocumentTypeVersion.objects.create(family=family, version_label="v1")
        NormativeSnapshot.objects.create(
            process=process,
            document_type_version=version,
            snapshot_label="base",
            payload={},
            checksum="abc",
            is_current=True,
        )

        with self.assertRaises(IntegrityError):
            NormativeSnapshot.objects.create(
                process=process,
                document_type_version=version,
                snapshot_label="nuevo",
                payload={},
                checksum="def",
                is_current=True,
            )
