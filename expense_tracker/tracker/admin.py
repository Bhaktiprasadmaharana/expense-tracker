from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'category', 'user', 'date')
    list_filter = ('category', 'date')
    search_fields = ('title', 'user__username')
    ordering = ('-date',)
    list_per_page = 20

    # Optional: Make fields readonly if needed
    # readonly_fields = ('date',)

    fieldsets = (
        ('Expense Information', {
            'fields': ('title', 'amount', 'category')
        }),
        ('User Information', {
            'fields': ('user', 'date')
        }),
    )