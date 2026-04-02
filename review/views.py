from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from audit.models import AuditEvent
from bidders.models import Bidder
from causals.models import RejectionCauseAssessment
from common.choices import FinancialAssessmentStatus, FinancialInputStatus, ProcessState, ValidationStatus
from consolidation.models import BidderConsolidatedResult, ConsolidatedMatrixSnapshot
from documents.models import Document, DocumentVersion
from evaluation.models import ValidationDecisionRecord, ValidationEvidenceLink
from experience.models import ExperienceMetric, ExperienceRecord
from finance.models import FinancialAssessment, FinancialInputVersion
from procurement.models import ContractProcess
from rup.models import RUPCodeEntry, RUPFieldValue, RUPRecord, RUPSegmentEntry

from .forms import FinancialAssessmentCreateForm, FinancialInputVersionCreateForm


SECTION_LABELS = {
    "documents": "Documentos",
    "rup": "RUP",
    "experience": "Experiencia",
    "validations": "Validaciones",
    "causals": "Causales",
    "consolidation": "Consolidacion",
}

FINANCE_READ_PERMISSIONS = (
    "finance.view_financialinputversion",
    "finance.view_financialassessment",
)
FINANCE_INPUT_CREATE_PERMISSIONS = (*FINANCE_READ_PERMISSIONS, "finance.add_financialinputversion")
FINANCE_ASSESSMENT_CREATE_PERMISSIONS = (*FINANCE_READ_PERMISSIONS, "finance.add_financialassessment")


def _crumb(label, route_name=None, **kwargs):
    return {
        "label": label,
        "url": reverse(route_name, kwargs=kwargs) if route_name else None,
    }


def _get_process(process_id):
    process = get_object_or_404(
        ContractProcess.objects.select_related(
            "normative_binding__document_type_version__family",
            "normative_binding__current_snapshot",
        ).annotate(bidder_count=Count("bidders", distinct=True)),
        pk=process_id,
    )
    process.normative_binding_safe = getattr(process, "normative_binding", None)
    return process


def _get_bidder(process_id, bidder_id):
    return get_object_or_404(
        Bidder.objects.select_related("process").annotate(
            document_count=Count("documents", distinct=True),
            validation_count=Count("validation_decisions", distinct=True),
            causal_count=Count("rejection_cause_assessments", distinct=True),
            consolidation_count=Count("consolidated_results", distinct=True),
        ),
        pk=bidder_id,
        process_id=process_id,
    )


def _get_financial_input(process_id, bidder_id, input_id):
    return get_object_or_404(
        FinancialInputVersion.objects.select_related("process", "bidder", "source_document__document").filter(
            process_id=process_id,
            bidder_id=bidder_id,
        ),
        pk=input_id,
    )


def _assert_finance_write_allowed(process):
    if process.state in {ProcessState.CLOSED, ProcessState.ARCHIVED}:
        raise PermissionDenied("No se permiten operaciones financieras en procesos cerrados o archivados.")


def _assert_user_has_permissions(user, permissions, message):
    if not user.has_perms(permissions):
        raise PermissionDenied(message)


