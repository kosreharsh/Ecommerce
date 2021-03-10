from django.db import models
from django.urls import reverse
from django.conf.global_settings import AUTH_USER_MODEL as User
from django.utils.text import slugify
from django_countries.fields import CountryField
import channels.layers 
from django.dispatch import receiver  
from asgiref.sync import async_to_sync
import json  
from django.db.models.signals import post_save,pre_save  
import random, string

def create_ref(k):
    return ''.join(random.choices(string.ascii_lowercase+string.ascii_uppercase, k=10))


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
order_status_choices = (
    ('ORD','Order Received'),
    ('OFD' , 'Out For Delivery'),
    ('D','Dispatch'),
    ('OD' , 'Order Delivered'),
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
    discount_price = models.FloatField(default=0)
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
    
    def get_item_price(self):
        return self.price-self.discount_price
    
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
    ordered_date = models.DateField(null=True)
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey( Payment, related_name='Payment',on_delete=models.SET_NULL, blank=True, null=True)
    payment_via_paytm = models.ForeignKey( 'PaymentViaPaytm',on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey( 'Coupon',on_delete=models.SET_NULL, blank=True, null=True)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)
    order_status = models.CharField(choices=order_status_choices,max_length=4,default='ORD')
    ref_code = models.CharField(max_length=20,blank=True,null=True)

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return reverse('main:orderStatus',kwargs={'ref_code':self.ref_code})

    def save(self,*args,**kwargs):
        if self.ref_code == None:
            self.ref_code = create_ref(10)
        super(Order, self).save(*args,**kwargs)
    
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

@receiver(post_save,sender=Order)
def order_status_handler(sender,instance,created,**kwargs):
    if not created:
        channels_layer = channels.layers.get_channel_layer()
        data = {}
        data['order_id'] = instance.id 
        data['amount'] = instance.get_final_amount() 
        data['status'] = instance.get_order_status_display()
        data['date'] = str(instance.ordered_date)
        progress_percentage = 20
        if instance.order_status == 'Order Recieved':
            progress_percentage = 20
        elif instance.order_status == 'Dispatch':
            progress_percentage = 50
        elif instance.order_status == 'Out For Delivery':
            progress_percentage = 80
        elif instance.order_status == 'Order Delivered':
            progress_percentage = 100   
        data['progress'] = progress_percentage

        async_to_sync(channels_layer.group_send)(
            'order_%s' % instance.id,{
                'type' : 'order_status',
                'payload' : json.dumps(data)
            }
        )



        
