from django.http import HttpResponse
from .models import Order, OrderLineItem
from items.models import Item
from members.models import MemberProfile

import json
import time

class StripeWH_Handler:
    """ Handle Stripe Webhooks """

    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        """ Handle a generic or unknown or unexpected webhook event """
        return HttpResponse(content=f'Unhandled Webhook received: {event["type"]}', status=200)
    
    def handle_payment_intent_succeeded(self, event):
        """ Handle the payment_intent.succeeded webhook from stripe """
        intent = event.data.object
        pid = intent.id
        shopping_bag = intent.metadata.bag
        save_info = intent.metadata.save_info

        billing_details = intent.charges.data[0].billing_details
        shipping_details = intent.shipping
        grand_total = round(intent.charges.data[0].amount / 100, 2)

        # Clean data in the shipping details
        for field, value in shipping_details.address.items():
            if value == "":
                shipping_details.address[field] = None

        # Update the member profile info if the save info button was clicked
        member_profile = None
        username = intent.metadata.username
        if username!= 'AnonymousUser':
            member_profile = MemberProfile.objects.get(user__username =username)
            member_profile.default_phone_number = shipping_details.phone
            member_profile.default_country = shipping_details.address.country
            member_profile.default_postcode = shipping_details.address.postal_code
            member_profile.default_town_or_city = shipping_details.address.city
            member_profile.default_street_address1 = shipping_details.address.line1
            member_profile.default_street_address2 = shipping_details.address.line2
            member_profile.default_county = shipping_details.address.state
            member_profile.save()


        order_exists = False
        attempt = 1
        # check database for order
        while attempt <= 5:
            try:
                order = Order.objects.get(
                    full_name__iexact=shipping_details.name,
                    email__iexact=billing_details.email,
                    phone_number__iexact=shipping_details.phone,
                    country__iexact=shipping_details.address.country,
                    postcode__iexact=shipping_details.address.postal_code,
                    town_or_city__iexact=shipping_details.address.city,
                    street_address1__iexact=shipping_details.address.line1,
                    street_address2__iexact=shipping_details.address.line2,
                    county__iexact=shipping_details.address.state,
                    grand_total=grand_total,
                    original_bag_items=shopping_bag,
                    stripe_pid=pid,
                )
                order_exists = True
                break
            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)
        if order_exists:
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | SUCCESS: Verified order already in database',
                status=200)
        else:
            order = None
            try:
                order = Order.objects.create(
                    full_name=shipping_details.name,
                    member_profile=member_profile,
                    email=billing_details.email,
                    phone_number=shipping_details.phone,
                    country=shipping_details.address.country,
                    postcode=shipping_details.address.postal_code,
                    town_or_city=shipping_details.address.city,
                    street_address1=shipping_details.address.line1,
                    street_address2=shipping_details.address.line2,
                    county=shipping_details.address.state,
                    original_bag_items=shopping_bag,
                    stripe_pid=pid,
                )
                for item_id, quantity in json.loads(shopping_bag).items():
                    item = Item.objects.get(id=item_id)
                    order_line_item = OrderLineItem(
                        order=order,
                        item=item,
                        quantity=quantity,
                    )
                    order_line_item.save()
            except Exception as e:
                if order:
                    order.delete()
                return HttpResponse(
                    content=f'Webhook received: {event["type"]} | ERROR: {e}',
                    status=500)
        return HttpResponse(
            content=f'Webhook received: {event["type"]} | SUCCESS: Created order in webhook',
            status=200)

    
    def handle_payment_intent_payment_failed(self, event):
        """ Handle the payment_intent.payment_failed webhook from stripe """
        return HttpResponse(content=f'Webhook received: {event["type"]}', status=200)

