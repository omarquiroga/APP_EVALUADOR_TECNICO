from django.core.exceptions import ValidationError
from django.test import TestCase

from causals.models import RejectionCauseAssessment, RejectionCauseDefinition
from common.tests.helpers import create_bidder, create_bidder_member, create_process
from evaluation.models import ValidationDecisionRecord
from rules.models import RuleDefinition, RuleVersion


class RejectionCauseAssessmentTests(TestCase):
    def setUp(self):
        self.process = create_process()
        self.other_process = create_process(code="PROC-002", name="Proceso 2")
        self.bidder = create_bidder(process=self.process)
        self.other_bidder = create_bidder(
            process=self.other_process,
            identification_number="900000099",
            name="Proponente 2",
        )
        self.member = create_bidder_member(self.bidder)
        self.rule_definition = RuleDefinition.objects.create(
            code="RULE-CAUSAL-1",
            name="Regla causal",
            module="bidders",
            rule_type="boolean",
        )
        self.rule_version = RuleVersion.objects.create(
            rule_definition=self.rule_definition,
            process=self.process,
            version_label="1",
            parameters={},
            checksum="hash-causal-rule",
            version_no=1,
        )
        self.triggering_decision = ValidationDecisionRecord.objects.create(
            process=self.process,
            bidder=self.bidder,
            module="bidders",
            subject_type="bidder_member",
            subject_uuid=self.member.pk,
            rule_definition=self.rule_definition,
            rule_version=self.rule_version,
            bidder_member=self.member,
            input_payload={"source": "test", "evaluated_value": str(self.member.pk)},
            logic_trace={"rule": self.rule_definition.code, "step": "trigger"},
        )
        self.cause_definition = RejectionCauseDefinition.objects.create(
            process=self.process,
            code="CAUSE-1",
            name="Causal 1",
        )

    def test_accepts_valid_triggering_decision_record(self):
        assessment = RejectionCauseAssessment(
            process=self.process,
            bidder=self.bidder,
            cause_definition=self.cause_definition,
            triggering_decision_record=self.triggering_decision,
            status="suggested",
        )
        assessment.full_clean()
        assessment.save()
        self.assertEqual(RejectionCauseAssessment.objects.count(), 1)

    def test_rejects_triggering_decision_from_other_process(self):
        other_rule_definition = RuleDefinition.objects.create(
            code="RULE-CAUSAL-2",
            name="Regla causal 2",
            module="bidders",
            rule_type="boolean",
        )
        other_rule_version = RuleVersion.objects.create(
            rule_definition=other_rule_definition,
            process=self.other_process,
            version_label="1",
            parameters={},
            checksum="hash-other-rule",
            version_no=1,
        )
        other_member = create_bidder_member(self.other_bidder, identification_number="100000099", name="Miembro 2")
        other_decision = ValidationDecisionRecord.objects.create(
            process=self.other_process,
            bidder=self.other_bidder,
            module="bidders",
            subject_type="bidder_member",
            subject_uuid=other_member.pk,
            rule_definition=other_rule_definition,
            rule_version=other_rule_version,
            bidder_member=other_member,
            input_payload={"source": "test", "evaluated_value": str(other_member.pk)},
            logic_trace={"rule": other_rule_definition.code, "step": "trigger"},
        )
        assessment = RejectionCauseAssessment(
            process=self.process,
            bidder=self.bidder,
            cause_definition=self.cause_definition,
            triggering_decision_record=other_decision,
            status="under_review",
        )
        with self.assertRaises(ValidationError):
            assessment.full_clean()

    def test_rejects_cause_definition_from_other_process(self):
        other_cause_definition = RejectionCauseDefinition.objects.create(
            process=self.other_process,
            code="CAUSE-2",
            name="Causal 2",
        )
        assessment = RejectionCauseAssessment(
            process=self.process,
            bidder=self.bidder,
            cause_definition=other_cause_definition,
            triggering_decision_record=self.triggering_decision,
        )
        with self.assertRaises(ValidationError):
            assessment.full_clean()

    def test_allows_basic_causal_states(self):
        for status in ["not_triggered", "alert_detected", "suggested", "under_review", "confirmed", "dismissed", "obsolete"]:
            assessment = RejectionCauseAssessment(
                process=self.process,
                bidder=self.bidder,
                cause_definition=self.cause_definition,
                triggering_decision_record=self.triggering_decision,
                status=status,
            )
            assessment.full_clean()
