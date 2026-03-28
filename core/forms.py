from django import forms

from core.models import Project

INPUT_CLASS = (
    "input-themed rounded-md px-3 py-2 "
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "domain"]
        labels = {
            "name": "Project name",
            "domain": "Domain (optional)",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "autofocus": True}),
            "domain": forms.TextInput(attrs={"class": INPUT_CLASS}),
        }
