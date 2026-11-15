from django import forms

from .models import Enquiry

INPUT = "w-full rounded-sm border border-line bg-white px-4 py-2.5"


class EnquiryForm(forms.ModelForm):
    # honeypot: humans never see or fill this
    website = forms.CharField(required=False, widget=forms.HiddenInput, label="")

    class Meta:
        model = Enquiry
        fields = ("name", "email", "phone", "category", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
