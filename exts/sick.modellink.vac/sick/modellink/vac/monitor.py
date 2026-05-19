from injector import inject
from pxr import Usd,  UsdShade
from sick.modellink.core.modellink_manager import linked, usd_attr
import carb


@linked(cluster="VAC")
class Monitor:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        

    def _change_dynamic_texture(self, source_name: str) -> None:
        
        # Try to get shader via relationship (vac:shaderpath as rel)
        shader_rel = self.prim.GetRelationship("vac:shaderpath")
        shader_prim = None
        
        if shader_rel:
            # Get targets from relationship
            targets = shader_rel.GetTargets()
            if targets:
                shader_prim = self.stage.GetPrimAtPath(targets[0])
        
        # Fallback: try as attribute (string path)
        if not shader_prim:
            shader_path_attr = self.prim.GetAttribute("vac:shaderpath")
            if shader_path_attr:
                shader_path_str = shader_path_attr.Get()
                if shader_path_str:
                    shader_prim = self.stage.GetPrimAtPath(shader_path_str)
        
        if not shader_prim or not shader_prim.IsValid():
            carb.log_error("Could not resolve shader prim from vac:shaderpath")
            return
        
        shader = UsdShade.Shader(shader_prim)
        if not shader:
            carb.log_error(f"Could not create shader from prim: {shader_prim.GetPath()}")
            return
        
        input_name_attr = self.prim.GetAttribute("vac:inputname")
        input_name = input_name_attr.Get() if input_name_attr else "diffuse_texture"

        dynamic_texture_path = f"dynamic://{source_name}"
        diffuse_texture_input = shader.GetInput(input_name)
        if diffuse_texture_input:
            diffuse_texture_input.Set(dynamic_texture_path)

    @usd_attr("vac:source_name;vac:shaderpath;vac:inputname")
    def source_name(self):
        source_name = self.prim.GetAttribute("vac:source_name").Get()
        self._change_dynamic_texture(source_name)

