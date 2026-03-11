import re
from django import forms
from django.forms import ModelForm, ValidationError, CharField

from apps.models import User


def normalize_phone_number(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("998"):
        digits = digits[3:]
    if len(digits) != 9:
        raise ValidationError("Telefon raqami noto'g'ri. Masalan: +998901234567")
    return digits


class RegisterModelForm(ModelForm):
    phone_number = CharField(
        max_length=20,
        error_messages={
            "required": "Telefon raqamni kiriting.",
        },
    )
    password = CharField(
        max_length=128,
        min_length=6,
        widget=forms.PasswordInput,
        error_messages={
            "required": "Parolni kiriting.",
            "min_length": "Parol kamida 6 ta belgidan iborat bo'lishi kerak.",
        },
    )
    confirm_password = CharField(
        max_length=128,
        min_length=6,
        widget=forms.PasswordInput,
        error_messages={
            "required": "Parolni qayta kiriting.",
            "min_length": "Parol kamida 6 ta belgidan iborat bo'lishi kerak.",
        },
    )
    class Meta:
        model = User
        fields = ("phone_number",)

    def clean_phone_number(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("phone_number"))
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("Bu telefon raqami ro'yxatdan o'tgan.")
        return phone_number

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm_password = cleaned.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", ValidationError("Parollar mos emas"))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        error_messages={
            "required": "Telefon raqamni kiriting.",
        },
    )
    password = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput,
        error_messages={
            "required": "Parolni kiriting.",
        },
    )

    def clean_phone_number(self):
        return normalize_phone_number(self.cleaned_data.get("phone_number"))


class OtpForm(forms.Form):
    otp_code = forms.RegexField(
        regex=r"^\d{6}$",
        max_length=6,
        min_length=6,
        error_messages={
            "required": "OTP kodini kiriting.",
            "invalid": "OTP kodi 6 xonali raqam bo'lishi kerak.",
            "min_length": "OTP kodi 6 xonali bo'lishi kerak.",
        },
    )


class ProfileForm(forms.ModelForm):
    phone_number = CharField(
        max_length=20,
        error_messages={
            "required": "Telefon raqamni kiriting.",
        },
    )
    new_password = CharField(
        max_length=128,
        min_length=6,
        required=False,
        widget=forms.PasswordInput,
        error_messages={
            "min_length": "Parol kamida 6 ta belgidan iborat bo'lishi kerak.",
        },
    )
    confirm_password = CharField(
        max_length=128,
        min_length=6,
        required=False,
        widget=forms.PasswordInput,
        error_messages={
            "min_length": "Parol kamida 6 ta belgidan iborat bo'lishi kerak.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.password_changed = False

    def clean_phone_number(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("phone_number"))
        qs = User.objects.filter(phone_number=phone_number)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Bu telefon raqami band.")
        return phone_number

    def clean_first_name(self):
        return (self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self):
        return (self.cleaned_data.get("last_name") or "").strip()

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm_password = cleaned.get("confirm_password")
        if new_password or confirm_password:
            if not new_password:
                self.add_error("new_password", ValidationError("Parolni kiriting."))
            if not confirm_password:
                self.add_error("confirm_password", ValidationError("Parolni qayta kiriting."))
            elif new_password != confirm_password:
                self.add_error("confirm_password", ValidationError("Parollar mos emas"))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
            self.password_changed = True
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number")
