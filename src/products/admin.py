from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponse
from .models import (
    Category, SubCategory, Brand, Product, ProductImage, ProductDescription,
    Color, ProductAvailability, Shipping, PillItem, Pill, PillAddress,
    PillStatusLog, CouponDiscount, Rating, Discount, LovedProduct,
    StockAlert, PriceDropAlert, SpecialProduct, SpinWheelDiscount,
    SpinWheelResult, SpinWheelSettings, CartSettings, PillGift,
    OverTaxConfig, FreeShippingOffer
)

import json
try:
    import xlsxwriter
    EXCEL_AVAILABLE = True
except ImportError:
    try:
        import openpyxl
        EXCEL_AVAILABLE = True
    except ImportError:
        EXCEL_AVAILABLE = False
import io
from datetime import datetime

class GovernmentListFilter(admin.SimpleListFilter):
    title = 'Government'
    parameter_name = 'government'

    def lookups(self, request, model_admin):
        from .models import GOVERNMENT_CHOICES
        
        # Add custom option for null/blank governments
        choices = [
            ('null', 'No Government (Empty)'),
        ]
        
        # Add all government choices
        choices.extend(GOVERNMENT_CHOICES)
        
        return choices

    def queryset(self, request, queryset):
        if self.value() == 'null':
            return queryset.filter(government__isnull=True) | queryset.filter(government='')
        elif self.value():
            return queryset.filter(government=self.value())
        return queryset

class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_image_preview')
    search_fields = ('name',)
    inlines = [SubCategoryInline]

    @admin.display(description='Image')
    def get_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"

# FIX: Added a dedicated admin for SubCategory with search_fields
@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name', 'category__name')
    autocomplete_fields = ('category',)
    list_filter = ('category',)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_logo_preview')
    search_fields = ('name',)

    @admin.display(description='Logo')
    def get_logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" />', obj.logo.url)
        return "No Logo"

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductDescriptionInline(admin.TabularInline):
    model = ProductDescription
    extra = 1

class ProductAvailabilityInline(admin.TabularInline):
    model = ProductAvailability
    extra = 1
    autocomplete_fields = ['color']

class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0
    fields = ('discount', 'discount_start', 'discount_end', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','product_number' ,'type','is_active','get_base_image_preview', 'category', 'price', 'get_total_quantity', 'average_rating', 'is_important', 'date_added')
    list_filter = ('category', 'brand', 'is_important', 'date_added', 'is_active')
    search_fields = ('name', 'description')
    autocomplete_fields = ('category', 'sub_category', 'brand')
    readonly_fields = ('average_rating', 'number_of_ratings', 'get_total_quantity')
    inlines = [ProductImageInline, ProductDescriptionInline, ProductAvailabilityInline, DiscountInline]
    list_select_related = ('category', 'brand')
    list_editable = ('type', 'is_active')

    @admin.display(description='Image')
    def get_base_image_preview(self, obj):
        if obj.base_image:
            return format_html('<img src="{}" width="50" height="50" />', obj.base_image.url)
        return "No Image"
    
    @admin.display(description='Total Quantity', ordering='total_quantity')
    def get_total_quantity(self, obj):
        return obj.total_quantity()


@admin.register(ProductAvailability)
class ProductAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        'product', 
        'size', 
        'color', 
        'quantity', 
        'native_price', 
        'date_added'
    )
    list_filter = (
        'product__category', 
        'color', 
        'size', 
        'date_added'
    )
    search_fields = (
        'product__name', 
        'color__name', 
        'size'
    )
    readonly_fields = ('date_added',)
    ordering = ('-date_added',)
    date_hierarchy = 'date_added'

    autocomplete_fields = ['product', 'color']
    list_select_related = ['product', 'color']

    def get_queryset(self, request):
        # Optimize queryset by selecting related objects
        qs = super().get_queryset(request)
        return qs.select_related('product', 'color')

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'degree')
    search_fields = ('name', 'degree')

class PillAddressInline(admin.StackedInline):
    model = PillAddress
    can_delete = False

class PillStatusLogInline(admin.TabularInline):
    model = PillStatusLog
    extra = 0
    readonly_fields = ('status', 'changed_at')
    can_delete = False

# class PillItemInline(admin.TabularInline):
#     model = PillItem
#     extra = 0
#     autocomplete_fields = ('product', 'color')
#     readonly_fields = ('price_at_sale', 'native_price_at_sale', 'date_sold')
    
class FinalPriceListFilter(admin.SimpleListFilter):
    title = 'Max Final Price'
    parameter_name = 'max_final_price'

    def lookups(self, request, model_admin):
        # Provide choices for max price: 100, 200, ..., 1000
        return [(str(price), f'≤ {price}') for price in range(100, 1100, 100)]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            try:
                max_price = float(value)
                # Filter pills with final_price <= max_price
                return queryset.filter(id__in=[
                    pill.id for pill in queryset if pill.final_price() is not None and pill.final_price() <= max_price
                ])
            except Exception:
                return queryset
        return queryset

