from django import forms

from core.models import Project

INPUT_CLASS = (
    "w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 "
    "text-slate-100 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
