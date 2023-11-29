from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class BaseModel(models.Model):
    class Meta:
        abstract = True

    created = models.DateTimeField('Created', blank=False, default=timezone.now, editable=False)
    updated = models.DateTimeField('Updated', blank=False, auto_now=True)


class User(BaseModel):
    class Meta:
        verbose_name_plural = _('Users')
        verbose_name = _('User')

    id = models.BigIntegerField(_('ID'), primary_key=True)
    username = models.CharField(_('Username'), max_length=50, blank=True, null=True)
    first_name = models.CharField(_('First name'), max_length=50, blank=True, null=True)
    last_name = models.CharField(_('Last name'), max_length=50, blank=True, null=True)
    phone = models.CharField(_('Phone number'), max_length=15, blank=True, null=True)
    is_bot = models.BooleanField(_('Is bot'), default=False)
    is_deleted = models.BooleanField(_('Is deleted'), default=False)

    def __str__(self):
        return f'{self.id} {self.username}'


class District(BaseModel):
    class Meta:
        verbose_name_plural = _('Districts')
        verbose_name = _('District')

    name = models.CharField(_('Name'), max_length=50, unique=True)

    def __str__(self):
        return self.name


class Address(BaseModel):
    class Meta:
        verbose_name_plural = _('Addresses')
        verbose_name = _('Address')

    name = models.CharField(_('Address'), max_length=100, unique=True)

    def __str__(self):
        return self.name


class Chain(BaseModel):
    class Meta:
        verbose_name_plural = _('Chains')
        verbose_name = _('Chain')

    name = models.CharField(_('Name'), max_length=100, unique=True)

    def __str__(self):
        return self.name


class Phone(BaseModel):
    class Meta:
        verbose_name_plural = _('Phone numbers')
        verbose_name = _('Phone number')

    number = models.CharField(_('Number'), max_length=15, unique=True)

    def __str__(self):
        return self.number


class Pharmacy(BaseModel):
    class Meta:
        verbose_name_plural = _('Pharmacies')
        verbose_name = _('Pharmacy')
        unique_together = ('chain', 'address')

    RATING = [(i, i) if i else (0, '-----') for i in range(16)]

    chain = models.ForeignKey('Chain', on_delete=models.PROTECT, related_name='pharmacy', verbose_name=_('Chain'))
    address = models.ForeignKey('Address', on_delete=models.PROTECT, related_name='pharmacy', verbose_name=_('Address'))
    district = models.ForeignKey('District', on_delete=models.PROTECT, related_name='pharmacy', verbose_name=_('District'))
    phone = models.ManyToManyField('Phone', verbose_name=_('Phone number'), blank=False)
    rating = models.IntegerField(_('Rating'), choices=RATING, blank=True, default=0, validators=[MinValueValidator(0), MaxValueValidator(RATING[-1][0])])

    def __str__(self):
        return f'{self.chain} - {self.address}'


class Medication(BaseModel):
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['name', 'dosage'])
        ]
        verbose_name_plural = _('Medications')
        verbose_name = _('Medication')
        unique_together = ('name', 'dosage')

    FORM = (
        ('pills', _('pills')),
        ('ampoules', _('ampoules'))
    )

    UNITS = (
        ('ml', _('ml')),
        ('mg', _('mg'))
    )

    name = models.CharField(max_length=255, verbose_name=_('Name'), blank=False)
    dosage = models.IntegerField(verbose_name=_('Dosage'), blank=True, null=True)
    units = models.CharField(max_length=10, verbose_name=_('Units'), choices=UNITS, blank=True, null=True)
    quantity = models.IntegerField(verbose_name=_('Quantity in pack'), validators=[MinValueValidator(1), MaxValueValidator(10000)], blank=True, null=True)
    form = models.CharField(_('Form'), choices=FORM, blank=True, null=True)
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)

    def __str__(self):
        if self.dosage and self.units and self.quantity and self.form:
            return f'{self.name}, {self.dosage} {_(self.units)}, {self.quantity} {_(self.form)}'
        elif self.dosage and self.units and not self.quantity:
            return f'{self.name}, {self.dosage} {_(self.units)}'
        elif not self.dosage and self.quantity and self.form:
            return f'{self.name}, {self.quantity} {_(self.form)}'
        else:
            return f'{self.name}'


class PharmacyStock(BaseModel):
    class Meta:
        verbose_name_plural = _('Pharmacy stocks')
        verbose_name = _('Pharmacy stock')
        constraints = [
            models.UniqueConstraint(fields=['pharmacy', 'medication'], name='unique_pharmacy_medication')
        ]

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.PROTECT, related_name='stocks', verbose_name=_('Pharmacy'))
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT, related_name='stocks', verbose_name=_('Medication'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Price'), blank=False)

    def __str__(self):
        return str(self.id)


class ProductOfTheDay(BaseModel):
    class Meta:
        verbose_name_plural = _('Products of the day')
        verbose_name = _('Product of the day')
        unique_together = ('pharmacy', 'medication')

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.PROTECT, related_name='product_of_the_day', verbose_name=_('Pharmacy'))
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT, related_name='product_of_the_day', verbose_name=_('Medication'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Price'), blank=False)

    def __str__(self):
        return str(self.id)