class StockProblemListFilter(admin.SimpleListFilter):
    title = 'Stock Problem Status'
    parameter_name = 'stock_problem'

    def lookups(self, request, model_admin):
        return [
            ('has_problem', 'Has Stock Problem'),
            ('resolved', 'Resolved'),
            ('no_problem', 'No Stock Problem'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'has_problem':
            return queryset.filter(has_stock_problem=True, is_resolved=False)
        elif self.value() == 'resolved':
            return queryset.filter(has_stock_problem=True, is_resolved=True)
        elif self.value() == 'no_problem':
            return queryset.filter(has_stock_problem=False)
        return queryset

@admin.register(Pill)
class PillAdmin(admin.ModelAdmin):
    list_display = [
        'pill_number', 'easypay_invoice_sequence', 'easypay_invoice_uid', 'user', 'paid', 'status', 'is_shipped',
        'stock_problem_status', 'final_price_display', 'get_calculate_over_tax_price',
    ]
    list_filter = ['status', 'paid', 'is_shipped', 'has_stock_problem', 'is_resolved', StockProblemListFilter, FinalPriceListFilter]
    search_fields = ['pill_number', 'user__username']
    readonly_fields = ['pill_number', 'stock_problem_items']
    list_editable = ['paid', 'status', 'is_shipped']
    actions = ['mark_stock_problems_resolved', 'check_stock_problems']

    def final_price_display(self, obj):
        return obj.final_price()
    def get_calculate_over_tax_price(self, obj):
        return obj.calculate_over_tax_price()
    final_price_display.short_description = 'Final Price'
    get_calculate_over_tax_price.short_description = 'Over Tax Price'
    final_price_display.admin_order_field = None
    get_calculate_over_tax_price.admin_order_field = None

    def stock_problem_status(self, obj):
        """Display stock problem status with color coding"""
        if obj.has_stock_problem:
            if obj.is_resolved:
                return format_html('<span style="color: #28a745; font-weight: bold;">✓ Resolved</span>')
            else:
                problem_count = len(obj.stock_problem_items) if obj.stock_problem_items else 0
                return format_html(
                    '<span style="color: #dc3545; font-weight: bold;">⚠ Problem ({} items)</span>',
                    problem_count
                )
        else:
            return format_html('<span style="color: #6c757d;">-</span>')
    
    stock_problem_status.short_description = 'Stock Status'
    stock_problem_status.admin_order_field = 'has_stock_problem'

    @admin.action(description='Mark selected pills as stock problems resolved')
    def mark_stock_problems_resolved(self, request, queryset):
        """Mark selected pills with stock problems as resolved"""
        updated_count = 0
        
        for pill in queryset.filter(has_stock_problem=True, is_resolved=False):
            # Check current stock availability
            availability_check = pill.check_all_items_availability()
            
            if availability_check['all_available']:
                # Stock is now available, mark as resolved
                pill.is_resolved = True
                pill.has_stock_problem = False
                pill.stock_problem_items = None
                pill.save(update_fields=['is_resolved', 'has_stock_problem', 'stock_problem_items'])
                updated_count += 1
            else:
                # Still has stock problems, update the problem items
                pill.stock_problem_items = availability_check['problem_items']
                pill.save(update_fields=['stock_problem_items'])
        
        if updated_count > 0:
            self.message_user(
                request,
                f'Successfully resolved stock problems for {updated_count} pills.',
                level='SUCCESS'
            )
        else:
            self.message_user(
                request,
                'No pills were resolved. Selected pills either still have stock problems or were already resolved.',
                level='WARNING'
            )

    @admin.action(description='Check stock problems for selected pills')
    def check_stock_problems(self, request, queryset):
        """Manually check stock problems for selected pills"""
        checked_count = 0
        problems_found = 0
        
        for pill in queryset.filter(paid=True):
            pill._check_and_update_stock_problems()
            pill.refresh_from_db()
            checked_count += 1
            
            if pill.has_stock_problem and not pill.is_resolved:
                problems_found += 1
        
        self.message_user(
            request,
            f'Checked {checked_count} pills. Found {problems_found} pills with stock problems.',
            level='INFO'
        )


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'discount', 'discount_start', 'discount_end', 'is_active', 'is_currently_active')
    list_filter = ('is_active', 'category')
    search_fields = ('product__name', 'category__name')
    autocomplete_fields = ('product', 'category')

@admin.register(CouponDiscount)
class CouponDiscountAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'discount_value', 'available_use_times', 'is_wheel_coupon', 'coupon_start', 'coupon_end')
    search_fields = ('coupon', 'user__username')
    readonly_fields = ('coupon',)
    autocomplete_fields = ['user']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'star_number', 'date_added')
    list_filter = ('star_number', 'date_added')
    search_fields = ('product__name', 'user__username', 'review')
    autocomplete_fields = ['product', 'user']

