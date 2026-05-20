#TODO : Rethink everythink, there is perhaps some redundancy

***THIS IS UNDER CONSTRUCTION***

# ModelLink VAC

Virtual Automation Controller (VAC) - A collection of linked classes for Omniverse that provide automation components for motion control, data conversion, communication, and visual effects in USD scenes.

## Table of Contents

- [Overview](#overview)
- [VAC Classes](#vac-classes)
  - [Motion Control](#motion-control)
  - [Data Conversion](#data-conversion)
  - [Communication & Events](#communication--events)
  - [Visual & Output](#visual--output)
  - [Media Transmission](#media-transmission)
  - [Utilities](#utilities)

## Overview

The VAC extension provides a modular system of linked classes that can be attached to USD prims to add interactivity and automation. Each class manages specific USD attributes (prefixed with `vac:`) and responds to changes through the ModelLink event system.

### ModelLink Integration

All VAC classes are **ModelLink-enabled** via the `@linked` decorator. This means:
- Each class is automatically instantiated by ModelLink when the corresponding prim is loaded
- Changes to `vac:*` attributes are tracked and trigger callbacks via the `@usd_attr()` decorator
- Periodic updates are handled by the `@on_update()` decorator
- Classes use dependency injection to access USD primitives and stages

### Automation Factory Pattern

The core intention of VAC is to enable building **complete automation factories and control systems** using only:
1. **USD scene structure** - Define your 3D model hierarchy in USD
2. **VAC linked classes** - Attach VAC components to prims via `linkedClass` metadata
3. **`vac:*` attributes** - Configure components and establish data flow via USD attributes and relationships

This allows engineers to:
- **Design complex automation logic** entirely within Omniverse USD
- **Avoid custom Python code** for most use cases
- **Create reusable automation templates** as USD assets
- **Enable non-programmers** to build automation systems through visual USD editing
- **Leverage USD's powerful composition features** (references, variants, layers) for scalability

**Example Workflow:**
```
1. Create USD scene with automation components
2. Add linkedClass = "Rotor" to motor prim
3. Add linkedClass = "Coupler" to converter prim
4. Connect vac:* attributes and relationships
5. System automatically wires everything through ModelLink
→ Complete automation system, no Python required
```

---

## VAC Classes

### Motion Control

#### **Mover**
Moves a target prim along a specified direction based on a numeric value.

**File:** `mover.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:direction` | Vec3d | (1, 0, 0) | Direction vector for movement |
| `vac:offset` | Float | 0.0 | Offset applied to the value |
| `vac:range` | (Float, Float) | (0.0, 1.0) | Min/max clamp range for scaled value |
| `vac:factor` | Float | 1.0 | Multiplier applied to input value |
| `vac:clamp` | Bool | True | Whether to clamp value to range |
| `vac:value` | Float | 0.0 | Input value triggering movement (watched) |

**Relationships:**
- `vac:target` - Target prims to move

**Methods:**
- `move(value: float)` - Updates movement based on input value

---

#### **Rotor**
Rotates a target prim around a specified axis based on a numeric value.

**File:** `rotor.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:axis` | Vec3d | (0, 0, 1) | Rotation axis (normalized) |
| `vac:offset` | Float | 0.0 | Offset applied to the angle |
| `vac:range` | (Float, Float) | (0.0, 360.0) | Min/max clamp range for angle in degrees |
| `vac:factor` | Float | 1.0 | Multiplier applied to input value |
| `vac:clamp` | Bool | True | Whether to clamp angle to range |
| `vac:value` | Float | 0.0 | Input angle value (watched) |

**Relationships:**
- `vac:target` - Target prims to rotate

**Methods:**
- `rotate(value: float)` - Updates rotation based on input angle value

---

### Data Conversion

#### **Coupler**
Converts between different data types (bool, int, float) with scaling and thresholding.

**File:** `coupler.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:format` | String | "real" | Output format: "bool", "int", or "real" |
| `vac:bool_values` | (Float, Float) | (0.0, 1.0) | Values for false/true when converting to float |
| `vac:factor` | Float | 1.0 | Multiplier for numeric conversions |
| `vac:threshold` | Float | 0.0 | Threshold for float-to-bool conversion |
| `vac:on` | Bool | - | Boolean input (watched) |
| `vac:select` | Int | - | Integer input (watched) |
| `vac:value` | Float | - | Float input (watched) |

**Relationships:**
- `stateReceiver` - Target prims receiving converted output

**Methods:**
- `convert_bool(input_bool: bool)` - Converts boolean to configured format
- `convert_int(input_int: int)` - Converts integer to configured format
- `convert_real(input_real: float)` - Converts float to configured format

---

### Communication & Events

#### **MqttCoupler**
Bidirectional MQTT integration for sending and receiving automation values.

**File:** `mqtt_coupler.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:broker` | String | "localhost" | MQTT broker hostname/IP |
| `vac:port` | Int | 1883 | MQTT broker port |
| `vac:topic` | String | "vac/default" | MQTT topic for publishing/subscribing |
| `vac:value` | Float | - | Value to publish to MQTT topic (watched) |

**Relationships:**
- `stateReceiver` - Target prims receiving MQTT messages

**Methods:**
- `publish_value(value: float)` - Publishes value to MQTT topic
- `set_topic(new_topic: str)` - Changes subscription topic
- `update(prim: Prim)` - Processes received MQTT messages (internal)

**Behavior:**
- Connects to MQTT broker on initialization
- Subscribes to configured topic
- Incoming messages set `vac:value` on receiver prims
- Outgoing values published when `vac:value` changes

---

#### **LightBarrier** (LightBarrierClass)
Ray-based light barrier that detects obstructions and sends boolean signals.

**File:** `light_barrier.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| (Transforms) | - | - | Uses prim's local X-axis as ray direction |

**Relationships:**
- `stateReceiver` - Target prim receiving boolean hit detection result

**Methods:**
- `send_signal(enabled: bool)` - Sends detection result
- `update(prim: Prim)` - Performs ray query each frame

**Behavior:**
- Casts a ray from prim origin in local +X direction (0-100 units)
- Sends `vac:on = True` if ray hits something, `False` if clear
- Uses Omniverse raycast query interface

---

### Visual & Output

#### **Monitor**
Dynamically creates and binds materials with video textures for visualization.

**File:** `monitor.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:mesh` | String | - | Name of target mesh prim for material binding |
| `vac:sourcename` | String | - | Source identifier for dynamic texture (used in `dynamic://{sourcename}`) |

**Methods:**
- `_setup_material()` - Creates OmniPBR material with dynamic texture (internal)

**Behavior:**
- Creates material at `{prim_path}/Material`
- Sets up OmniPBR shader with diffuse dynamic texture
- Binds material to specified mesh prim on initialization

---

#### **Enabler**
Shows/hides target prims via visibility attribute.

**File:** `enabler.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:on` | Bool | False | Visibility state (watched) |

**Relationships:**
- `vac:target` - Target prims to show/hide

**Methods:**
- `enable_light(enabled: bool)` - Sets visibility of targets

**Behavior:**
- Sets targets to "inherited" visibility if enabled
- Sets targets to "invisible" if disabled

---

### Media Transmission

#### **Transmitter**
Streams camera feeds or video files as dynamic textures to receiver materials in the scene.

**File:** `transmitter.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:type` | String | "camera" | Source type: "camera" or "movie" |
| `vac:path` | String | - | USD camera path (for type="camera") or file path (for type="movie") |
| `vac:texture_size` | Int2 | (512, 512) | Texture size in pixels as (width, height) |

**Relationships:**
- `vac:image_receiver` - Target prims that receive the texture material

**Methods:**
- `_initialize_capture()` - Sets up capture based on type (internal)
- `_bind_receivers(texture_name: str)` - Binds material to receiver prims (internal)

**Behavior:**
- **Camera mode**: Uses Replicator to capture from USD camera with configurable texture size
- **Movie mode**: Reads video file frame-by-frame via OpenCV, loops on end
- Dynamically creates OmniPBR material with diffuse texture for each receiver
- Texture updates in real-time as new frames arrive
- Supports configuration changes via attribute updates

**Example Configuration (USD):**
```usda
def Xform "MediaServer" (
    assetInfo = { string linkedClass = "Transmitter" }
)
{
    custom string vac:type = "camera"
    custom string vac:path = "/World/BroadcastCamera"
    custom rel vac:image_receiver = [</World/Monitor1/Mesh>, </World/Monitor2/Mesh>]
}
```

---

### Utilities

#### **Switcher**
Routes signals to one of multiple target prims based on selection index.

**File:** `switcher.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:select` | Int | - | Index selecting which target to toggle (watched) |

**Relationships:**
- `vac:target` - Array of target prims (switches between them)

**Methods:**
- `select_target(select_index: int)` - Toggles state on selected target

**Behavior:**
- Uses `select_index` to pick target from `vac:target` relationship
- Toggles boolean state (0/1) on selected target each call

---

#### **WaveGenerator**
Generates periodic waveforms (sine, square, triangle, sawtooth) for continuous control signals.

**File:** `wave_generator.py`

**USD Attributes:**
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `vac:amplitude` | Float | 1.0 | Wave amplitude (peak magnitude) |
| `vac:frequency` | Float | 1.0 | Wave frequency in cycles per second |
| `vac:phase` | Float | 0.0 | Phase offset in radians |
| `vac:type` | String | "sin" | Wave type: "sin", "square", "triangle", "sawtooth" |

**Relationships:**
- `stateReceiver` - Target prims receiving generated wave value

**Methods:**
- `update(prim: Prim)` - Generates next waveform sample (called each frame)

**Behavior:**
- Updates internal time at ~60 FPS (dt=0.016s)
- Computes waveform value based on time, frequency, and phase
- Sends computed value to receiver prims via `vac:value`

---
