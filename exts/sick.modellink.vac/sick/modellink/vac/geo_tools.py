from pxr import Usd, UsdGeom, Gf
import carb

def hasRotate(prim: Usd.Prim) -> bool:

    if not prim or not prim.IsA(UsdGeom.Xformable):
        return False

    xformable = UsdGeom.Xformable(prim)
    xform_ops = xformable.GetOrderedXformOps()

    for op in xform_ops:
        if op.GetOpType() in [UsdGeom.XformOp.TypeRotateXYZ, UsdGeom.XformOp.TypeRotateXZY,
                              UsdGeom.XformOp.TypeRotateYXZ, UsdGeom.XformOp.TypeRotateYZX,
                              UsdGeom.XformOp.TypeRotateZXY, UsdGeom.XformOp.TypeRotateZYX]:
            return True
        elif op.GetOpType() == UsdGeom.XformOp.TypeOrient:
            return False
    return False


def quaternion_to_rotate(prim):

    xformable = UsdGeom.Xformable(prim)
    xform_ops = xformable.GetOrderedXformOps()
    xformable.ClearXformOpOrder()

    for xform_op in xform_ops:
        if xform_op.GetOpType() == UsdGeom.XformOp.TypeOrient:
            
            #quaternion = xform_op.Get()
            # rotation_matrix = Gf.Matrix4d().SetRotate(quaternion)
            # rotation_euler_angles = Gf.Matrix3d(quaternion).ExtractRotation().GetAngles()
            #if not hasRotate(prim):
            #   rotate_op = xformable.AddRotateXYZOp()
            # rotate_op.Set(rotation_euler_angles)
            xform_ops.remove(xform_op)
            # return

    if not hasRotate(prim):
        xformable.AddRotateXYZOp()
        

# --------------------------------------------------.
# Set Rotate.
# --------------------------------------------------.
def setRotate(prim: Usd.Prim, rV: Gf.Vec3f):
    if prim is None:
        return
    
    if not hasRotate(prim):
        carb.log_warn("Prim does not have a rotate attribute. Creating one.")
        quaternion_to_rotate(prim)

    # Get rotOrder.
    # If rotation does not exist, rotOrder = UsdGeom.XformCommonAPI.RotationOrderXYZ.
    xformAPI = UsdGeom.XformCommonAPI(prim)
    time_code = Usd.TimeCode.Default()
    translation, rotation, scale, pivot, rotOrder = xformAPI.GetXformVectors(time_code)

    # Convert rotOrder to "xformOp:rotateXYZ" etc.
    t = xformAPI.ConvertRotationOrderToOpType(rotOrder)
    rotateAttrName = "xformOp:" + UsdGeom.XformOp.GetOpTypeToken(t)

    # Set rotate.
    rotate = prim.GetAttribute(rotateAttrName).Get()
    if rotate != None:
        # Specify a value for each type.
        if type(rotate) == Gf.Vec3f:
            prim.GetAttribute(rotateAttrName).Set(Gf.Vec3f(rV))
        elif type(rotate) == Gf.Vec3d:
            prim.GetAttribute(rotateAttrName).Set(Gf.Vec3d(rV))
    else:
        # xformOpOrder is also updated.
        xformAPI.SetRotate(Gf.Vec3f(rV), rotOrder)