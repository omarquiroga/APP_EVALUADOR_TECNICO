from django.db import models


class ProcessState(models.TextChoices):
    DRAFT = "draft", "Borrador"
    NORMATIVE_BOUND = "normative_bound", "Base normativa vinculada"
    CONFIGURED = "configured", "Configurado"
    IN_EVALUATION = "in_evaluation", "En evaluacion"
    UNDER_REVIEW = "under_review", "En revision"
    READY_FOR_CLOSURE = "ready_for_closure", "Listo para cierre"
    CLOSED = "closed", "Cerrado"
    ARCHIVED = "archived", "Archivado"


class BidderState(models.TextChoices):
    REGISTERED = "registered", "Registrado"
    DOCUMENTS_PENDING = "documents_pending", "Documentos pendientes"
    UNDER_VALIDATION = "under_validation", "En validacion"
    WITH_ALERTS = "with_alerts", "Con alertas"
    WITH_SUGGESTED_REJECTION = "with_suggested_rejection", "Con causal sugerida"
    ELIGIBLE_FOR_REVIEW = "eligible_for_review", "Listo para revision"
    FINALIZED = "finalized", "Finalizado"
    CLOSED_SNAPSHOT = "closed_snapshot", "Congelado al cierre"


class ValidationStatus(models.TextChoices):
    NOT_EVALUATED = "not_evaluated", "No evaluado"
    PRELIMINAR = "preliminar", "Preliminar"
    NEEDS_HUMAN_REVIEW = "needs_human_review", "Requiere revision humana"
    CONFIRMED = "confirmed", "Confirmado"
    ADJUSTED_BY_HUMAN = "adjusted_by_human", "Ajustado por humano"
    REJECTED = "rejected", "Rechazado"
    OBSOLETE = "obsolete", "Obsoleto"
    VOIDED = "voided", "Anulado"


class CauseStatus(models.TextChoices):
    NOT_TRIGGERED = "not_triggered", "No activada"
    ALERT_DETECTED = "alert_detected", "Alerta detectada"
    SUGGESTED = "suggested", "Sugerida"
    UNDER_REVIEW = "under_review", "En revision"
    CONFIRMED = "confirmed", "Confirmada"
    DISMISSED = "dismissed", "Descartada"
    OBSOLETE = "obsolete", "Obsoleta"


class ResultCode(models.TextChoices):
    MEETS = "meets", "Cumple"
    NOT_MEETS = "not_meets", "No cumple"
    CONDITIONAL = "conditional", "Condicionado"
    PENDING = "pending", "Pendiente"


class SeverityLevel(models.TextChoices):
    LOW = "low", "Baja"
    MEDIUM = "medium", "Media"
    HIGH = "high", "Alta"
    CRITICAL = "critical", "Critica"


class ConfidenceLevel(models.TextChoices):
    HIGH = "high", "Alta"
    MEDIUM = "medium", "Media"
    LOW = "low", "Baja"
    NOT_APPLICABLE = "not_applicable", "No aplica"


class RuleType(models.TextChoices):
    BOOLEAN = "boolean", "Booleana"
    THRESHOLD = "threshold", "Umbral"
    CODE_LIST = "code_list", "Lista de codigos"
    AGGREGATION = "aggregation", "Agregacion"
    PERCENTAGE = "percentage", "Porcentaje"
    DOCUMENT_PRESENCE = "document_presence", "Presencia documental"
    COMPOSITE = "composite", "Compuesta"


class ScopeType(models.TextChoices):
    GENERAL = "general", "General"
    SPECIFIC = "specific", "Especifica"


class SubjectType(models.TextChoices):
    BIDDER = "bidder", "Proponente"
    BIDDER_MEMBER = "bidder_member", "Integrante"
    DOCUMENT = "document", "Documento"
    RUP_RECORD = "rup_record", "Registro RUP"
    RUP_FIELD_VALUE = "rup_field_value", "Campo RUP"
    EXPERIENCE_RECORD = "experience_record", "Contrato de experiencia"
    EXPERIENCE_METRIC = "experience_metric", "Metrica de experiencia"
    FINANCIAL_INPUT_VERSION = "financial_input_version", "Input financiero"
    EXTERNAL_CHECK = "external_check", "Consulta externa"


class FinancialInputStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    SUBMITTED = "submitted", "Radicado"
    SUPERSEDED = "superseded", "Reemplazado"


class FinancialAssessmentStatus(models.TextChoices):
    PRELIMINAR = "preliminar", "Preliminar"
    CONFIRMED = "confirmed", "Confirmado"
    OBSOLETE = "obsolete", "Obsoleto"
    VOIDED = "voided", "Anulado"


class DocumentStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    REPLACED = "replaced", "Reemplazado"
    VOIDED = "voided", "Anulado"


class CheckStatus(models.TextChoices):
    NOT_RUN = "not_run", "No ejecutada"
    NO_MATCH = "no_match", "Sin coincidencia"
    MATCH = "match", "Con coincidencia"
    INCONCLUSIVE = "inconclusive", "No concluyente"
    ERROR = "error", "Error"
