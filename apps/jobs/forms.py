from django import forms

from .models import Application, Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ("title", "location", "employment_type", "description", "requirements")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 8}),
            "requirements": forms.Textarea(attrs={"rows": 5}),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("resume", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def clean_resume(self):
        resume = self.cleaned_data["resume"]
        if resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Resume must be 5 MB or smaller.")
        return resume