def _build_section_payload(process, bidder, section, query_params=None):
    query_params = query_params or {}
    base_context = {
        "process": process,
        "bidder": bidder,
        "section": section,
        "section_label": SECTION_LABELS[section],
    }

    if section == "documents":
        document_type = query_params.get("document_type", "").strip()
        documents_queryset = (
            Document.objects.filter(process=process, bidder=bidder)
            .select_related("process", "bidder")
            .prefetch_related(
                Prefetch(
                    "versions",
                    queryset=DocumentVersion.objects.order_by("-version_no", "-created_at"),
                )
            )
            .order_by("document_type", "name")
        )
        document_type_choices = list(
            documents_queryset.order_by("document_type")
            .values_list("document_type", flat=True)
            .distinct()
        )
        if document_type:
            documents_queryset = documents_queryset.filter(document_type=document_type)
        return "review/partials/_documents.html", {
            **base_context,
            "documents": documents_queryset,
            "document_type_choices": document_type_choices,
            "current_document_type": document_type,
        }

    if section == "rup":
        rup_records = (
            RUPRecord.objects.filter(process=process, bidder=bidder)
            .select_related("source_document")
            .prefetch_related(
                Prefetch(
                    "field_values",
                    queryset=RUPFieldValue.objects.select_related("schema", "document_page_ref").order_by(
                        "schema__sort_order",
                        "-version_no",
                    ),
                ),
                Prefetch(
                    "segments",
                    queryset=RUPSegmentEntry.objects.select_related("document_page_ref").order_by(
                        "segment_code",
                        "-version_no",
                    ),
                ),
                Prefetch(
                    "codes",
                    queryset=RUPCodeEntry.objects.select_related("document_page_ref").order_by(
                        "code_type",
                        "code_value",
                        "-version_no",
                    ),
                ),
            )
            .order_by("-record_date", "-version_no", "-created_at")
        )
        return "review/partials/_rup.html", {**base_context, "rup_records": rup_records}

    if section == "experience":
        experience_records = (
            ExperienceRecord.objects.filter(process=process, bidder=bidder)
            .select_related("bidder_member", "source_document")
            .prefetch_related(
                Prefetch(
                    "metrics",
                    queryset=ExperienceMetric.objects.select_related("document_page_ref").order_by(
                        "metric_code",
                        "-version_no",
                    ),
                )
            )
            .order_by("-created_at", "-version_no")
        )
        return "review/partials/_experience.html", {**base_context, "experience_records": experience_records}

    if section == "validations":
        validation_status = query_params.get("validation_status")
        validations = (
            ValidationDecisionRecord.objects.filter(process=process, bidder=bidder)
            .select_related(
                "rule_definition",
                "rule_version",
                "normative_snapshot",
                "human_confirmed_by",
                "bidder_member",
                "document",
                "rup_record",
                "rup_field_value__schema",
                "experience_record",
                "experience_metric",
                "financial_input_version",
                "external_check",
            )
            .prefetch_related(
                Prefetch(
                    "evidence_links",
                    queryset=ValidationEvidenceLink.objects.select_related(
                        "document_version",
                        "document_page_ref",
                    ).order_by("-created_at"),
                )
            )
            .order_by("-created_at", "-version_no")
        )
        if validation_status in ValidationStatus.values:
            validations = validations.filter(status=validation_status)
        return "review/partials/_validations.html", {
            **base_context,
            "validations": validations,
            "current_validation_status": validation_status if validation_status in ValidationStatus.values else "",
            "validation_status_choices": ValidationStatus.choices,
        }

    if section == "causals":
        causals = (
            RejectionCauseAssessment.objects.filter(process=process, bidder=bidder)
            .select_related("cause_definition", "triggering_decision_record", "reviewed_by")
            .order_by("-created_at", "-version_no")
        )
        return "review/partials/_causals.html", {**base_context, "causals": causals}

    consolidated_results = (
        BidderConsolidatedResult.objects.filter(process=process, bidder=bidder)
        .select_related("matrix_snapshot")
        .order_by("-created_at", "-version_no")
    )
    matrix_snapshots = (
        ConsolidatedMatrixSnapshot.objects.filter(process=process)
        .select_related("normative_snapshot", "generated_by")
        .order_by("-generated_at", "-version_no")
    )
    financial_assessments = (
        FinancialAssessment.objects.filter(process=process, bidder=bidder)
        .select_related("financial_input_version", "reviewed_by")
        .order_by("-created_at", "-version_no")
    )
    financial_inputs = (
        FinancialInputVersion.objects.filter(process=process, bidder=bidder)
        .select_related("source_document")
        .order_by("-source_date", "-version_no", "-created_at")
    )
    return "review/partials/_consolidation.html", {
        **base_context,
        "consolidated_results": consolidated_results,
        "matrix_snapshots": matrix_snapshots,
        "financial_assessments": financial_assessments,
        "financial_inputs": financial_inputs,
    }


