from .models import Inventory, InventoryHistory
from django.utils import timezone

def update_inventory(pharmacy, medicine, quantity, price=None, batch_number='', expiry_date=None):
    if quantity < 0:
        raise ValueError("Quantity cannot be negative")
        
    inventory, created = Inventory.objects.get_or_create(
        pharmacy=pharmacy,
        medicine=medicine,
        defaults={
            'quantity': quantity,
            'price': price,
            'batch_number': batch_number,
            'expiry_date': expiry_date,
        }
    )
    
    if not created:
        inventory.quantity = quantity
        if price is not None:
            inventory.price = price
        if batch_number:
            inventory.batch_number = batch_number
        if expiry_date:
            inventory.expiry_date = expiry_date
        inventory.save()
        
    InventoryHistory.objects.create(
        pharmacy=pharmacy,
        medicine=medicine,
        quantity=quantity,
    )
    
    return inventory
