from django.db import IntegrityError
from django.test import TransactionTestCase

from common.tests.helpers import create_process
from normative.models import DocumentTypeFamily, DocumentTypeVersion, NormativeSnapshot, NormativeSource
from rules.models import ProcessRuleActivation, RuleDefinition, RuleVersion


class ProcessRuleActivationConstraintTests(TransactionTestCase):
    def test_only_one_active_version_per_process_and_rule_definition(self):
        process = create_process()
        source = NormativeSource.objects.create(code="CCE", name="Colombia Compra")
        family = DocumentTypeFamily.objects.create(source=source, code="DT-RULE", name="Doc tipo regla")
        version = DocumentTypeVersion.objects.create(family=family, version_label="v1")
        snapshot = NormativeSnapshot.objects.create(
            process=process,
            document_type_version=version,
            snapshot_label="snap",
            payload={},
            checksum="abc",
        )
        definition = RuleDefinition.objects.create(code="RULE-1", name="Regla 1", module="rup", rule_type="boolean")
        rv1 = RuleVersion.objects.create(
            rule_definition=definition,
            normative_snapshot=snapshot,
            process=process,
            version_label="1",
            parameters={},
            checksum="hash-1",
            version_no=1,
        )
        rv2 = RuleVersion.objects.create(
            rule_definition=definition,
            normative_snapshot=snapshot,
            process=process,
            version_label="2",
            parameters={},
            checksum="hash-2",
            version_no=2,
        )
        ProcessRuleActivation.objects.create(
            process=process,
            rule_definition=definition,
            rule_version=rv1,
            is_active=True,
        )

        with self.assertRaises(IntegrityError):
            ProcessRuleActivation.objects.create(
                process=process,
                rule_definition=definition,
                rule_version=rv2,
                is_active=True,
            )
