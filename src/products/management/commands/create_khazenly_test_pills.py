"""
Management command to create test pills for Khazenly integration testing.
These pills use the same product data from failed orders but with test user info.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from products.models import (
    from django.core.management.base import BaseCommand


    class Command(BaseCommand):
        help = 'Khazenly test data command removed; manual shipping is active'

        def handle(self, *args, **options):
            self.stdout.write(self.style.WARNING('Khazenly integration is disabled.'))
                    user=test_user,
                    product=product,
                    quantity=order_data['quantity'],
                    size=None,  # No size for books
                    color=None,  # No color for books
                    status='i',  # Initiated
                )
                
                # Create Pill
                pill = Pill.objects.create(
                    user=test_user,
                    status='i',  # Initiated - you'll mark as paid in admin
                    paid=False,
                )
                
                # Add item to pill
                pill.items.add(pill_item)
                
                # Create PillAddress with TEST data
                pill_address = PillAddress.objects.create(
                    pill=pill,
                    name='test test test',  # Test name as requested
                    email='test@test.com',
                    phone='01000000000',  # Random test phone as requested
                    address=order_data['address'],
                    government=order_data['government'],
                    city=order_data['city'],
                    pay_method='v',  # Visa/Prepaid
                )
                
                created_pills.append({
                    'pill': pill,
                    'address': pill_address,
                    'government': gov_name,
                })
                
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Created Pill ID: {pill.id}, Number: {pill.pill_number}"
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error creating pill: {str(e)}"))

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✅ Created {len(created_pills)} test pills"))
        self.stdout.write(f"{'='*60}\n")
        
        if created_pills:
            self.stdout.write("📋 Pills created (ready to be marked as Paid in Django Admin):\n")
            for item in created_pills:
                pill = item['pill']
                self.stdout.write(f"   • Pill #{pill.pill_number} (ID: {pill.id}) - {item['government']}")
            
            self.stdout.write("\n📝 Next Steps:")
            self.stdout.write("   1. Go to Django Admin → Products → Pills")
            self.stdout.write("   2. Filter by user 'khazenly_test_user' or search by pill number")
            self.stdout.write("   3. Select the test pills and mark them as 'Paid'")
            self.stdout.write("   4. Use the 'Send to Khazenly' action to test the integration")
            self.stdout.write("")
