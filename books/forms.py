from django import forms
from .models import Profile
from .models import Comment

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['address', 'city', 'postal_code', 'phone_number']




class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
