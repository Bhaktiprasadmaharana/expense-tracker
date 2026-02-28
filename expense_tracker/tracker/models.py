from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Bills', 'Bills'),
        ('Entertainment', 'Entertainment'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")

    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.amount}"

class Debt(models.Model):
    TYPE_CHOICES = (
        ('borrowed', 'Borrowed'),
        ('lent', 'Lent'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="debts")
    person_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    @property
    def total_paid(self):
        from django.db.models import Sum
        return self.payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

    @property
    def remaining(self):
        return self.amount - self.total_paid

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.person_name} ({self.type}) - ₹{self.amount}"


# New model for DebtPayment
class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment of ₹{self.amount} for {self.debt.person_name}"