@login_required
@require_GET
def process_list(request):
    processes = list(
        ContractProcess.objects.select_related(
            "normative_binding__document_type_version__family",
            "normative_binding__current_snapshot",
        )
        .annotate(bidder_count=Count("bidders", distinct=True))
        .order_by("-created_at")
    )
    for process in processes:
        process.normative_binding_safe = getattr(process, "normative_binding", None)
    return render(
        request,
        "review/process_list.html",
        {
            "processes": processes,
            "breadcrumbs": [_crumb("Procesos")],
        },
    )


@login_required
@require_GET
def process_detail(request, process_id):
    process = _get_process(process_id)
    bidders = (
        process.bidders.all()
        .annotate(
            document_count=Count("documents", distinct=True),
            validation_count=Count("validation_decisions", distinct=True),
            causal_count=Count("rejection_cause_assessments", distinct=True),
        )
        .order_by("name")
    )
    recent_audit_events = (
        AuditEvent.objects.filter(process=process).select_related("bidder", "created_by").order_by("-created_at")[:10]
    )
    return render(
        request,
        "review/process_detail.html",
        {
            "process": process,
            "bidders": bidders,
            "recent_audit_events": recent_audit_events,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code),
            ],
        },
    )


@login_required
@require_GET
def process_bidder_list(request, process_id):
    process = _get_process(process_id)
    bidders = (
        Bidder.objects.filter(process=process)
        .annotate(
            document_count=Count("documents", distinct=True),
            validation_count=Count("validation_decisions", distinct=True),
            causal_count=Count("rejection_cause_assessments", distinct=True),
            member_count=Count("members", distinct=True),
        )
        .order_by("name")
    )
    return render(
        request,
        "review/bidder_list.html",
        {
            "process": process,
            "bidders": bidders,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code, "review:process_detail", process_id=process.id),
                _crumb("Proponentes"),
            ],
        },
    )


@login_required
@require_GET
def bidder_dossier(request, process_id, bidder_id):
    process = _get_process(process_id)
    bidder = _get_bidder(process_id, bidder_id)
    active_section = request.GET.get("section", "documents")
    if active_section not in SECTION_LABELS:
        active_section = "documents"
    template_name, section_context = _build_section_payload(process, bidder, active_section, request.GET)
    section_html = render_to_string(template_name, section_context, request=request)
    recent_audit_events = (
        AuditEvent.objects.filter(process=process, bidder=bidder).select_related("created_by").order_by("-created_at")[:8]
    )
    return render(
        request,
        "review/bidder_dossier.html",
        {
            "process": process,
            "bidder": bidder,
            "active_section": active_section,
            "section_labels": SECTION_LABELS,
            "section_html": section_html,
            "recent_audit_events": recent_audit_events,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code, "review:process_detail", process_id=process.id),
                _crumb("Proponentes", "review:process_bidder_list", process_id=process.id),
                _crumb(bidder.name),
            ],
        },
    )


@login_required
@require_GET
def bidder_dossier_section(request, process_id, bidder_id, section):
    process = _get_process(process_id)
    bidder = _get_bidder(process_id, bidder_id)
    if section not in SECTION_LABELS:
        raise Http404("Seccion no soportada.")
    template_name, context = _build_section_payload(process, bidder, section, request.GET)
    return render(request, template_name, context)


