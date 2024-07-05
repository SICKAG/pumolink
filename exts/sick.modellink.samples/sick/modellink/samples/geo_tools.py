from pxr import Usd, UsdGeom, Gf


# --------------------------------------------------.
# Set Rotate.
# --------------------------------------------------.
def setRotate(prim: Usd.Prim, rV: Gf.Vec3f):
    if prim is None:
        return

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