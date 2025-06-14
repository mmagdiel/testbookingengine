from datetime import datetime
from django import forms
from django.forms import ModelForm

from .models import Booking, Customer


class RoomSearchForm(ModelForm):
    class Meta:
        model = Booking
        fields = ['checkin', 'checkout', 'guests']
        labels = {
            "guests": "Huéspedes"
        }
        widgets = {
            'checkin': forms.DateInput(attrs={'type': 'date', 'min': datetime.today().strftime('%Y-%m-%d')}),
            'checkout': forms.DateInput(
                attrs={'type': 'date', 'max': datetime.today().replace(month=12, day=31).strftime('%Y-%m-%d')}),
            'guests': forms.DateInput(attrs={'type': 'number', 'min': 1, 'max': 4}),
        }


class CustomerForm(ModelForm):
    class Meta:
        model = Customer
        fields = "__all__"
        labels = {
            "name": "Nombre y apellido",
            "phone": "Teléfono"
        }


class BookingForm(ModelForm):
    class Meta:
        model = Booking
        fields = "__all__"
        labels = {
        }
        widgets = {
            'checkin': forms.HiddenInput(),
            'checkout': forms.HiddenInput(),
            'guests': forms.HiddenInput()
        }


class BookingFormExcluded(ModelForm):
    class Meta:
        model = Booking
        exclude = ["customer", "room", "code"]
        labels = {
        }
        widgets = {
            'checkin': forms.HiddenInput(),
            'checkout': forms.HiddenInput(),
            'guests': forms.HiddenInput(),
            'total': forms.HiddenInput(),
            'state': forms.HiddenInput(),
        }

class EditBookingDatesForm(ModelForm):
    class Meta:
        model = Booking
        fields = ['checkin', 'checkout']
        labels = {
            "checkin": "Fecha de entrada",
            "checkout": "Fecha de salida"
        }
        widgets = {
            'checkin': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'min': datetime.today().strftime('%Y-%m-%d')
            }),
            'checkout': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'min': datetime.today().strftime('%Y-%m-%d')
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        checkin = cleaned_data.get('checkin')
        checkout = cleaned_data.get('checkout')
        
        if checkin and checkout:
            # Validate that checkout is after checkin
            if checkout <= checkin:
                raise forms.ValidationError("La fecha de salida debe ser posterior a la fecha de entrada.")
            
            # Validate that checkin is not in the past
            if checkin < datetime.now().date():
                raise forms.ValidationError("La fecha de entrada no puede ser anterior a hoy.")
        
        return cleaned_data