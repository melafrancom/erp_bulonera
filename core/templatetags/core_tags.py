from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def replace(value, arg):
    """
    Usage: {{ value|replace:"old,new" }}
    """
    if ',' not in arg:
        return value
    old, new = arg.split(',')
    return value.replace(old, new)


from decimal import Decimal, ROUND_HALF_UP
from django.utils.safestring import mark_safe

@register.filter(is_safe=True)
def price_display(value, mode='compact'):
    """
    Format a decimal number as Argentine currency with split integer and decimal parts.
    Example: 123.456 -> <span class="...">...</span>
    """
    if value is None:
        value = Decimal('0.00')
    
    try:
        # Convert to Decimal and make sure we have exactly 6 decimal places
        dec_val = Decimal(str(value)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError, ArithmeticError):
        dec_val = Decimal('0.000000')
        
    # Split into integer and decimals parts
    val_str = f"{dec_val:f}"
    if '.' in val_str:
        integer_part, decimal_part = val_str.split('.')
    else:
        integer_part, decimal_part = val_str, '000000'
        
    # Format integer part with thousands separators (Argentina: '.' for thousands)
    try:
        int_val = int(integer_part)
        integer_formatted = f"{int_val:,}".replace(',', '.')
    except ValueError:
        integer_formatted = integer_part
        
    # Clean up trailing zeros from the decimal part, but keep at least 2 decimals!
    # E.g., "135000" -> "135", "500000" -> "5", "000000" -> "00"
    stripped_decimal = decimal_part.rstrip('0')
    if len(stripped_decimal) < 2:
        stripped_decimal = stripped_decimal.ljust(2, '0')
        
    size_class = "price-display--hero" if mode == 'hero' else "price-display--compact"
    
    html = (
        f'<span class="price-display {size_class}" aria-label="$ {integer_formatted},{stripped_decimal}">'
        f'<span class="price-display__symbol">$</span>'
        f'<span class="price-display__integer">{integer_formatted}</span>'
        f'<span class="price-display__separator">,</span>'
        f'<span class="price-display__decimals">{stripped_decimal}</span>'
        f'</span>'
    )
    return mark_safe(html)

