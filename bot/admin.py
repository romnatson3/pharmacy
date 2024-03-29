from django.contrib import admin
from bot.models import Pharmacy, Medication, PharmacyStock, District, Address, \
    Phone, Chain, ProductOfTheDay, Form, Unit
from django.utils.translation import gettext_lazy as _
from bot.forms import MedicationForm, PharmacyStockForm, PharmacyForm
from django_admin_inline_paginator.admin import TabularInlinePaginated
from django.db.models import Q
from django.utils.html import mark_safe


admin.site.site_header = _('Medication Bot')
admin.site.site_title = _('Medication Bot')
admin.site.index_title = _('Medication Bot')


class BaseAdmin(admin.ModelAdmin):
    def get_search_results(self, request, queryset, search_term):
        if search_term:
            where = Q(
                Q(pharmacy__chain__name__icontains=search_term) | 
                Q(pharmacy__address__name__icontains=search_term) | 
                Q(medication__name__icontains=search_term)
            )
            queryset = queryset.filter(where).all()
        return queryset, False


class ChainAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_display_links = ('name',)


class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_display_links = ('name',)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_display_links = ('name',)


class FormAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_display_links = ('name',)


class UnitAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_display_links = ('name',)


class PhoneAdmin(admin.ModelAdmin):
    list_display = ('number',)
    search_fields = ('number',)
    list_display_links = ('number',)


# class PharmacyStockInline(admin.StackedInline):
class PharmacyStockInline(TabularInlinePaginated):
    model = PharmacyStock
    per_page = 20
    extra = 0
    form = PharmacyStockForm
    autocomplete_fields = ('medication',)
    fieldsets = (
        (None, {
            'fields': (('medication', 'price'),)
        }),
    )


class PharmacyAdmin(admin.ModelAdmin):
    form = PharmacyForm
    list_display = ('id', 'chain', 'address', 'phones', 'district', 'rating')
    search_fields = ('id',)
    list_display_links = ('chain', 'address')
    list_filter = ('district', 'chain')
    inlines = [PharmacyStockInline]
    autocomplete_fields = ('address', 'phone', 'chain')
    actions = ('copy_action',)

    def phones(self, obj):
        if obj.phone.exists():
            text = ', '.join([i.number for i in obj.phone.all()])
            return text
        else:
            return '-'
    phones.short_description = _('Phone numbers')

    def get_search_results(self, request, queryset, search_term):
        if search_term:
            where = Q(
                Q(chain__name__icontains=search_term) | 
                Q(address__name__icontains=search_term) 
            )
            queryset = queryset.filter(where).all()
        return queryset, False

    def save_model(self, request, obj, form, change):
        if obj.rating:
            pharmacies = Pharmacy.objects.filter(rating=obj.rating).all()
            for i in pharmacies:
                i.rating = 0
                i.save()
        super().save_model(request, obj, form, change)

    def copy_action(self, request, queryset):
        for obj in queryset:
            previous_phone = obj.phone.all()
            obj.id = None
            obj.rating = 0
            obj.address_id = None
            obj.save()
            obj.phone.set(previous_phone)
        self.message_user(request, _('Selected records were copied successfully'))
    copy_action.short_description = _('Copy chosen records')

    class Media:
        css = {
            'all': ('bot/css/pharmacystock.css',)
        }


class MedicationAdmin(admin.ModelAdmin):
    form = MedicationForm
    list_display = ('id', 'name', 'dosage', 'units', 'quantity', 'form')
    search_fields = ('name', 'dosage')
    list_display_links = ('name',)
    fields = ('name', ('dosage', 'units'), ('quantity', 'form'))

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form

    class Media:
        js = ('bot/js/medication.js',)


class PharmacyStockAdmin(BaseAdmin):
    form = PharmacyStockForm
    autocomplete_fields = ('pharmacy', 'medication')
    list_display = ('id', 'pharmacy', 'medication', 'price')
    search_fields = ('id',)
    list_display_links = ('pharmacy', 'medication')
    actions = ('copy_action',)
    per_page = 100

    def copy_action(self, request, queryset):
        for obj in queryset:
            obj.id = None
            obj.pharmacy_id = None
            obj.save()
        self.message_user(request, _('Selected records were copied successfully'))
    copy_action.short_description = _('Copy chosen records')


class ProductOfTheDayAdmin(BaseAdmin):
    autocomplete_fields = ('pharmacy', 'medication')
    list_display = ('id', 'pharmacy', 'medication', 'price')
    search_fields = ('id',)
    list_display_links = ('pharmacy', 'medication')
    per_page = 100


admin.site.register(Chain, ChainAdmin)
admin.site.register(District, DistrictAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Phone, PhoneAdmin)
admin.site.register(Pharmacy, PharmacyAdmin)
admin.site.register(Medication, MedicationAdmin)
admin.site.register(PharmacyStock, PharmacyStockAdmin)
admin.site.register(ProductOfTheDay, ProductOfTheDayAdmin)
admin.site.register(Form, FormAdmin)
admin.site.register(Unit, UnitAdmin)
