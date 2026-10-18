from django import forms

from .models import LiveChatQuestion


class LiveChatQuestionForm(forms.ModelForm):
    # A simple honeypot to discourage basic bot submissions.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = LiveChatQuestion
        fields = ('name', 'body')
        labels = {'body': 'Your question'}
        widgets = {
            'name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'body': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_website(self):
        if self.cleaned_data['website']:
            raise forms.ValidationError('Invalid submission.')
        return ''
