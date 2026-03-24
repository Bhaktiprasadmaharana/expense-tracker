from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from decimal import Decimal, InvalidOperation

from .models import Expense, Debt, DebtPayment
from .forms import CustomUserCreationForm


@login_required
def home(request):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        amount_raw = request.POST.get('amount', '').strip()
        category = request.POST.get('category', '').strip()
        date_raw = request.POST.get('date', '').strip()

        # Validate inputs
        if not title or not amount_raw or not category:
            messages.error(request, "All fields are required.")
            return redirect('home')

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, "Please enter a valid positive amount.")
            return redirect('home')

        expense_kwargs = dict(user=request.user, title=title, amount=amount, category=category)
        if date_raw:
            try:
                from datetime import date
                expense_kwargs['date'] = date.fromisoformat(date_raw)
            except ValueError:
                pass  # fall back to default (today)

        Expense.objects.create(**expense_kwargs)
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

    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0

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

    # Current month total for the stat card
    now = timezone.now()
    this_month_total = (
        Expense.objects
        .filter(user=request.user, date__year=now.year, date__month=now.month)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    return render(request, 'tracker/home.html', {
        'expenses': expenses,
        'total_expense': total_expense,
        'category_summary': category_summary,
        'available_months': available_months,
        'sidebar_balance': total_expense,
        'this_month_total': this_month_total,
    })


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        amount_raw = request.POST.get('amount', '').strip()
        category = request.POST.get('category', '').strip()
        date_raw = request.POST.get('date', '').strip()

        if not title or not amount_raw or not category:
            messages.error(request, "All fields are required.")
            return redirect('edit_expense', pk=pk)

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, "Please enter a valid positive amount.")
            return redirect('edit_expense', pk=pk)

        expense.title = title
        expense.amount = amount
        expense.category = category
        if date_raw:
            try:
                from datetime import date
                expense.date = date.fromisoformat(date_raw)
            except ValueError:
                pass
        expense.save()
        messages.success(request, "Expense updated successfully.")
        return redirect('home')

    return render(request, 'tracker/edit_expense.html', {'expense': expense})


@login_required
@require_POST
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
        'total_expense': total_expense,
        'sidebar_balance': total_expense,
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
        "sidebar_balance": total_expense,
    })


@login_required
def debt_list(request):
    if request.method == "POST":
        person_name = request.POST.get("person_name", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        debt_type = request.POST.get("type", "").strip()
        note = request.POST.get("note", "").strip()

        if person_name and amount_raw and debt_type:
            try:
                amount = Decimal(amount_raw)
                if amount <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid positive amount.")
                return redirect("debt_list")

            Debt.objects.create(
                user=request.user,
                person_name=person_name,
                amount=amount,
                type=debt_type,
                note=note
            )
            messages.success(request, "Record added successfully.")
            return redirect("debt_list")
        else:
            messages.error(request, "All required fields must be filled.")
            return redirect("debt_list")

    debts = Debt.objects.filter(user=request.user).prefetch_related('payments').order_by("-created_at")

    total_borrowed = Decimal("0")
    total_lent = Decimal("0")

    for debt in debts:
        total_paid = debt.payments.aggregate(
            Sum("amount")
        )["amount__sum"] or Decimal("0")
        remaining = debt.amount - total_paid

        if debt.type == "borrowed":
            total_borrowed += remaining
        else:
            total_lent += remaining

    net_balance = total_lent - total_borrowed

    return render(request, "tracker/debt_list.html", {
        "debts": debts,
        "total_borrowed": total_borrowed,
        "total_lent": total_lent,
        "net_balance": net_balance,
        "sidebar_balance": net_balance,
        "edit_mode": request.session.get("edit_mode", False),
    })


@login_required
def edit_debt(request, pk):
    debt = get_object_or_404(Debt, pk=pk, user=request.user)

    if request.method == "POST":
        person_name = request.POST.get("person_name", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        debt_type = request.POST.get("type", "").strip()
        note = request.POST.get("note", "").strip()

        if not person_name or not amount_raw or not debt_type:
            messages.error(request, "All required fields must be filled.")
            return redirect("edit_debt", pk=pk)

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, "Please enter a valid positive amount.")
            return redirect("edit_debt", pk=pk)

        debt.person_name = person_name
        debt.amount = amount
        debt.type = debt_type
        debt.note = note
        debt.save()
        messages.success(request, "Debt record updated successfully.")
        return redirect("debt_list")

    total_paid = debt.payments.aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    remaining = debt.amount - total_paid

    return render(request, "tracker/edit_debt.html", {
        "debt": debt,
        "total_paid": total_paid,
        "remaining": remaining,
        "sidebar_balance": 0,
    })


@login_required
@require_POST
def delete_debt(request, pk):
    debt = get_object_or_404(Debt, pk=pk, user=request.user)
    debt.delete()
    messages.success(request, "Debt deleted successfully.")
    return redirect('debt_list')


@login_required
@require_POST
def verify_password(request):
    password = request.POST.get("password")

    if request.user.check_password(password):
        request.session["edit_mode"] = True
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False})


@login_required
def disable_edit_mode(request):
    request.session["edit_mode"] = False
    return redirect("debt_list")


@login_required
@require_POST
def add_payment(request, pk):
    debt = get_object_or_404(Debt, pk=pk, user=request.user)

    amount_raw = request.POST.get("amount")

    try:
        amount = Decimal(amount_raw)
    except (TypeError, ValueError, InvalidOperation):
        messages.error(request, "Invalid payment amount.")
        return redirect("debt_list")

    if amount <= 0:
        messages.error(request, "Payment amount must be greater than zero.")
        return redirect("debt_list")

    total_paid = debt.payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0")
    remaining = debt.amount - total_paid

    if amount > remaining:
        messages.error(request, f"Payment exceeds remaining amount (₹{remaining}).")
        return redirect("debt_list")

    DebtPayment.objects.create(
        debt=debt,
        amount=amount
    )

    messages.success(request, "Payment added successfully.")
    return redirect("debt_list")


@login_required
@require_POST
def delete_payment(request, pk):
    payment = get_object_or_404(DebtPayment, pk=pk, debt__user=request.user)
    payment.delete()
    messages.success(request, "Payment deleted successfully.")
    return redirect("debt_list")