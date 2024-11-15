from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Customer, Loan
from .serializers import (
    CustomerSerializer, LoanSerializer, CustomerRegistrationSerializer,
    LoanEligibilitySerializer, CreateLoanSerializer
)
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Max
import math

def calculate_credit_score(c_id):
    loans = Loan.objects.filter(customer_id=c_id)
    if not loans:
        return 50  # Default score for new customers
    
    score = 50
    total_loans = loans.count()
    paid_on_time = sum(loan.emis_paid_on_time for loan in loans)
    current_year_loans = loans.filter(start_date__year=date.today().year).count()
    
    # Adjust score based on payment history
    if total_loans > 0:
        payment_ratio = paid_on_time / (total_loans * 12)
        score += payment_ratio * 20
    
    # Adjust for loan volume
    if total_loans <= 3:
        score += 10
    elif total_loans <= 5:
        score += 5
    
    # Penalize for too many current year loans
    if current_year_loans > 3:
        score -= 20
    
    return min(100, max(0, score))

@api_view(['POST'])
def register_customer(request):
    serializer = CustomerRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        monthly_salary = Decimal(serializer.validated_data['monthly_salary'])
        approved_limit = math.floor(monthly_salary * 36 / 100000) * 100000
        
        max_id = Customer.objects.aggregate(Max('customer_id'))['customer_id__max'] or 0
        new_customer_id = max_id + 1

        customer = Customer.objects.create(
            customer_id=new_customer_id,
            **serializer.validated_data,
            approved_limit=approved_limit,
            current_debt=0
        )
        
        return Response({
            'customer_id': customer.customer_id,
            'name': f"{customer.first_name} {customer.last_name}",
            'age': customer.age,
            'monthly_income': customer.monthly_salary,
            'approved_limit': customer.approved_limit,
            'phone_number': customer.phone_number
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def check_eligibility(request):
    serializer = LoanEligibilitySerializer(data=request.data)
    if serializer.is_valid():
        customer = Customer.objects.get(customer_id=serializer.validated_data['customer_id'])
        credit_score = calculate_credit_score(customer.customer_id)
        
        loan_amount = Decimal(serializer.validated_data['loan_amount'])  # Convert to Decimal
        interest_rate = Decimal(serializer.validated_data['interest_rate'])  # Convert to Decimal
        tenure = serializer.validated_data['tenure']
        
        # Calculate monthly EMI
        monthly_rate = interest_rate / (12 * 100)
        emi = (loan_amount * monthly_rate * (1 + monthly_rate)**tenure) / ((1 + monthly_rate)**tenure - 1)
        
        # Check eligibility conditions
        current_loans = Loan.objects.filter(customer_id=customer.customer_id)
        total_emi = sum(loan.monthly_repayment for loan in current_loans)
        
        if total_emi + emi > customer.monthly_salary * Decimal(0.5):  # Convert 0.5 to Decimal
            return Response({
                'customer_id': customer.customer_id,
                'approval': False,
                'interest_rate': float(interest_rate),  # Convert Decimal back to float for the response
                'corrected_interest_rate': float(interest_rate),  # Convert Decimal back to float
                'tenure': tenure,
                'monthly_installment': float(emi),  # Convert Decimal back to float
            })
        
        # Determine approval and interest rate based on credit score
        approval = True
        corrected_interest_rate = interest_rate
        
        if credit_score < 10:
            approval = False
        elif credit_score < 30:
            if interest_rate < Decimal(16):
                corrected_interest_rate = Decimal(16)
        elif credit_score < 50:
            if interest_rate < Decimal(12):
                corrected_interest_rate = Decimal(12)
        
        return Response({
            'customer_id': customer.customer_id,
            'approval': approval,
            'interest_rate': float(interest_rate),
            'corrected_interest_rate': float(corrected_interest_rate),
            'tenure': tenure,
            'monthly_installment': float(emi),
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def check_loan_eligibility(c_id, loan_amount, interest_rate, tenure):
    try:
        customer = Customer.objects.get(customer_id=c_id)
        credit_score = calculate_credit_score(c_id)
        
        # Calculate monthly EMI
        monthly_rate = Decimal(interest_rate) / (12 * 100)
        emi = (Decimal(loan_amount) * monthly_rate * (1 + monthly_rate)**tenure) / ((1 + monthly_rate)**tenure - 1)
        
        # Check eligibility conditions
        current_loans = Loan.objects.filter(customer_id=c_id)
        total_emi = sum(loan.monthly_repayment for loan in current_loans)
        
        if total_emi + emi > customer.monthly_salary * Decimal('0.5'):
            return {
                'customer_id': c_id,
                'approval': False,
                'interest_rate': interest_rate,
                'corrected_interest_rate': interest_rate,
                'tenure': tenure,
                'monthly_installment': emi
            }
        
        # Determine approval and interest rate based on credit score
        approval = True
        corrected_interest_rate = interest_rate
        
        if credit_score < 10:
            approval = False
        elif credit_score < 30:
            if interest_rate < 16:
                corrected_interest_rate = 16
        elif credit_score < 50:
            if interest_rate < 12:
                corrected_interest_rate = 12
        
        return {
            'customer_id': c_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate,
            'tenure': tenure,
            'monthly_installment': emi
        }
    except Customer.DoesNotExist:
        return None


@api_view(['POST'])
def create_loan(request):
    serializer = CreateLoanSerializer(data=request.data)
    
    if not Customer.objects.filter(customer_id=request.data['customer_id']).exists():
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

    customer = Customer.objects.get(customer_id=request.data['customer_id'])

    if serializer.is_valid():
        # Check eligibility first
        eligibility_result = check_loan_eligibility(
            request.data['customer_id'],
            request.data['loan_amount'],
            request.data['interest_rate'],
            request.data['tenure']
        )
        
        if not eligibility_result or not eligibility_result['approval']:
            return Response({
                'loan_id': None,
                'customer_id': customer.customer_id,
                'loan_approved': False,
                'message': 'Loan not approved based on eligibility criteria',
                'monthly_installment': eligibility_result['monthly_installment'] if eligibility_result else None
            })

        max_id = Loan.objects.aggregate(Max('loan_id'))['loan_id__max'] or 0
        new_loan_id = max_id + 1

        # Create the loan
        loan = Loan.objects.create(
            loan_id=new_loan_id,
            customer_id=customer,
            loan_amount=request.data['loan_amount'],
            interest_rate=eligibility_result['corrected_interest_rate'],
            tenure=request.data['tenure'],
            monthly_repayment=eligibility_result['monthly_installment'],
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30*request.data['tenure'])
        )
        
        return Response({
            'loan_id': loan.loan_id,
            'customer_id': loan.customer_id.customer_id,
            'loan_approved': True,
            'message': 'Loan approved',
            'monthly_installment': loan.monthly_repayment
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def view_loan(request, loan_id):
    try:
        loan = Loan.objects.get(loan_id=loan_id)
        return Response({
            'loan_id': loan.loan_id,
            'customer': {
                'customer_id': loan.customer_id.customer_id,
                'first_name': loan.customer_id.first_name,
                'last_name': loan.customer_id.last_name,
                'phone_number': loan.customer_id.phone_number,
                'age': loan.customer_id.age
            },
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_repayment,
            'tenure': loan.tenure
        })
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def view_loans(request, customer_id):
    loans = Loan.objects.filter(customer_id=customer_id)
    loan_data = []
    
    for loan in loans:
        months_passed = (date.today().year - loan.start_date.year) * 12 + (date.today().month - loan.start_date.month)
        repayments_left = max(0, loan.tenure - months_passed)
        
        loan_data.append({
            'loan_id': loan.loan_id,
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_repayment,
            'repayments_left': repayments_left
        })
    
    return Response(loan_data)