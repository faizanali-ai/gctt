from django import forms

from .models import Enquiry


class EnquiryForm(forms.ModelForm):
    # honeypot: humans never see or fill this
    website = forms.CharField(required=False, widget=forms.HiddenInput, label="")

    class Meta:
        model = Enquiry
        fields = ("name", "email", "phone", "company", "area", "how_heard", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}
        labels = {
            "company": "Company (optional)",
            "area": "Area of interest (optional)",
            "how_heard": "How did you hear about us? (optional)",
            "phone": "Contact number (optional)",
            "message": "Message",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.setdefault("autocomplete", "name")
        self.fields["email"].widget.attrs.setdefault("autocomplete", "email")
        self.fields["phone"].widget.attrs.setdefault("autocomplete", "tel")
        self.fields["company"].widget.attrs.setdefault("autocomplete", "organization")

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
