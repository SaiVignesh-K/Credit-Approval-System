from django.core.management.base import BaseCommand
import pandas as pd
from loans.models import Customer, Loan
from datetime import datetime
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Delete all rows and re-import customer and loan data from Excel files'

    def handle(self, *args, **kwargs):
        # Delete all existing data from the Customer and Loan tables
        Loan.objects.all().delete()  # Deletes all loans
        Customer.objects.all().delete()  # Deletes all customers

        self.stdout.write(self.style.SUCCESS('Successfully deleted all data'))

        # Import customer data
        df_customers = pd.read_excel('/app/customer_data.xlsx')
        for _, row in df_customers.iterrows():
            # Create customer only if it doesn't exist already
            Customer.objects.get_or_create(
                customer_id=row['Customer ID'],
                defaults={
                    'first_name': row['First Name'],
                    'last_name': row['Last Name'],
                    'age': row['Age'],
                    'phone_number': row['Phone Number'],
                    'monthly_salary': row['Monthly Salary'],
                    'approved_limit': row['Approved Limit'],
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully imported customer data'))

        # Import loan data
        df_loans = pd.read_excel('/app/loan_data.xlsx')  # Fix the path to the correct one
        for _, row in df_loans.iterrows():
            try:
                # Fetch the customer for the loan
                customer = Customer.objects.get(customer_id=row['Customer ID'])
                
                # Create the loan record and associate it with the customer
                loan, created = Loan.objects.update_or_create(
                loan_id=row['Loan ID'],  # Unique field, as it's the primary key
                defaults={
                    'customer_id': customer,
                    'loan_amount': row['Loan Amount'],
                    'interest_rate': row['Interest Rate'],
                    'tenure': row['Tenure'],
                    'monthly_repayment': row['Monthly payment'],
                    'emis_paid_on_time': row['EMIs paid on Time'],
                    'start_date': datetime.strptime(str(row['Date of Approval']), '%Y-%m-%d %H:%M:%S').date(),
                    'end_date': datetime.strptime(str(row['End Date']), '%Y-%m-%d %H:%M:%S').date()
                    }
                )
            
            except Customer.DoesNotExist:
                # If the customer does not exist, print a warning and skip
                self.stdout.write(self.style.WARNING(f"Customer with ID {row['Customer ID']} does not exist. Skipping loan import for this customer."))
            except IntegrityError as e:
                # Handle cases where the loan already exists or violates constraints
                self.stdout.write(self.style.ERROR(f"Error creating loan for Customer ID {row['Customer ID']}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('Successfully imported loan data'))
