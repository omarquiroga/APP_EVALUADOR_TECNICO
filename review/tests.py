from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from bidders.models import Bidder, BidderMember
from causals.models import RejectionCauseAssessment, RejectionCauseDefinition
from common.choices import CauseStatus, ConfidenceLevel, ResultCode, ValidationStatus
from consolidation.models import BidderConsolidatedResult, ConsolidatedMatrixSnapshot
from documents.models import Document, DocumentVersion
from evaluation.models import ValidationDecisionRecord, ValidationEvidenceLink
from experience.models import ExperienceMetric, ExperienceRecord
from finance.models import FinancialAssessment, FinancialInputVersion
from normative.models import (
    DocumentTypeFamily,
    DocumentTypeVersion,
    NormativeSnapshot,
    NormativeSource,
    ProcessNormativeBinding,
)
from procurement.models import ContractProcess
from rules.models import RuleDefinition, RuleVersion
from rup.models import RUPCodeEntry, RUPFieldSchema, RUPFieldValue, RUPRecord, RUPSegmentEntry


class ReviewViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="reviewer", password="test12345")
        cls.no_finance_perm_user = User.objects.create_user(username="no_finance_perm", password="test12345")
        cls.finance_reader_user = User.objects.create_user(username="finance_reader", password="test12345")
        cls.finance_input_user = User.objects.create_user(username="finance_input", password="test12345")
        cls.finance_assessment_user = User.objects.create_user(username="finance_assessment", password="test12345")

        permissions = Permission.objects.filter(
            content_type__app_label="finance",
            codename__in=[
                "view_financialinputversion",
                "view_financialassessment",
                "add_financialinputversion",
                "add_financialassessment",
            ],
        )
        permission_map = {permission.codename: permission for permission in permissions}
        cls.user.user_permissions.set(permissions)
        cls.finance_reader_user.user_permissions.set(
            [
                permission_map["view_financialinputversion"],
                permission_map["view_financialassessment"],
            ]
        )
        cls.finance_input_user.user_permissions.set(
            [
                permission_map["view_financialinputversion"],
                permission_map["view_financialassessment"],
                permission_map["add_financialinputversion"],
            ]
        )
        cls.finance_assessment_user.user_permissions.set(
            [
                permission_map["view_financialinputversion"],
                permission_map["view_financialassessment"],
                permission_map["add_financialassessment"],
            ]
        )

        cls.source = NormativeSource.objects.create(code="CCE", name="Colombia Compra")
        cls.family = DocumentTypeFamily.objects.create(
            source=cls.source,
            code="DT-REVIEW",
            name="Documento Tipo Review",
            sector="Infraestructura",
            modality="Licitacion",
        )
        cls.doc_type_version = DocumentTypeVersion.objects.create(
            family=cls.family,
            version_label="2026.1",
            is_active=True,
        )

        cls.process = ContractProcess.objects.create(
            code="PROC-REVIEW-001",
            name="Proceso Review 1",
            entity_name="Entidad Demo",
            process_type="licitacion_publica",
            modality="pliego_tipo",
            state="in_evaluation",
            opening_date=date(2026, 3, 1),
            closing_date=date(2026, 3, 30),
        )
        cls.other_process = ContractProcess.objects.create(
            code="PROC-REVIEW-002",
            name="Proceso Review 2",
            entity_name="Entidad Demo",
            process_type="licitacion_publica",
            modality="pliego_tipo",
            state="configured",
        )
        cls.closed_process = ContractProcess.objects.create(
            code="PROC-REVIEW-003",
            name="Proceso Cerrado",
            entity_name="Entidad Demo",
            process_type="licitacion_publica",
            modality="pliego_tipo",
            state="closed",
        )
        cls.archived_process = ContractProcess.objects.create(
            code="PROC-REVIEW-004",
            name="Proceso Archivado",
            entity_name="Entidad Demo",
            process_type="licitacion_publica",
            modality="pliego_tipo",
            state="archived",
        )

        cls.normative_snapshot = NormativeSnapshot.objects.create(
            process=cls.process,
            document_type_version=cls.doc_type_version,
            snapshot_label="Snapshot Review",
            payload={"seed": True},
            checksum="snapshot-review",
            is_current=True,
            version_no=1,
        )
        ProcessNormativeBinding.objects.create(
            process=cls.process,
            document_type_version=cls.doc_type_version,
            current_snapshot=cls.normative_snapshot,
        )

        cls.bidder = Bidder.objects.create(
            process=cls.process,
            name="Consorcio Review",
            identification_type="NIT",
            identification_number="900111222",
            bidder_type="consorcio",
            state="under_validation",
        )
        cls.other_bidder = Bidder.objects.create(
            process=cls.other_process,
            name="Otro Proponente",
            identification_type="NIT",
            identification_number="900333444",
            bidder_type="individual",
            state="registered",
        )
        cls.closed_bidder = Bidder.objects.create(
            process=cls.closed_process,
            name="Proponente Cerrado",
            identification_type="NIT",
            identification_number="900555666",
            bidder_type="individual",
            state="registered",
        )
        cls.archived_bidder = Bidder.objects.create(
            process=cls.archived_process,
            name="Proponente Archivado",
            identification_type="NIT",
            identification_number="900666777",
            bidder_type="individual",
            state="registered",
        )
        cls.member = BidderMember.objects.create(
            bidder=cls.bidder,
            name="Integrante Review",
            identification_type="CC",
            identification_number="111222333",
            participation_percentage=Decimal("60.00"),
            is_lead=True,
        )

        cls.document = Document.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            name="RUP principal",
            document_type="RUP",
            classification="habilitante",
            is_required=True,
        )
        cls.document_version = DocumentVersion.objects.create(
            document=cls.document,
            file="documents/test/rup.pdf",
            original_filename="rup.pdf",
            file_hash="hash-rup-review",
            page_count=6,
            is_current=True,
            version_no=1,
        )

        cls.rup_record = RUPRecord.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            source_document=cls.document_version,
            record_date=date(2026, 3, 10),
            issuer="Camara Demo",
            review_status=ValidationStatus.CONFIRMED,
            validity_note="RUP vigente",
            version_no=1,
        )
        cls.rup_schema = RUPFieldSchema.objects.create(
            code="SEGMENTO_72",
            label="Segmento 72",
            data_type="text",
            is_required=True,
            sort_order=1,
        )
        RUPFieldValue.objects.create(
            rup_record=cls.rup_record,
            schema=cls.rup_schema,
            value_text="72",
            version_no=1,
        )
        RUPSegmentEntry.objects.create(
            rup_record=cls.rup_record,
            segment_code="72",
            description="Servicios de construccion",
            version_no=1,
        )
        RUPCodeEntry.objects.create(
            rup_record=cls.rup_record,
            code_type="UNSPSC",
            code_value="72141100",
            description="Construccion vial",
            version_no=1,
        )

        cls.experience_document = Document.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            name="Contrato experiencia",
            document_type="CONTRATO",
            classification="experiencia",
        )
        cls.experience_document_version = DocumentVersion.objects.create(
            document=cls.experience_document,
            file="documents/test/contrato.pdf",
            original_filename="contrato.pdf",
            file_hash="hash-experience-review",
            page_count=10,
            is_current=True,
            version_no=1,
        )
        cls.experience_record = ExperienceRecord.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            bidder_member=cls.member,
            contract_identifier="EXP-REVIEW-001",
            contract_type="Obra publica",
            contract_object="Mejoramiento de via urbana",
            contract_value_nominal=Decimal("1200000000.00"),
            contract_currency="COP",
            contract_year=2024,
            participation_percentage=Decimal("60.00"),
            execution_length_value=Decimal("4.5"),
            execution_length_unit="km",
            is_general_experience_candidate=True,
            is_specific_experience_candidate=True,
            source_document=cls.experience_document_version,
            review_status=ValidationStatus.CONFIRMED,
            version_no=1,
        )
        ExperienceMetric.objects.create(
            experience_record=cls.experience_record,
            metric_code="road_length_km",
            metric_value_number=Decimal("4.5"),
            metric_unit="km",
            source="manual",
            version_no=1,
        )

        cls.rule_definition = RuleDefinition.objects.create(
            code="RULE-REVIEW-001",
            name="Validacion review",
            module="rup",
            rule_type="boolean",
            default_human_required=True,
        )
        cls.rule_version = RuleVersion.objects.create(
            rule_definition=cls.rule_definition,
            normative_snapshot=cls.normative_snapshot,
            process=cls.process,
            version_label="v1",
            parameters={"segment": "72"},
            checksum="rule-review-checksum",
            is_active=True,
            version_no=1,
        )

        cls.validation = ValidationDecisionRecord.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            module="rup",
            subject_type="rup_record",
            subject_uuid=cls.rup_record.id,
            rule_definition=cls.rule_definition,
            rule_version=cls.rule_version,
            normative_snapshot=cls.normative_snapshot,
            rup_record=cls.rup_record,
            input_payload={"source": "manual", "input_kind": "rup", "evaluated_value": "72"},
            logic_trace={
                "rule_code": "RULE-REVIEW-001",
                "rule_version": "v1",
                "evaluation_mode": "manual",
                "summary": "Segmento encontrado",
            },
            result_code=ResultCode.MEETS,
            confidence_level=ConfidenceLevel.HIGH,
            status=ValidationStatus.CONFIRMED,
            human_required=True,
            version_no=1,
        )
        ValidationEvidenceLink.objects.create(
            validation_decision=cls.validation,
            document_version=cls.document_version,
            evidence_role="support",
            note="Soporte principal",
        )

        cls.cause_definition = RejectionCauseDefinition.objects.create(
            process=cls.process,
            code="CAUSAL-001",
            name="Causal demo",
            is_subsanable=False,
            severity="high",
            human_required=True,
        )
        RejectionCauseAssessment.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            cause_definition=cls.cause_definition,
            triggering_decision_record=cls.validation,
            status=CauseStatus.UNDER_REVIEW,
            origin_type="mixed",
            is_subsanable=False,
            evidence_summary="Revision en curso",
            human_review_required=True,
            impact_on_closure=True,
            version_no=1,
        )

        cls.fin_input = FinancialInputVersion.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            source_label="Area financiera",
            source_document=cls.document_version,
            source_date=date(2026, 3, 15),
            assets_value=Decimal("2500000000.00"),
            liabilities_value=Decimal("800000000.00"),
            operating_income_value=Decimal("1400000000.00"),
            status="submitted",
            version_no=1,
        )
        cls.other_fin_input = FinancialInputVersion.objects.create(
            process=cls.other_process,
            bidder=cls.other_bidder,
            source_label="Area financiera externa",
            source_date=date(2026, 3, 16),
            assets_value=Decimal("500000000.00"),
            liabilities_value=Decimal("100000000.00"),
            operating_income_value=Decimal("250000000.00"),
            status="submitted",
            version_no=1,
        )
        FinancialAssessment.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            financial_input_version=cls.fin_input,
            result_code=ResultCode.MEETS,
            status="confirmed",
            used_in_consolidation=True,
            assessment_note="Resultado favorable",
            version_no=1,
        )

        cls.matrix_snapshot = ConsolidatedMatrixSnapshot.objects.create(
            process=cls.process,
            normative_snapshot=cls.normative_snapshot,
            snapshot_label="Matriz review",
            data_fingerprint="matrix-review",
            serialized_matrix_payload={"seed": True},
            is_current=True,
            version_no=1,
        )
        BidderConsolidatedResult.objects.create(
            process=cls.process,
            bidder=cls.bidder,
            matrix_snapshot=cls.matrix_snapshot,
            technical_result=ResultCode.MEETS,
            rup_result=ResultCode.MEETS,
            experience_general_result=ResultCode.MEETS,
            experience_specific_result=ResultCode.CONDITIONAL,
            financial_result=ResultCode.MEETS,
            rejection_result=ResultCode.PENDING,
            final_result=ResultCode.CONDITIONAL,
            observations="Resultado consolidado de prueba",
            trace_payload={"source": "test"},
            version_no=1,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_process_list_responds_200(self):
        response = self.client.get(reverse("review:process_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Procesos de contratacion")
        self.assertContains(response, self.process.code)

    def test_process_detail_responds_200_for_valid_process(self):
        response = self.client.get(reverse("review:process_detail", kwargs={"process_id": self.process.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.process.name)
        self.assertContains(response, "Ver proponentes")

    def test_bidder_list_responds_200_for_valid_process(self):
        response = self.client.get(reverse("review:process_bidder_list", kwargs={"process_id": self.process.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.bidder.name)
        self.assertContains(response, "Abrir expediente")

    def test_bidder_dossier_responds_200_for_valid_bidder_in_process(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Expediente del proponente")
        self.assertContains(response, self.bidder.name)

    def test_finance_overview_responds_200_for_valid_bidder(self):
        response = self.client.get(
            reverse(
                "review:finance_overview",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contexto financiero del proponente")
        self.assertContains(response, "Evaluación financiera vigente")
        self.assertContains(response, "Último insumo registrado")
        self.assertContains(response, self.fin_input.source_label)

    def test_finance_overview_requires_finance_read_permissions(self):
        self.client.force_login(self.no_finance_perm_user)
        response = self.client.get(
            reverse(
                "review:finance_overview",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_finance_overview_allows_finance_reader(self):
        self.client.force_login(self.finance_reader_user)
        response = self.client.get(
            reverse(
                "review:finance_overview",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contexto financiero del proponente")

    def test_financial_input_detail_responds_200_for_valid_input_within_context(self):
        response = self.client.get(
            reverse(
                "review:financial_input_detail",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detalle del insumo financiero")
        self.assertContains(response, self.fin_input.source_label)

    def test_financial_input_detail_responds_404_if_input_does_not_belong_to_bidder(self):
        response = self.client.get(
            reverse(
                "review:financial_input_detail",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.other_fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_financial_input_detail_requires_finance_read_permissions(self):
        self.client.force_login(self.no_finance_perm_user)
        response = self.client.get(
            reverse(
                "review:financial_input_detail",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_financial_input_create_get_responds_200_for_valid_context(self):
        response = self.client.get(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registrar nueva versión de insumo financiero")

    def test_financial_input_create_post_valid_creates_submitted_version(self):
        response = self.client.post(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            ),
            {
                "source_label": "Nuevo corte financiero",
                "source_document": str(self.document_version.id),
                "source_date": "2026-03-20",
                "assets_value": "3000000000.00",
                "liabilities_value": "900000000.00",
                "operating_income_value": "1600000000.00",
                "financial_observation": "Cargado desde review",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        created_input = FinancialInputVersion.objects.get(source_label="Nuevo corte financiero")
        self.assertEqual(created_input.status, "submitted")
        self.assertEqual(created_input.process_id, self.process.id)
        self.assertEqual(created_input.bidder_id, self.bidder.id)
        self.assertEqual(created_input.version_no, 2)
        self.assertEqual(created_input.supersedes_id, self.fin_input.id)
        self.assertContains(response, "Insumo financiero registrado como nueva versión.")

    def test_financial_input_create_post_invalid_does_not_create_record(self):
        before_count = FinancialInputVersion.objects.count()
        response = self.client.post(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            ),
            {
                "source_label": "Intento invalido",
                "source_date": "",
                "assets_value": "-1",
                "liabilities_value": "100",
                "operating_income_value": "200",
                "financial_observation": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FinancialInputVersion.objects.count(), before_count)
        self.assertContains(response, "Los activos no pueden ser negativos.")

    def test_financial_input_create_responds_404_if_bidder_does_not_belong_to_process(self):
        response = self.client.get(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.other_bidder.id},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_financial_input_create_is_blocked_for_closed_process(self):
        response = self.client.get(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.closed_process.id, "bidder_id": self.closed_bidder.id},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_financial_input_create_requires_input_permission(self):
        self.client.force_login(self.finance_reader_user)
        response = self.client.get(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_financial_input_create_allows_input_user(self):
        self.client.force_login(self.finance_input_user)
        response = self.client.get(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registrar nueva versión de insumo financiero")

    def test_financial_assessment_create_get_responds_200_for_valid_context(self):
        response = self.client.get(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear y confirmar")
        self.assertNotContains(response, 'name="used_in_consolidation"', html=False)
        self.assertContains(response, "queda vigente")

    def test_financial_assessment_create_post_valid_creates_assessment(self):
        response = self.client.post(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            ),
            {
                "result_code": ResultCode.CONDITIONAL,
                "assessment_note": "Nuevo assessment de prueba",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        previous_current = FinancialAssessment.objects.get(assessment_note="Resultado favorable")
        created_assessment = FinancialAssessment.objects.get(assessment_note="Nuevo assessment de prueba")
        self.assertEqual(created_assessment.status, "confirmed")
        self.assertEqual(created_assessment.process_id, self.process.id)
        self.assertEqual(created_assessment.bidder_id, self.bidder.id)
        self.assertEqual(created_assessment.financial_input_version_id, self.fin_input.id)
        self.assertTrue(created_assessment.used_in_consolidation)
        self.assertEqual(created_assessment.supersedes_id, previous_current.id)
        self.assertEqual(created_assessment.reviewed_by_id, self.user.id)
        self.assertIsNotNone(created_assessment.reviewed_at)
        self.assertContains(response, "Evaluación financiera confirmada correctamente.")

    def test_financial_assessment_create_keeps_only_one_current_assessment(self):
        FinancialAssessment.objects.create(
            process=self.process,
            bidder=self.bidder,
            financial_input_version=self.fin_input,
            result_code=ResultCode.PENDING,
            status="confirmed",
            used_in_consolidation=False,
            assessment_note="Assessment previo no vigente",
            version_no=2,
        )
        response = self.client.post(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            ),
            {
                "result_code": ResultCode.CONDITIONAL,
                "assessment_note": "Assessment vigente nuevo",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FinancialAssessment.objects.filter(process=self.process, bidder=self.bidder, used_in_consolidation=True).count(),
            1,
        )
        new_current = FinancialAssessment.objects.get(assessment_note="Assessment vigente nuevo")
        self.assertTrue(new_current.used_in_consolidation)
        previous_current = FinancialAssessment.objects.get(assessment_note="Resultado favorable")
        self.assertEqual(previous_current.status, "obsolete")
        self.assertFalse(previous_current.used_in_consolidation)
        self.assertEqual(new_current.supersedes_id, previous_current.id)

    def test_financial_assessment_create_supersedes_current_assessment_not_latest_non_current(self):
        FinancialAssessment.objects.create(
            process=self.process,
            bidder=self.bidder,
            financial_input_version=self.fin_input,
            result_code=ResultCode.PENDING,
            status="confirmed",
            used_in_consolidation=False,
            assessment_note="Assessment no vigente más reciente",
            version_no=2,
        )
        response = self.client.post(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            ),
            {
                "result_code": ResultCode.CONDITIONAL,
                "assessment_note": "Assessment reemplaza vigente",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        new_assessment = FinancialAssessment.objects.get(assessment_note="Assessment reemplaza vigente")
        previous_current = FinancialAssessment.objects.get(assessment_note="Resultado favorable")
        self.assertEqual(new_assessment.supersedes_id, previous_current.id)
        self.assertTrue(new_assessment.used_in_consolidation)
        self.assertEqual(previous_current.status, "obsolete")

    def test_financial_assessment_create_post_invalid_does_not_create_record(self):
        before_count = FinancialAssessment.objects.count()
        response = self.client.post(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            ),
            {
                "result_code": "",
                "assessment_note": "Intento invalido",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FinancialAssessment.objects.count(), before_count)
        self.assertContains(response, "Este campo es obligatorio.")

    def test_financial_assessment_create_responds_404_if_input_does_not_belong_to_context(self):
        response = self.client.get(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.other_fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_financial_assessment_create_is_blocked_for_closed_process(self):
        closed_input = FinancialInputVersion.objects.create(
            process=self.closed_process,
            bidder=self.closed_bidder,
            source_label="Input cerrado",
            source_date=date(2026, 3, 18),
            assets_value=Decimal("1000.00"),
            liabilities_value=Decimal("500.00"),
            operating_income_value=Decimal("250.00"),
            status="submitted",
            version_no=1,
        )
        response = self.client.get(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.closed_process.id,
                    "bidder_id": self.closed_bidder.id,
                    "input_id": closed_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_financial_assessment_create_is_blocked_for_archived_process(self):
        archived_input = FinancialInputVersion.objects.create(
            process=self.archived_process,
            bidder=self.archived_bidder,
            source_label="Input archivado",
            source_date=date(2026, 3, 18),
            assets_value=Decimal("1000.00"),
            liabilities_value=Decimal("500.00"),
            operating_income_value=Decimal("250.00"),
            status="submitted",
            version_no=1,
        )
        response = self.client.get(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.archived_process.id,
                    "bidder_id": self.archived_bidder.id,
                    "input_id": archived_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_financial_assessment_create_requires_assessment_permission(self):
        self.client.force_login(self.finance_input_user)
        response = self.client.get(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_financial_assessment_create_allows_assessment_user(self):
        self.client.force_login(self.finance_assessment_user)
        response = self.client.post(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            ),
            {
                "result_code": ResultCode.CONDITIONAL,
                "assessment_note": "Assessment por usuario autorizado",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        created_assessment = FinancialAssessment.objects.get(assessment_note="Assessment por usuario autorizado")
        self.assertEqual(created_assessment.reviewed_by_id, self.finance_assessment_user.id)

    def test_bidder_dossier_responds_404_if_bidder_does_not_belong_to_process(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier",
                kwargs={"process_id": self.process.id, "bidder_id": self.other_bidder.id},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_each_htmx_block_responds_correctly(self):
        expected_snippets = {
            "documents": "Documentos del expediente",
            "rup": "Registros RUP del proponente",
            "experience": "Contratos de experiencia",
            "validations": "Registros de validacion",
            "causals": "Causales evaluadas",
            "consolidation": "Consolidacion del proponente",
        }
        for section, expected_text in expected_snippets.items():
            with self.subTest(section=section):
                response = self.client.get(
                    reverse(
                        "review:bidder_dossier_section",
                        kwargs={
                            "process_id": self.process.id,
                            "bidder_id": self.bidder.id,
                            "section": section,
                        },
                    ),
                    HTTP_HX_REQUEST="true",
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)

    def test_consolidation_section_emphasizes_final_result(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier_section",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "section": "consolidation",
                },
            ),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resultado final")
        self.assertContains(response, self.matrix_snapshot.snapshot_label)
        self.assertContains(response, "Resultados por dimension")

    def test_consolidation_section_shows_clear_empty_state_without_results(self):
        empty_bidder = Bidder.objects.create(
            process=self.process,
            name="Sin consolidacion",
            identification_type="NIT",
            identification_number="900777888",
            bidder_type="individual",
            state="registered",
        )
        response = self.client.get(
            reverse(
                "review:bidder_dossier_section",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": empty_bidder.id,
                    "section": "consolidation",
                },
            ),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aun no existe consolidacion para este proponente.")

    def test_documents_section_can_filter_by_document_type(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier_section",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "section": "documents",
                },
            ),
            {"document_type": "RUP"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RUP principal")
        self.assertNotContains(response, "Contrato experiencia")

    def test_documents_section_shows_empty_state_for_document_type_filter_without_matches(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier_section",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "section": "documents",
                },
            ),
            {"document_type": "ANEXO_INEXISTENTE"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay documentos para este proponente con el tipo documental seleccionado.")

    def test_bidder_dossier_respects_section_query_param(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            ),
            {"section": "validations"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registros de validacion")
        self.assertContains(response, "hx-push-url")

    def test_validations_section_can_filter_by_status(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier_section",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "section": "validations",
                },
            ),
            {"validation_status": ValidationStatus.REJECTED},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay validaciones para este proponente con el filtro actual.")

    def test_breadcrumbs_and_basic_navigation_render(self):
        response = self.client.get(
            reverse(
                "review:bidder_dossier",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/review/processes/"', html=False)
        self.assertContains(response, self.process.code)
        self.assertContains(response, "Volver a proponentes")
        for label in ["Documentos", "RUP", "Experiencia", "Validaciones", "Causales", "Consolidacion"]:
            self.assertContains(response, label)
        self.assertContains(response, "data-review-section-link")

    def test_login_required_on_review_views(self):
        self.client.logout()
        response = self.client.get(reverse("review:process_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        response = self.client.get(
            reverse(
                "review:finance_overview",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        response = self.client.get(
            reverse(
                "review:financial_input_create",
                kwargs={"process_id": self.process.id, "bidder_id": self.bidder.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        response = self.client.get(
            reverse(
                "review:financial_assessment_create",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        response = self.client.get(
            reverse(
                "review:financial_input_detail",
                kwargs={
                    "process_id": self.process.id,
                    "bidder_id": self.bidder.id,
                    "input_id": self.fin_input.id,
                },
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
