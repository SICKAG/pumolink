# ModelLinkManager API Documentation

The modellink_manager module provides decorators to link methods to various events and attributes in a model. These decorators facilitate the integration of custom logic with model events and attributes.

## Decorators

1. on_update(f)
- Description: Links a method to the update event
1. on_stop(f)
- Description: Links a method to the stop event.
- Parameters:
    - f (function): The method to be linked.
- Returns: The original method f.

2. on_step(f)
- Description: Links a method to the 'Physics' step event. Requires the modellink.extras extension to be enabled.
- Parameters:
    - f (function): The method to be linked.
- Returns: The original method f.

3. on_event(_id: str | int)
- Description: Links a method to a custom event. Instead of using predefined events like 'on_play', you can use this decorator with a custom event ID.
- Parameters:
    - _id (str | int): A string or integer to identify the event. Strings are converted to integers using modellink.core.type_for.
- Returns: A decorator function that takes a method f and links it to the specified event.

4. usd_attr(path: str, param_name: str | None = None)
- Description: Links a method to a prim attribute. The method is called when the attribute changes, and the changed value is passed to the method.
- Parameters:
    - path (str): The name of the attribute of the prim to be observed.
    - param_name (str | None, optional): The name of the parameter to be passed to the function. Defaults to the path.
- Returns: A decorator function that takes a method f and links it to the specified attribute.

5. linked(*args, enabled: bool = True)
- Description: Links a class to a prim. The correct prim is recognized using 'detection'.
- Parameters:
    - *args: Variable length argument list.
    - enabled (bool, optional): Whether the linking is enabled. Defaults to True.
- Returns: The original class.

### Example Usage
```python
@on_stop
def handle_stop_event():
    print("Stop event triggered")

@on_step
def handle_step_event():
    print("Step event triggered")

@on_event("custom_event")
def handle_custom_event():
    print("Custom event triggered")

@usd_attr("attribute_path")
def handle_attribute_change(value):
    print(f"Attribute changed to {value}")

@linked
class MyModel:
    pass
```
This documentation provides an overview of the decorators available in the `modellink_manager` module and how to use them to link methods and classes to various events and attributes in your model.