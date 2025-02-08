from django import forms
from .models import TextFile


from django import forms

class TextFileUpdateForm(forms.ModelForm):
    class Meta:
        model = TextFile
        fields = ['voice_id', 'api_key']
