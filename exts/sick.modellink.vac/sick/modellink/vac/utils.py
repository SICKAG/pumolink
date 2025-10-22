import carb
from pxr import Usd, Gf, UsdGeom


def set_translation_on_xform(xform: UsdGeom.Xformable, position: Gf.Vec3d):
    """Safely set translation on an Xform, adding translate op if necessary."""
    ops = xform.GetOrderedXformOps() or []
    translate_op = None
    for op in ops:
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            translate_op = op
            break
    if not translate_op:
        # Add a translate op if none exists
        translate_op = xform.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
    
    # Set the value based on the op's precision
    if translate_op.GetPrecision() == UsdGeom.XformOp.PrecisionFloat:
        translate_op.Set(Gf.Vec3f(position), Usd.TimeCode.Default())
    else:
        translate_op.Set(position, Usd.TimeCode.Default())


def set_rotation_on_xform(xform: UsdGeom.Xformable, rotation: Gf.Rotation):
    """Safely set rotation on an Xform, adding rotate op if necessary."""
    ops = xform.GetOrderedXformOps() or []
    rotate_op = None
    for op in ops:
        if op.GetOpType() == UsdGeom.XformOp.TypeOrient:
            rotate_op = op
            break
    if not rotate_op:
        # Add a rotate op if none exists
        rotate_op = xform.AddOrientOp(UsdGeom.XformOp.PrecisionDouble)
    
    # Set the value based on the op's precision
    quat = rotation.GetQuat()
    if rotate_op.GetPrecision() == UsdGeom.XformOp.PrecisionFloat:
        rotate_op.Set(Gf.Quatf(quat), Usd.TimeCode.Default())
    else:
        rotate_op.Set(Gf.Quatd(quat), Usd.TimeCode.Default())