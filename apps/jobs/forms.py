from pathlib import Path

from django import forms

from .models import Application

# First bytes of each allowed format. Extension alone is not trustworthy.
SIGNATURES = {
    "pdf": b"%PDF",
    "doc": b"\xd0\xcf\x11\xe0",
    "docx": b"PK\x03\x04",
}


JOB_INPUT_CLASS = "w-full rounded-xl border border-[#dde9ff] bg-[#f8f9ff] px-4 py-2.5 text-sm text-[#0d1c2f] focus:border-[#006398] focus:outline-hidden"


class ApplicationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Jane", "class": JOB_INPUT_CLASS}
        ),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Doe", "class": JOB_INPUT_CLASS}
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"placeholder": "jane.doe@example.com", "class": JOB_INPUT_CLASS}
        ),
    )
    phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "+1 (555) 000-0000", "class": JOB_INPUT_CLASS}
        ),
    )
    work_authorization = forms.ChoiceField(
        choices=[
            ("us_citizen", "U.S. Citizen / Permanent Resident (Green Card)"),
            ("ead", "EAD / Employment Authorization"),
            ("h1b", "H-1B / Visa Transfer Eligible"),
            ("other", "Other / Requires Sponsorship"),
        ],
        required=False,
        widget=forms.Select(
            attrs={"class": JOB_INPUT_CLASS}
        ),
    )

    class Meta:
        model = Application
        fields = ("resume", "message")
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Briefly describe your enterprise tech experience, key specializations, and earliest start date...",
                    "class": JOB_INPUT_CLASS,
                }
            )
        }

    def __init__(self, *args, is_authenticated=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_authenticated = is_authenticated
        self.fields["message"].required = True
        if not self.is_authenticated:
            self.fields["first_name"].required = True
            self.fields["last_name"].required = True
            self.fields["email"].required = True

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if not resume:
            raise forms.ValidationError("Please upload a resume file.")
        if resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Resume must be 5 MB or smaller.")
        extension = Path(resume.name).suffix.lower().lstrip(".")
        expected_sig = SIGNATURES.get(extension)
        head = resume.read(8)
        resume.seek(0)
        if not expected_sig or not head.startswith(expected_sig):
            raise forms.ValidationError("Upload a valid PDF or Word document (.pdf, .doc, .docx).")
        return resume
