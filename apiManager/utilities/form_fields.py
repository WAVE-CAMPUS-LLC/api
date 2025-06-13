def get_form_fields(form_class):
    form = form_class()
    fields = {}
    
    for name, field in form.fields.items():
        field_info = {
            "label": str(field.label) if field.label else "",
            "required": field.required,
            "widget": field.widget.__class__.__name__,
            "initial": field.initial,
            "help_text": str(field.help_text) if field.help_text else "",
            "type": field.__class__.__name__,
        }
        
        if hasattr(field, "choices") and field.choices:
            # Convert choices to JSON-serializable format
            choices = []
            for value, label in field.choices:
                choices.append({
                    "value": value,
                    "label": str(label)
                })
            field_info["choices"] = choices
        
        fields[name] = field_info
    return fields