# Credit-Approval-System
I've created a complete Django-based credit approval system with all the required endpoints and functionality. Here's what's included:

Project Structure:
Django 4+ with Django REST Framework
PostgreSQL database
Docker and docker-compose setup

Models:
Customer model with all required fields
Loan model with loan-related fields

API Endpoints:
/api/register - Register new customers
/api/check-eligibility - Check loan eligibility
/api/create-loan - Process new loans
/api/view-loan/<loan_id> - View specific loan details
/api/view-loans/<customer_id> - View all loans for a customer

Features:
Credit score calculation based on multiple factors
Loan eligibility checks
Data import command for Excel files

To use the system:
Place your Excel files (customer_data.xlsx and loan_data.xlsx) in the project root
Run docker-compose up --build to start the system

Once running, import data using:
docker-compose exec web python manage.py import_data

The API will be available at http://localhost:8000/api/.
All endpoints are implemented according to the specifications, including proper error handling and status codes. 
