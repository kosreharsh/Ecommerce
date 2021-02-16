from django.db import models
from django.urls import reverse
from django.conf.global_settings import AUTH_USER_MODEL as User
from django.utils.text import slugify
from django_countries.fields import CountryField

Category_choices = (
    ('S', 'Shirt'),
    ('SW', 'Sportwear'),
    ('OW', 'Outwear')
)

Label_choices = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger')
)
# Create your models here.
class Address(models.Model):
    user = models.ForeignKey( User, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zipcode = models.CharField(max_length=10)
    use_default_shipping = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class PaymentViaPaytm(models.Model):
    order_id = models.CharField(max_length=250)
    checksum = models.CharField(max_length=250)
    user = models.ForeignKey( User, on_delete=models.SET_NULL,null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=50)
    user = models.ForeignKey( User, on_delete=models.SET_NULL,null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
    
    


class Item(models.Model):
    name =  models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField()
    category = models.CharField(choices=Category_choices,max_length=2)
    label = models.CharField(choices=Label_choices,max_length=1)
    description = models.TextField(default="",blank=True)
    slug = models.SlugField()
    image = models.ImageField(upload_to='item/images',blank=True,null=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('main:product-detail', kwargs={'slug': self.slug})
    
    

class OrderItem(models.Model):
    item = models.ForeignKey( Item,on_delete=models.CASCADE)
    user = models.ForeignKey( User, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.quantity} of {self.item.name}" 

    def get_total_amount(self):
        return self.quantity * self.item.price - self.get_discount_amount()
    
    def get_discount_amount(self):
        if self.item.discount_price:
            return self.quantity * self.item.discount_price
        return 0;
    
    def get_amount_saved(self):
        if self.item.discount_price:
            return self.get_total_amount() - self.get_discount_amount()
        return 0;
    


class Order(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    ordered = models.BooleanField(default=False)
    ordered_date = models.DateField()
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey( Payment, related_name='Payment',on_delete=models.SET_NULL, blank=True, null=True)
    payment_via_paytm = models.ForeignKey( 'PaymentViaPaytm',on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey( 'Coupon',on_delete=models.SET_NULL, blank=True, null=True)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    being_delivered = models.BooleanField(default=False)
    ref_code = models.CharField(max_length=20,blank=True,null=True)

    def __str__(self):
        return self.user.username
    
    def get_final_amount(self):
        total = 0
        for x in self.items.all():
            total += x.get_total_amount()
        if self.coupon:
            total -= self.coupon.amount
        return total

class Coupon(models.Model):
    code = models.CharField(max_length=15)
    amount = models.FloatField()

    def __str__(self):
        return self.code

class Refund(models.Model):
    order = models.ForeignKey( Order, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200)
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"
