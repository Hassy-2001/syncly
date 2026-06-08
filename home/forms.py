from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm
from .models import *

MAX_IMAGE_UPLOAD_SIZE = 3 * 1024 * 1024
MAX_ATTACHMENT_UPLOAD_SIZE = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_ATTACHMENT_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/webp',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def validate_uploaded_file(uploaded_file, allowed_types, max_size, label):
    if not uploaded_file:
        return
    if (
        getattr(settings, 'MEDIA_UPLOADS_REQUIRE_CLOUDINARY', False)
        and not getattr(settings, 'MEDIA_UPLOADS_CONFIGURED', False)
    ):
        raise ValidationError(
            f'{label} uploads are not configured yet. Add Cloudinary environment variables in Vercel and redeploy.'
        )
    content_type = getattr(uploaded_file, 'content_type', '')
    if content_type not in allowed_types:
        raise ValidationError(f'{label} type is not allowed.')
    if uploaded_file.size > max_size:
        size_mb = max_size // (1024 * 1024)
        raise ValidationError(f'{label} must be {size_mb}MB or smaller.')


class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        exclude = ['host', 'participants', 'invite_code']
        labels = {
            'is_private': 'Private room',
            'cover': 'Room cover image',
        }

    def clean_cover(self):
        cover = self.cleaned_data.get('cover')
        validate_uploaded_file(cover, ALLOWED_IMAGE_TYPES, MAX_IMAGE_UPLOAD_SIZE, 'Room cover')
        return cover

class MessageForm(ModelForm):
    class Meta:
        model = Message
        fields = ['body', 'attachment']
        widgets = {
            'body': forms.TextInput(attrs={'placeholder': 'Write a message...'}),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        validate_uploaded_file(attachment, ALLOWED_ATTACHMENT_TYPES, MAX_ATTACHMENT_UPLOAD_SIZE, 'Attachment')
        return attachment

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email))
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.username = user.email
        if commit:
            user.save()
        return user

class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['photo', 'bio', 'location', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={
                'placeholder': 'Write a short bio',
                'rows': 4,
            }),
            'location': forms.TextInput(attrs={'placeholder': 'City or country'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        validate_uploaded_file(photo, ALLOWED_IMAGE_TYPES, MAX_IMAGE_UPLOAD_SIZE, 'Profile photo')
        return photo

class StyledPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Current password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter current password',
            'autocomplete': 'current-password',
        })
    )
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password',
        })
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })
    )

class EmailUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        label='First name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        label='Last name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name',
        })
    )
    email = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.username = user.email
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        if commit:
            user.save()
        return user

class ForgotPasswordRequestForm(forms.Form):
    identifier = forms.CharField(
        label='Email address',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
        })
    )
