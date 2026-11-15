from django import forms

from .models import Application


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
        return resume
