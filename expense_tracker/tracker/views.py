from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from .models import Expense
from django.db.models import Sum
from django.db.models.functions import TruncMonth

from .forms import CustomUserCreationForm


@login_required
def home(request):
    if request.method == "POST":
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        category = request.POST.get('category')

        Expense.objects.create(
            user=request.user,
            title=title,
            amount=amount,
            category=category
        )

        messages.success(request, "Expense added successfully.")
        return redirect('home')

    expenses = Expense.objects.filter(user=request.user)

    search_query = request.GET.get('search')
    if search_query:
        expenses = expenses.filter(title__icontains=search_query)

    month = request.GET.get('month')
    if month:
        expenses = expenses.filter(date__month=month)

    expenses = expenses.order_by('-date')

    total_expense = expenses.aggregate(
        total=Sum('amount')
    )['total'] or 0

    category_summary = (
        expenses
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    available_months = (
        Expense.objects
        .filter(user=request.user)
        .dates('date', 'month', order='DESC')
    )

    return render(request, 'tracker/home.html', {
        'expenses': expenses,
        'total_expense': total_expense,
        'category_summary': category_summary,
        'available_months': available_months,
    })


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)

    if request.method == "POST":
        expense.title = request.POST.get('title')
        expense.amount = request.POST.get('amount')
        expense.category = request.POST.get('category')
        expense.save()
        messages.success(request, "Expense updated successfully.")
        return redirect('home')

    return render(request, 'tracker/edit_expense.html', {'expense': expense})


@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    expense.delete()
    messages.success(request, "Expense deleted successfully.")
    return redirect('home')


def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created successfully! Welcome, {user.username} 🎉")
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


@login_required
def categories_view(request):
    category_summary = (
        Expense.objects
        .filter(user=request.user)
        .values('category')
        .annotate(total=Sum('amount'))
    )

    total_expense = Expense.objects.filter(user=request.user).aggregate(
        Sum('amount')
    )['amount__sum'] or 0

    return render(request, 'tracker/categories.html', {
        'category_summary': category_summary,
        'total_expense': total_expense
    })


@login_required
def reports_view(request):
    selected_month = request.GET.get("month")

    expenses = Expense.objects.filter(user=request.user)

    if selected_month:
        expenses = expenses.filter(date__month=selected_month)

    monthly_summary = (
        expenses
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    total_expense = Expense.objects.filter(user=request.user).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    return render(request, "tracker/reports.html", {
        "monthly_summary": monthly_summary,
        "total_expense": total_expense,
        "selected_month": selected_month,
    })