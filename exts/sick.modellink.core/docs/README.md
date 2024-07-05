# ModelLink Core

This library allows you to connect Python classes and OpenUSD Prims using decorators. 
Corresponding instances of the Python class are created as soon as a corresponding prim is added to the stage. 
The instance is also removed when the prim is deleted. Attributes can be easily observed. 
You can easily register for various events. Dependency Injection is also used to be able to use all common Omniverse/OpenUsd objects.

## Example Code