@login_required
@require_GET
def finance_overview(request, process_id, bidder_id):
    _assert_user_has_permissions(
        request.user,
        FINANCE_READ_PERMISSIONS,
        "No tiene permisos para consultar el contexto financiero.",
    )
    process = _get_process(process_id)
    bidder = _get_bidder(process_id, bidder_id)
    current_assessment = (
        FinancialAssessment.objects.filter(process=process, bidder=bidder, used_in_consolidation=True)
        .select_related("financial_input_version", "reviewed_by")
        .order_by("-created_at", "-version_no")
        .first()
    )
    latest_input = (
        FinancialInputVersion.objects.filter(process=process, bidder=bidder)
        .select_related("source_document__document")
        .order_by("-source_date", "-version_no", "-created_at")
        .first()
    )
    financial_inputs = (
        FinancialInputVersion.objects.filter(process=process, bidder=bidder)
        .select_related("source_document__document")
        .order_by("-source_date", "-version_no", "-created_at")
    )
    financial_assessments = (
        FinancialAssessment.objects.filter(process=process, bidder=bidder)
        .select_related("financial_input_version", "reviewed_by")
        .order_by("-created_at", "-version_no")
    )
    return render(
        request,
        "review/finance_overview.html",
        {
            "process": process,
            "bidder": bidder,
            "current_assessment": current_assessment,
            "latest_input": latest_input,
            "financial_inputs": financial_inputs,
            "financial_assessments": financial_assessments,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code, "review:process_detail", process_id=process.id),
                _crumb("Proponentes", "review:process_bidder_list", process_id=process.id),
                _crumb(bidder.name, "review:bidder_dossier", process_id=process.id, bidder_id=bidder.id),
                _crumb("Financiero"),
            ],
        },
    )


