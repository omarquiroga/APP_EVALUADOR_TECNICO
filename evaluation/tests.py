from django.core.exceptions import ValidationError
from django.test import TestCase

from common.tests.helpers import create_bidder, create_bidder_member, create_document, create_process
from evaluation.models import ValidationDecisionRecord
from rules.models import RuleDefinition, RuleVersion


class ValidationDecisionRecordTests(TestCase):
    def setUp(self):
        self.process = create_process()
        self.other_process = create_process(code="PROC-002", name="Proceso 2")
        self.bidder = create_bidder(process=self.process)
        self.other_bidder = create_bidder(
            process=self.other_process,
            identification_number="900000009",
            name="Proponente 2",
        )
        self.member = create_bidder_member(self.bidder)
        self.rule_definition = RuleDefinition.objects.create(
            code="RULE-EVAL-1",
            name="Regla evaluacion",
            module="bidders",
            rule_type="boolean",
        )
        self.rule_version = RuleVersion.objects.create(
            rule_definition=self.rule_definition,
            process=self.process,
            version_label="1",
            parameters={},
            checksum="hash-rule-1",
            version_no=1,
        )

    def build_record(self, **overrides):
        data = {
            "process": self.process,
            "bidder": self.bidder,
            "module": "bidders",
            "subject_type": "bidder_member",
            "subject_uuid": self.member.pk,
            "rule_definition": self.rule_definition,
            "rule_version": self.rule_version,
            "bidder_member": self.member,
            "input_payload": {"source": "test", "evaluated_value": str(self.member.pk)},
            "logic_trace": {"rule": self.rule_definition.code, "step": "unit_test"},
        }
        data.update(overrides)
        return ValidationDecisionRecord(**data)

    def test_accepts_exactly_one_valid_subject_fk(self):
        record = self.build_record()
        record.full_clean()
        record.save()
        self.assertEqual(ValidationDecisionRecord.objects.count(), 1)

    def test_rejects_multiple_subject_fks(self):
        document = create_document(process=self.process, bidder=self.bidder, name="Soporte", document_type="anexo")
        record = self.build_record(document=document)
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_rejects_incompatible_subject_type(self):
        record = self.build_record(subject_type="document")
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_rejects_subject_uuid_not_matching_fk(self):
        record = self.build_record(subject_uuid=self.bidder.pk)
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_rejects_bidder_from_other_process(self):
        record = self.build_record(bidder=self.other_bidder)
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_rejects_member_not_belonging_to_bidder(self):
        other_member = create_bidder_member(self.other_bidder, identification_number="100000009", name="Otro miembro")
        record = self.build_record(bidder_member=other_member, subject_uuid=other_member.pk)
        with self.assertRaises(ValidationError):
            record.full_clean()
