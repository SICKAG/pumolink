# ModelLink Storage

Storage extension for `sick.modellink.core`.

It provides shared state objects keyed by:

- `primID` (from customData/assetInfo/attribute)
- `detector.reference`

This keeps storage stable across prim path changes (move/rename), as long as `primID`
is stable.

## Injection

Bind targets provided by this extension:

- `ModelLinkSharedStorage`
- `ModelLinkStorageService`

And in linked classes you can inject one of those services and resolve storage with
the current `prim` and detector reference.

## Convenience for current class

`ModelLinkStorageService` also provides:

- `storage_for_current_link(prim)`

It infers the calling class from the Python call stack, then resolves storage as if
`storage_for_link(prim, YourClass)` had been called.

## Robust option without stack inspection

Use explicit owner mapping with `@storage_owner` and resolve from instance:

```python
from injector import inject
from pxr import Usd
from sick.modellink.core import linked
from sick.modellink.storage import ModelLinkStorageService, storage_owner

@linked("Cube")
@storage_owner()
class MyHandler:
    @inject
    def __init__(self, prim: Usd.Prim, storage_service: ModelLinkStorageService):
        self.state = storage_service.storage_for_instance_link(prim, self)
```

You can also map helper classes to another owner class:

```python
@storage_owner(MyHandler)
class MyHelper:
    pass
```
