from django.test import TestCase

from causals.models import RejectionCauseAssessment, RejectionCauseDefinition
from common.tests.helpers import create_bidder, create_document, create_process
from consolidation.models import BidderConsolidatedResult, ConsolidatedMatrixSnapshot
from documents.models import DocumentVersion
from evaluation.models import ValidationDecisionRecord
from normative.models import DocumentTypeFamily, DocumentTypeVersion, NormativeSnapshot, NormativeSource
from rules.models import RuleDefinition, RuleVersion


class CoreFlowEndToEndTests(TestCase):
    def test_core_flow_process_to_consolidation(self):
        process = create_process(code="PROC-E2E", name="Proceso E2E")
        bidder = create_bidder(process=process, identification_number="900000777", name="Proponente E2E")
        document = create_document(process=process, bidder=bidder, name="Oferta tecnica", document_type="oferta")
        document_version = DocumentVersion.objects.create(
            document=document,
            file="documents/oferta-tecnica.pdf",
            original_filename="oferta-tecnica.pdf",
            file_hash="hash-oferta-e2e",
            is_current=True,
        )

        source = NormativeSource.objects.create(code="CCE-E2E", name="Colombia Compra E2E")
        family = DocumentTypeFamily.objects.create(source=source, code="DT-E2E", name="Documento Tipo E2E")
        doc_type_version = DocumentTypeVersion.objects.create(family=family, version_label="v1")
        normative_snapshot = NormativeSnapshot.objects.create(
            process=process,
            document_type_version=doc_type_version,
            snapshot_label="snapshot-e2e",
            payload={"source": "test"},
            checksum="checksum-e2e",
            is_current=True,
        )

        rule_definition = RuleDefinition.objects.create(
            code="RULE-E2E-1",
            name="Regla E2E",
            module="documents",
            rule_type="boolean",
        )
        rule_version = RuleVersion.objects.create(
            rule_definition=rule_definition,
            process=process,
            normative_snapshot=normative_snapshot,
            version_label="1",
            parameters={"required": True},
            checksum="rule-checksum-e2e",
            version_no=1,
        )

        validation = ValidationDecisionRecord(
            process=process,
            bidder=bidder,
            module="documents",
            subject_type="document",
            subject_uuid=document.pk,
            rule_definition=rule_definition,
            rule_version=rule_version,
            normative_snapshot=normative_snapshot,
            document=document,
            input_payload={
                "source": "test",
                "input_kind": "document",
                "evaluated_value": str(document.pk),
            },
            logic_trace={
                "rule_code": rule_definition.code,
                "rule_version": rule_version.version_label,
                "evaluation_mode": "manual_test",
                "summary": "Documento presente y asociado al proceso",
            },
            result_code="meets",
            status="confirmed",
        )
        validation.full_clean()
        validation.save()

        cause_definition = RejectionCauseDefinition.objects.create(
            process=process,
            code="CAUSE-E2E-1",
            name="Causal E2E",
        )
        cause_assessment = RejectionCauseAssessment(
            process=process,
            bidder=bidder,
            cause_definition=cause_definition,
            triggering_decision_record=validation,
            status="dismissed",
        )
        cause_assessment.full_clean()
        cause_assessment.save()

        matrix_snapshot = ConsolidatedMatrixSnapshot.objects.create(
            process=process,
            normative_snapshot=normative_snapshot,
            snapshot_label="matriz-e2e",
            data_fingerprint="fingerprint-e2e",
            serialized_matrix_payload={"bidder_count": 1},
            is_current=True,
        )
        consolidated_result = BidderConsolidatedResult(
            process=process,
            bidder=bidder,
            matrix_snapshot=matrix_snapshot,
            technical_result="meets",
            rup_result="pending",
            experience_general_result="pending",
            experience_specific_result="pending",
            financial_result="pending",
            rejection_result="pending",
            final_result="conditional",
            trace_payload={
                "validation_id": str(validation.pk),
                "cause_assessment_id": str(cause_assessment.pk),
                "document_version_id": str(document_version.pk),
            },
        )
        consolidated_result.full_clean()
        consolidated_result.save()

        self.assertEqual(validation.document_id, document.pk)
        self.assertEqual(cause_assessment.triggering_decision_record_id, validation.pk)
        self.assertEqual(consolidated_result.matrix_snapshot_id, matrix_snapshot.pk)
        self.assertEqual(consolidated_result.bidder_id, bidder.pk)