@login_required
@require_GET
def financial_input_detail(request, process_id, bidder_id, input_id):
    _assert_user_has_permissions(
        request.user,
        FINANCE_READ_PERMISSIONS,
        "No tiene permisos para consultar el detalle financiero.",
    )
    process = _get_process(process_id)
    bidder = _get_bidder(process_id, bidder_id)
    financial_input = _get_financial_input(process.id, bidder.id, input_id)
    related_assessments = (
        FinancialAssessment.objects.filter(process=process, bidder=bidder, financial_input_version=financial_input)
        .select_related("reviewed_by")
        .order_by("-created_at", "-version_no")
    )
    return render(
        request,
        "review/finance_input_detail.html",
        {
            "process": process,
            "bidder": bidder,
            "financial_input": financial_input,
            "related_assessments": related_assessments,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code, "review:process_detail", process_id=process.id),
                _crumb("Proponentes", "review:process_bidder_list", process_id=process.id),
                _crumb(bidder.name, "review:bidder_dossier", process_id=process.id, bidder_id=bidder.id),
                _crumb("Financiero", "review:finance_overview", process_id=process.id, bidder_id=bidder.id),
                _crumb(f"Insumo v{financial_input.version_no}"),
            ],
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def financial_input_create(request, process_id, bidder_id):
    _assert_user_has_permissions(
        request.user,
        FINANCE_INPUT_CREATE_PERMISSIONS,
        "No tiene permisos para registrar insumos financieros.",
    )
    process = _get_process(process_id)
    bidder = _get_bidder(process_id, bidder_id)
    _assert_finance_write_allowed(process)
    latest_input = (
        FinancialInputVersion.objects.filter(process=process, bidder=bidder)
        .select_related("source_document__document")
        .order_by("-version_no", "-created_at")
        .first()
    )
    if request.method == "POST":
        form = FinancialInputVersionCreateForm(request.POST, process=process, bidder=bidder)
        if form.is_valid():
            next_version = 1 if latest_input is None else latest_input.version_no + 1
            financial_input = form.save(commit=False)
            financial_input.process = process
            financial_input.bidder = bidder
            financial_input.status = FinancialInputStatus.SUBMITTED
            financial_input.version_no = next_version
            financial_input.supersedes = latest_input
            financial_input.created_by = request.user
            financial_input.full_clean()
            financial_input.save()
            messages.success(request, "Insumo financiero registrado como nueva versión.")
            return redirect(
                "review:financial_input_detail",
                process_id=process.id,
                bidder_id=bidder.id,
                input_id=financial_input.id,
            )
    else:
        form = FinancialInputVersionCreateForm(process=process, bidder=bidder)

    return render(
        request,
        "review/finance_input_form.html",
        {
            "process": process,
            "bidder": bidder,
            "form": form,
            "latest_input": latest_input,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code, "review:process_detail", process_id=process.id),
                _crumb("Proponentes", "review:process_bidder_list", process_id=process.id),
                _crumb(bidder.name, "review:bidder_dossier", process_id=process.id, bidder_id=bidder.id),
                _crumb("Financiero", "review:finance_overview", process_id=process.id, bidder_id=bidder.id),
                _crumb("Nuevo input"),
            ],
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def financial_assessment_create(request, process_id, bidder_id, input_id):
    _assert_user_has_permissions(
        request.user,
        FINANCE_ASSESSMENT_CREATE_PERMISSIONS,
        "No tiene permisos para confirmar evaluaciones financieras.",
    )
    process = _get_process(process_id)
    bidder = _get_bidder(process_id, bidder_id)
    _assert_finance_write_allowed(process)
    financial_input = _get_financial_input(process.id, bidder.id, input_id)

    if request.method == "POST":
        form = FinancialAssessmentCreateForm(
            request.POST,
            process=process,
            bidder=bidder,
            financial_input=financial_input,
        )
        if form.is_valid():
            with transaction.atomic():
                locked_assessments = FinancialAssessment.objects.select_for_update().filter(
                    process=process,
                    bidder=bidder,
                )
                latest_assessment = locked_assessments.order_by("-version_no", "-created_at").first()
                current_assessment = locked_assessments.filter(used_in_consolidation=True).order_by(
                    "-version_no",
                    "-created_at",
                ).first()
                next_version = 1 if latest_assessment is None else latest_assessment.version_no + 1
                new_assessment = form.save(commit=False)
                new_assessment.version_no = next_version
                new_assessment.supersedes = current_assessment
                new_assessment.created_by = request.user
                new_assessment.reviewed_by = request.user
                new_assessment.reviewed_at = timezone.now()
                if current_assessment:
                    current_assessment.used_in_consolidation = False
                    current_assessment.status = FinancialAssessmentStatus.OBSOLETE
                    current_assessment.save(update_fields=["used_in_consolidation", "status"])

                new_assessment.full_clean()
                new_assessment.save()

            messages.success(request, "Evaluación financiera confirmada correctamente.")
            return redirect(
                "review:finance_overview",
                process_id=process.id,
                bidder_id=bidder.id,
            )
    else:
        form = FinancialAssessmentCreateForm(
            process=process,
            bidder=bidder,
            financial_input=financial_input,
        )

    current_assessment = (
        FinancialAssessment.objects.filter(process=process, bidder=bidder, used_in_consolidation=True)
        .select_related("financial_input_version", "reviewed_by")
        .order_by("-created_at", "-version_no")
        .first()
    )
    return render(
        request,
        "review/finance_assessment_form.html",
        {
            "process": process,
            "bidder": bidder,
            "financial_input": financial_input,
            "current_assessment": current_assessment,
            "form": form,
            "breadcrumbs": [
                _crumb("Procesos", "review:process_list"),
                _crumb(process.code, "review:process_detail", process_id=process.id),
                _crumb("Proponentes", "review:process_bidder_list", process_id=process.id),
                _crumb(bidder.name, "review:bidder_dossier", process_id=process.id, bidder_id=bidder.id),
                _crumb("Financiero", "review:finance_overview", process_id=process.id, bidder_id=bidder.id),
                _crumb(f"Insumo v{financial_input.version_no}", "review:financial_input_detail", process_id=process.id, bidder_id=bidder.id, input_id=financial_input.id),
                _crumb("Nuevo assessment"),
            ],
        },
    )
