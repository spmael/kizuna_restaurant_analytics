import os

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import DataUpload


class DataUploadForm(forms.ModelForm):
    """Form for uploading data files"""

    class Meta:
        model = DataUpload
        fields = ["file", "file_type"]
        widgets = {
            "file": forms.FileInput(
                attrs={"accept": ".csv, .xlsx, .xls", "class": "form-control-file"}
            ),
            "file_type": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML(
                '<div class="alert alert-info">'
                + str(_("Upload Excel (.xlsx) or CSV files. Maximum file size: 10MB"))
                + "</div>"
            ),
            Row(
                Column("file_type", css_class="form-group col-md-4 mb-3"),
                Column("file", css_class="form-group col-md-8 mb-3"),
            ),
            HTML('<div id="file-info" class="mb-3" style="display:none;"></div>'),
            Submit("submit", _("Upload File"), css_class="btn btn-primary"),
        )

    def clean_file(self):
        file = self.cleaned_data.get("file")

        if file:
            # check file size
            if file.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError(_("File size exceeds 10MB limit."))

            # check file extension
            ext = os.path.splitext(file.name)[1].lower()
            allowed_extensions = [".xlsx", ".xls", ".csv"]
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    _("Please upload a valid Excel or CSV file.")
                )

        return file

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set additional fields
        if instance.file:
            instance.original_file_name = instance.file.name
            instance.file_size = instance.file.size

        if commit:
            instance.save()

        return instance


class DataFilterForm(forms.Form):
    """Form for filtering data uploads"""

    STATUS_CHOICES = [("", _("All Statuses"))] + DataUpload.STATUS_CHOICES
    FILE_TYPE_CHOICES = [("", _("All File Types"))] + DataUpload.FILE_TYPE_CHOICES

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label=_("Status"),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    file_type = forms.ChoiceField(
        choices=FILE_TYPE_CHOICES,
        required=False,
        label=_("File Type"),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    date_from = forms.DateField(
        required=False,
        label=_("Date From"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    date_to = forms.DateField(
        required=False,
        label=_("Date To"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Row(
                Column("status", css_class="form-group col-md-3"),
                Column("file_type", css_class="form-group col-md-3"),
                Column("date_from", css_class="form-group col-md-3"),
                Column("date_to", css_class="form-group col-md-3"),
            ),
            Submit("submit", _("Filter"), css_class="btn btn-secondary"),
        )
