from django import forms
from bot.models import Pharmacy, Medication, PharmacyStock
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class PharmacyStockForm(forms.ModelForm):
    pharmacy = forms.ModelChoiceField(
        label=_('Pharmacy'),
        queryset=Pharmacy.objects.all(),
        required=True,
        widget=AutocompleteSelect(
            PharmacyStock.pharmacy.field,
            admin.site,
            attrs={'style': 'width: 700px'}
        )
    )

    medication = forms.ModelChoiceField(
        label=_('Medication'),
        queryset=Medication.objects.all(),
        required=True,
        widget=AutocompleteSelect(
            PharmacyStock.medication.field,
            admin.site,
            attrs={'style': 'width: 700px'}
        )
    )

    class Meta:
        model = Pharmacy
        fields = '__all__'


class MedicationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('dosage') and not cleaned_data.get('units'):
            raise forms.ValidationError(_('Units are required if dosage is specified'))
        elif cleaned_data.get('units') and not cleaned_data.get('dosage'):
            raise forms.ValidationError(_('Dosage is required if units are specified'))
        if cleaned_data.get('quantity') and not cleaned_data.get('form'):
            raise forms.ValidationError(_('Form is required if quantity is specified'))
        elif cleaned_data.get('form') and not cleaned_data.get('quantity'):
            raise forms.ValidationError(_('Quantity is required if form is specified'))
        return cleaned_data

    name = forms.CharField(
        label=_('Name'),
        widget=forms.TextInput(attrs={'style': 'width: 700px'})
    )

    class Meta:
        model = Medication
        fields = '__all__'


class PharmacyForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=Pharmacy.RATING,
        widget=forms.Select(attrs={'style': 'width: 50px'}),
        required=False,
    )

    class Meta:
        model = Pharmacy
        fields = '__all__'
