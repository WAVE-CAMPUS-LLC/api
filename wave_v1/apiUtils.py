def get_form_fields(form_class):
    """
    Get field information from a form class dynamically
    Returns a dictionary with field names and their attributes
    """
    form = form_class()
    fields = {}
    
    for field_name, field in form.fields.items():
        field_info = {
            'type': field.__class__.__name__,
            'required': field.required,
            'label': field.label or field_name.replace('_', ' ').title(),
            'help_text': field.help_text or '',
        }
        
        # Add choices if the field has them
        if hasattr(field, 'choices') and field.choices:
            field_info['choices'] = [
                {'value': choice[0], 'label': choice[1]} 
                for choice in field.choices
            ]
            
        # Add any validators
        if hasattr(field, 'validators') and field.validators:
            field_info['validators'] = [
                validator.__class__.__name__ 
                for validator in field.validators
            ]
            
        # Add min_length and max_length if they exist
        if hasattr(field, 'min_length') and field.min_length:
            field_info['min_length'] = field.min_length
        if hasattr(field, 'max_length') and field.max_length:
            field_info['max_length'] = field.max_length
            
        fields[field_name] = field_info
    
    return fields