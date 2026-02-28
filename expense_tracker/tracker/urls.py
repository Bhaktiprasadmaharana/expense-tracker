from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('edit/<int:pk>/', views.edit_expense, name='edit_expense'),
    path('delete/<int:pk>/', views.delete_expense, name='delete_expense'),
    path('categories/', views.categories_view, name='categories'),
    path('reports/', views.reports_view, name='reports'),
    path('debts/', views.debt_list, name='debt_list'),
    path('debts/edit/<int:pk>/', views.edit_debt, name='edit_debt'),
    path('debts/delete/<int:pk>/', views.delete_debt, name='delete_debt'),
    path('debts/verify-password/', views.verify_password, name='verify_password'),
    path('debts/add-payment/<int:pk>/', views.add_payment, name='add_payment'),
    path('payments/delete/<int:pk>/', views.delete_payment, name='delete_payment'),
    path('debts/disable-edit/', views.disable_edit_mode, name='disable_edit_mode'),
]