@admin.register(Shipping)
class ShippingAdmin(admin.ModelAdmin):
    list_display = ('get_government_display', 'shipping_price')
    list_editable = ('shipping_price',)

@admin.register(SpecialProduct)
class SpecialProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'is_active', 'created_at', 'get_image_preview')
    list_filter = ('is_active',)
    search_fields = ('product__name',)
    autocomplete_fields = ['product']
    list_editable = ('order', 'is_active')

    @admin.display(description='Special Image')
    def get_image_preview(self, obj):
        if obj.special_image:
            return format_html('<img src="{}" width="50" height="50" />', obj.special_image.url)
        return "No Image"

@admin.register(PillGift)
class PillGiftAdmin(admin.ModelAdmin):
    list_display = ('discount_value', 'min_order_value', 'max_order_value', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('discount_value',)

@admin.register(SpinWheelDiscount)
class SpinWheelDiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_value', 'probability', 'is_active', 'start_date', 'end_date', 'max_winners')
    list_filter = ('is_active',)

@admin.register(LovedProduct)
class LovedProductAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    autocomplete_fields = ('user', 'product')
    search_fields = ('user__username', 'product__name')

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'product', 'is_notified', 'created_at')
    list_filter = ('is_notified',)
    autocomplete_fields = ('user', 'product')
    search_fields = ('user__username', 'email', 'product__name')

@admin.register(PillAddress)
class PillAddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone','government', 'pill_number', 'email', 'city','address', 'pill__paid')
    list_filter = (GovernmentListFilter, 'pay_method', 'city', 'pill__status','pill__paid')
    search_fields = ('name', 'phone', 'pill__pill_number', 'email')
    autocomplete_fields = ('pill',)
    list_editable = ('government',)
    readonly_fields = ('pill_number',)
    
    
    @admin.display(description='Pill Number', ordering='pill__pill_number')
    def pill_number(self, obj):
        return obj.pill.pill_number if obj.pill else '-'
    
    def get_queryset(self, request):
        # Optimize queryset by selecting related objects
        qs = super().get_queryset(request)
        return qs.select_related('pill')


admin.site.register(ProductImage)
admin.site.register(ProductDescription)
@admin.register(PillItem)
class PillItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'user', 'quantity', 'status', 'price_at_sale', 'date_added', 'date_sold', 'get_pill_number']
    list_filter = ['status', 'date_added', 'date_sold', 'size', 'color']
    search_fields = ['product__name', 'user__username', 'user__email', 'pill__pill_number']
    autocomplete_fields = ['product', 'user', 'pill']
    readonly_fields = ['date_added', 'date_sold']
    date_hierarchy = 'date_added'

    @admin.display(description='Pill Number', ordering='pill__pill_number')
    def get_pill_number(self, obj):
        return obj.pill.pill_number if obj.pill else '-'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user', 'pill', 'color')
# admin.site.register(PillAddress)
admin.site.register(PillStatusLog)
admin.site.register(PriceDropAlert)
admin.site.register(SpinWheelResult)
admin.site.register(SpinWheelSettings)
admin.site.register(CartSettings)


@admin.register(OverTaxConfig)
class OverTaxConfigAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'max_products_without_tax', 'tax_amount_per_item', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['max_products_without_tax', 'tax_amount_per_item']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Tax Configuration', {
            'fields': ('max_products_without_tax', 'tax_amount_per_item', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')
    
    def save_model(self, request, obj, form, change):
        # Ensure only one active configuration
        if obj.is_active:
            OverTaxConfig.objects.filter(is_active=True).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(FreeShippingOffer)
class FreeShippingOfferAdmin(admin.ModelAdmin):
    list_display = [
        'description', 'target_type', 'get_target_name', 'start_date', 'end_date', 
        'is_active', 'is_currently_active', 'created_at'
    ]
    list_filter = ['target_type', 'is_active', 'start_date', 'end_date', 'created_at']
    search_fields = ['description', 'category__name', 'subcategory__name', 'brand__name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['category', 'subcategory', 'brand']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('description', 'target_type', 'is_active')
        }),
        ('Target Selection', {
            'fields': ('category', 'subcategory', 'brand'),
            'description': 'Select the target based on the target type chosen above.'
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Currently Active', boolean=True)
    def is_currently_active(self, obj):
        return obj.is_currently_active
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'subcategory', 'brand'
        )






