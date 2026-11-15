from pathlib import Path

from django import forms

from .models import Application

# First bytes of each allowed format. Extension alone is not trustworthy.
SIGNATURES = {
    "pdf": b"%PDF",
    "doc": b"\xd0\xcf\x11\xe0",
    "docx": b"PK\x03\x04",
}


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("resume", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 4, "placeholder": "Your experience and why this role suits you"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["message"].required = True

    def clean_resume(self):
        resume = self.cleaned_data["resume"]
        if resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Resume must be 5 MB or smaller.")
        extension = Path(resume.name).suffix.lower().lstrip(".")
        head = resume.read(8)
        resume.seek(0)
        if not head.startswith(SIGNATURES.get(extension, b"")):
            raise forms.ValidationError("Upload a valid PDF or Word document.")
        return resume
