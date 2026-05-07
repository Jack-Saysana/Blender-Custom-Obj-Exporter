import bpy
import mathutils
import math
# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
entity = bpy.data.texts["entity.py"].as_module()
scene = bpy.data.texts["scene.py"].as_module()

class ExportRiggedObj(Operator, ExportHelper):
    """Save a Wavefront OBJ file with rigging and animation data"""
    bl_idname = "rigged_obj.export"
    bl_label = "Export OBJ"

    # ExportHelper mixin class uses this
    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return entity.serialize_single_entity(self.filepath)


class ExportScene(Operator, ExportHelper):
    """Save a Wavefront OBJ file with all scene data"""
    bl_idname = "scene.export"
    bl_label = "Export Scene"

    directory: StringProperty(
        name="Output Directory",
        description="Directory to export chunk files into",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        return scene.serialize_scene(self.directory)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Only needed if you want to add into a dynamic menu
def menu_func_export_entity(self, context):
    self.layout.operator(ExportRiggedObj.bl_idname, text="Wavefront (rigged) (.obj)")

def menu_func_export_scene(self, context):
    self.layout.operator(ExportScene.bl_idname, text="Wavefront (scene) (.obj)")

def register():
    bpy.utils.register_class(ExportRiggedObj)
    bpy.utils.register_class(ExportScene)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_entity)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_scene)

def unregister():
    bpy.utils.unregister_class(ExportRiggedObj)
    bpy.utils.unregister_class(ExportScene)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_scene)

if __name__ == "__main__":
    register()
