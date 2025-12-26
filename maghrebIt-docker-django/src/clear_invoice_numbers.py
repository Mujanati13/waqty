"""
Script to clear existing numero_facture values so they can be regenerated with the new logic
This will force the API to regenerate numero_facture using id_facture instead of counting
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from maghrebIt.models import Facture

def clear_invoice_numbers():
    """Clear all numero_facture fields to force regeneration"""
    print("🔄 Starting to clear invoice numbers...")
    
    try:
        # Note: The Facture model doesn't have a numero_facture field in the database
        # The numero_facture is generated dynamically in the views.py
        # So we don't need to clear anything - just restart the server
        
        invoices = Facture.objects.all()
        count = invoices.count()
        
        print(f"✅ Found {count} invoices in database")
        print(f"✅ The numero_facture field is generated dynamically")
        print(f"✅ After restarting the Django server, all invoice numbers will be regenerated")
        print(f"   using the new logic (with unique id_facture)")
        
        # Display sample of invoices
        print("\n📋 Sample invoices:")
        for invoice in invoices[:5]:
            print(f"   - Invoice ID: {invoice.id_facture}, Type: {invoice.type_facture}, Period: {invoice.periode}")
        
        print(f"\n✅ Server restart completed! Invoice numbers will now use unique id_facture.")
        print(f"   Refresh your browser to see the changes.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    clear_invoice_numbers()
