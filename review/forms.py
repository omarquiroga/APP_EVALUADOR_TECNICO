from django import forms

from common.choices import FinancialAssessmentStatus
from documents.models import DocumentVersion
from finance.models import FinancialAssessment, FinancialInputVersion


class FinancialInputVersionCreateForm(forms.ModelForm):
    class Meta:
        model = FinancialInputVersion
        fields = [
            "source_label",
            "source_document",
            "source_date",
            "assets_value",
            "liabilities_value",
            "operating_income_value",
            "financial_observation",
        ]
        widgets = {
            "source_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "source_label": forms.TextInput(attrs={"class": "form-control"}),
            "source_document": forms.Select(attrs={"class": "form-select"}),
            "assets_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "liabilities_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "operating_income_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "financial_observation": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, process=None, bidder=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = process
        self.bidder = bidder
        self.fields["source_document"].required = False
        self.fields["source_document"].queryset = DocumentVersion.objects.none()
        if process and bidder:
            self.fields["source_document"].queryset = DocumentVersion.objects.select_related("document").filter(
                document__process=process,
                document__bidder=bidder,
            ).order_by("document__name", "-version_no")

    def clean_source_document(self):
        source_document = self.cleaned_data.get("source_document")
        if source_document and self.process and self.bidder:
            if source_document.document.process_id != self.process.id:
                raise forms.ValidationError("El documento soporte pertenece a otro proceso.")
            if source_document.document.bidder_id != self.bidder.id:
                raise forms.ValidationError("El documento soporte pertenece a otro proponente.")
        return source_document

    def clean_assets_value(self):
        value = self.cleaned_data["assets_value"]
        if value < 0:
            raise forms.ValidationError("Los activos no pueden ser negativos.")
        return value

    def clean_liabilities_value(self):
        value = self.cleaned_data["liabilities_value"]
        if value < 0:
            raise forms.ValidationError("Los pasivos no pueden ser negativos.")
        return value

    def clean_operating_income_value(self):
        value = self.cleaned_data["operating_income_value"]
        if value < 0:
            raise forms.ValidationError("El ingreso operacional no puede ser negativo.")
        return value


class FinancialAssessmentCreateForm(forms.ModelForm):
    class Meta:
        model = FinancialAssessment
        fields = ["result_code", "assessment_note"]
        widgets = {
            "result_code": forms.Select(attrs={"class": "form-select"}),
            "assessment_note": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, process=None, bidder=None, financial_input=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = process
        self.bidder = bidder
        self.financial_input = financial_input

    def clean(self):
        cleaned_data = super().clean()
        if self.financial_input is None:
            raise forms.ValidationError("No se encontro el input financiero asociado.")
        if self.process and self.financial_input.process_id != self.process.id:
            raise forms.ValidationError("El input financiero pertenece a otro proceso.")
        if self.bidder and self.financial_input.bidder_id != self.bidder.id:
            raise forms.ValidationError("El input financiero pertenece a otro proponente.")
        if self.financial_input.status != "submitted":
            raise forms.ValidationError("Solo se pueden confirmar assessments sobre inputs radicados.")
        self.instance.process = self.process
        self.instance.bidder = self.bidder
        self.instance.financial_input_version = self.financial_input
        self.instance.status = FinancialAssessmentStatus.CONFIRMED
        self.instance.used_in_consolidation = True
        self.instance.human_required = True
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
