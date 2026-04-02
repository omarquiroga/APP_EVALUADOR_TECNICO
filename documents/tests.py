from django.db import IntegrityError
from django.test import TransactionTestCase

from common.tests.helpers import create_document, create_process
from documents.models import DocumentVersion


class DocumentVersionConstraintTests(TransactionTestCase):
    def test_only_one_current_version_per_document(self):
        process = create_process()
        document = create_document(process=process)
        DocumentVersion.objects.create(
            document=document,
            file="documents/test-1.pdf",
            original_filename="test-1.pdf",
            file_hash="hash-1",
            is_current=True,
        )

        with self.assertRaises(IntegrityError):
            DocumentVersion.objects.create(
                document=document,
                file="documents/test-2.pdf",
                original_filename="test-2.pdf",
                file_hash="hash-2",
                is_current=True,
            )
