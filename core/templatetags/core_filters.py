from django import template
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder

register = template.Library()

@register.filter(name='to_json')
def to_json(value):
    import json
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder))

@register.filter(name='format_date')
def format_date(date_str):
    if not date_str:
        return 'N/A'
    
    # Se já for um objeto date/datetime, formata direto
    if hasattr(date_str, 'strftime'):
        return date_str.strftime('%d/%m/%Y')
        
    try:
        if 'T' in str(date_str):
            date_part = str(date_str).split('T')[0]
        else:
            date_part = str(date_str)
            
        parts = date_part.split('-')
        if len(parts) == 3:
            year, month, day = parts
            return f'{day}/{month}/{year}'
    except:
        pass
        
    return str(date_str)
