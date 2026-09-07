from django import forms
from django.utils import timezone

from .storage import get_store

CODE_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class LinkForm(forms.Form):
    target_url = forms.URLField(max_length=2000, label="Destination URL")
    code = forms.RegexField(
        regex=CODE_PATTERN,
        required=False,
        max_length=64,
        label="Custom slug",
        help_text="Letters, digits, hyphen and underscore. Leave blank for a random one.",
        error_messages={"invalid": "Use only letters, digits, hyphens and underscores."},
    )
    expires_at = forms.DateTimeField(
        required=False,
        label="Expires at",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )

    def __init__(self, *args, tenant_id: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id

    def clean_code(self) -> str:
        code = self.cleaned_data["code"]
        if code and get_store().get_link(self.tenant_id, code):
            raise forms.ValidationError("That slug is already used in this workspace.")
        return code

    def clean_expires_at(self):
        expires_at = self.cleaned_data["expires_at"]
        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError("Expiry must be in the future.")
        return expires_at
