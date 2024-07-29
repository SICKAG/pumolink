# Python USD ModelLink (pumolink)
![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/python-injector/injector) 
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.0-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python USD ModelLink is an Omniverse Extension that offers a library to easily develop _kit_ applications.
This library allows you to connect Python classes and OpenUSD Prims using decorators. Corresponding instances of the Python class are created as soon as a corresponding prim is added to the stage. The instance is also removed when the prim is deleted. Attributes can be easily observed. You can easily register for various events. Dependency Injection is also used to be able to use all common Omniverse/OpenUsd objects.

## Installation steps

- Clone this repository 
- Add Path of the `exts` folder to the Extension Manager and enable the extensions `sick.modellink`
![](images/install_extension.mkv)
## Usage
The connection of Python classes and OpenUSD Prims are called _link_. 

### Import from modellink
Import what you need, read the API Documentation for all possibilities.
```python
from modellink import linked, on_update, usd_attr
```
### Define the link
Define which UsdSchema should be connected to your Python class ('Cube', in this case). Links can also be created without UsdSchema, see API documentation.
```python
@linked('Cube')
class MyDevice:
    ...
```

### Injection

If necessary, just have a few Omniverse or OpenUsd objects injected, e.g. the Stage.

Python USD ModelLink uses a library called 'Injector' for dependency injection. For more information see: https://pypi.org/project/injector/

```python
    @inject
    def __init__(self, stage: Usd.Stage ) -> None:
        ...
```

### Events
Event decorators starting with 'on_' and in this example the 'update' event is used. So the name for the decorator is: 'on_update'.
```python
    @on_update
    def update(self, prim: Usd.Prim):
        self.rot += 0.5
        setRotate(prim, Gf.Vec3f(0.0, self.rot, 0.0))
```
### Observe Prim attributes 
You can also simply observe Usd Prim attributes.
```python
    @usd_attr('size')
    def attr_size_change(self, val: float):
        carb.log_info(f"attr_change .size={val}")
```


### Full example
```python
from injector import inject
from modellink import linked, on_update, usd_attr


@linked('Cube')
class MyDevice:

    @inject
    def __init__(self, stage: Usd.Stage ) -> None:
        carb.log_info("init called!")
        self._stage = stage
        self.rot = 0.0

    @on_update
    def update(self, prim: Usd.Prim):
        self.rot += 0.5
        setRotate(prim, Gf.Vec3f(0.0, self.rot, 0.0))

    @usd_attr('size')
    def attr_size_change(self, val: float):
        carb.log_info(f"attr_change .size={val}")

```
### Examples

We provided some examples `sick.modellink.samples`.

#### Handle Events

This sample demonstrates how to use events. The prim will rotate when the 'play' button is pressed
To see it in action:
- create a new 'Cone' prim (not 'Mesh') in the stage
- press the 'play' button to see the events being called
![](images/cone_example.mp4)

<video width="320" height="240" controls>
  <source src="images/cone_example.mp4" type="video/mp4">
</video>

#### Simple 

This sample demonstrates how to create a simple ModelLink.
To see it in action:
- create a new 'Cube' prim (not 'Mesh') in the stage
- press the 'play' button to see the omniverse update event is calling the 'update' function
- change the value of the 'size' attribute of the 'Cube' prim (in the Property Window)
    to see the 'attr_size_change' function being called
![](images/simple.mkv)

#### Detection by custom function

This sample demonstrates how to create a ModelLink using a custom function to detect the prim.
    The function 'my_custom_function' is used to detect the prim to be linked.
    The function should return True if the prim should be linked, otherwise False.
    In this example, the prim is linked if it has an attribute 'id' with value 42.

To see it in action:
- Drag and drop the .usda file contained in '/data/testfiles/' into the stage
![](images/detection_function.mkv)


#### Detection by class 

This sample demonstrates how to create a ModelLink using an information inside the prim
    This information can be stored in the prim's metadata either in 'assetInfo' or in 'customData'.
    The key used to store the information is 'linkedClass', the value is the name of the class to be linked.
    e.g.
        assetInfo = { 
            string linkedClass = "SensorClass"
        }

To see it in action:
- Drag and drop an .usda file contained in '/data/testfiles/' into the stage
![](images/detection_class.mkv)

#### LightBarrier Class

![](images/light_barrier.mkv)

### Most Important Decorators 

>[!NOTE] 
>Do not use these decorators together with @inject. All decorators inject just like @inject


|Decorator|Description|Parameters|
|-|-|-|
| `@linked` | Linked a class to a Prim. The correct prim is recognized using 'detection'. The detection can be specified as an argument to the decorator. This decorator is for classes only. | <ul><li>`@linked` or `@linked()` will activate any prim that contains the entry `linkedClass='yourClass'` in customData or assetInfo.</li><li>`@linked('YourSchema')` will activate any Prim where the Schema is 'YourPrim'</li><li>`@linked(your_function)` will activate any Prim where a function `def your_function(prim: Usd.Prim)->bool` returns True</li></ul>|
| `@usd_attr` | Observes a Prim attribute. The function is called every time the attribute changes. The changed value is passed to the method as argument with the name of the attribute or the name specified in param_name. This decorator is for member functions only. | `@usd_attr('attributeName')`                                 |
| `@on_update` | The function is called by an 'update' event. This decorator is for member functions only.| `@on_update` (only if 'playing') or `@on_update(editmode=True)` (always)|
| `@on_play` | The function is called by a 'play' event. This decorator is for member functions only.|  |
| `@on_pause` | The function is called by a 'pause' event. This decorator is for member functions only.|  |
| `@on_stop` | The function is called by a 'stop' event. This decorator is for member functions only.|  |
| `@on_event` | The function is called by any self named event. This decorator is for member functions only. | `@on_event('my_custom_event_name')` |

### Contribution

We welcome contributions to our open-source GitHub project! Whether it's adding features, fixing bugs, or improving documentation, your help is appreciated. Check out our repository and join our community of contributors. Thank you for your support!
[More infos](CODE_OF_CONDUCT.md)