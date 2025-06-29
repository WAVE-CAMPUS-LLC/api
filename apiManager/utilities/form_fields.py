def get_form_fields(form_class):
    form = form_class()
    fields = {}

    for name, field in form.fields.items():
        try:
            # Safely handle initial value - convert to string if not JSON serializable
            initial_value = field.initial
            if initial_value is not None:
                # Convert functions, lists, etc. to JSON-safe format
                if callable(initial_value):
                    initial_value = None  # Don't serialize functions
                elif hasattr(initial_value, "__iter__") and not isinstance(
                    initial_value, (str, dict)
                ):
                    initial_value = list(initial_value) if initial_value else []

            field_info = {
                "label": str(field.label) if field.label else "",
                "required": field.required,
                "widget": field.widget.__class__.__name__,
                "initial": initial_value,
                "help_text": str(field.help_text) if field.help_text else "",
                "type": field.__class__.__name__,
            }

            if hasattr(field, "choices") and field.choices:
                # Convert choices to JSON-serializable format
                choices = []
                try:
                    for choice_item in field.choices:
                        if len(choice_item) >= 2:
                            value, label = choice_item[0], choice_item[1]
                            choices.append(
                                {
                                    "value": str(value) if value is not None else "",
                                    "label": str(label) if label is not None else "",
                                }
                            )
                    field_info["choices"] = choices
                except Exception as e:
                    print(f"Error processing choices for field {name}: {e}")
                    field_info["choices"] = []

            fields[name] = field_info
        except Exception as e:
            print(f"Error processing field {name}: {e}")
            # Fallback with minimal info
            fields[name] = {
                "label": str(name).replace("_", " ").title(),
                "required": False,
                "widget": "TextInput",
                "initial": None,
                "help_text": "",
                "type": "CharField",
            }

    return fields
