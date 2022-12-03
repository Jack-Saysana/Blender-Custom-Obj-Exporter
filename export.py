import bpy
# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

def exists(arr, target, size):
    for elem in arr:
        match = True
        for i in range (0, size):
            if elem[i] != target[i]:
                match = False
                break
        if match == True:
            return True
    return False

def get_index(arr, target, size):
    for i in range(0, len(arr)):
        match = True
        for j in range(0, size):
            if (arr[i][j] != target[j]):
                match = False
                break
        if match == True:
            return i
    return -1

def compare_group(group):
    return group.weight

bones = []
def traverse_tree(bone, level, obj_file):
    for i in range(0, level):
        print(" ", end="")
    print("b %f %f %f %d" %(bone.head_local[0], bone.head_local[1], bone.head_local[2], len(bone.children)), file=obj_file)
    bones.append(bone.name)
    for child in bone.children:
        traverse_tree(child, level + 1, obj_file)

def write_data(filepath):
    obj_file = open(filepath, 'w', encoding='utf-8')
    mtl_file = open(filepath[0:-4] + ".mtl", 'w', encoding='utf-8')
    
    print("mtllib %s.mtl" % bpy.path.basename(filepath[0:-4]), file=obj_file)
    for object in bpy.data.objects:
        if object.type == 'ARMATURE':
            for bone in object.data.bones:
                if bone.parent == None:
                    traverse_tree(bone, 0, obj_file)
        if object.type == 'MESH':
            mesh_data = object.data
            group_list = object.vertex_groups
            normals = []
            uvs = []
            print("o %s" % (object.name), file=obj_file)
            for vertex in mesh_data.vertices:
                groups = []
                for group in vertex.groups:
                    groups.append(group)
                groups.sort(key=compare_group, reverse=True)
                
                used = []
                for i in range(0, 4):
                    if i < len(groups):
                        used.append(groups[i])
                    else:
                        used.append(-1)
                        
                print("v %f %f %f " % (vertex.co[0], vertex.co[1], vertex.co[2]), end = "", file=obj_file)
                for i in range(0, len(used)):
                    if (i < len(used) - 1):
                        if (used[i] != -1):
                            print("%d:%f" % (bones.index(group_list[used[i].group].name), used[i].weight), end=" ", file=obj_file)
                        else:
                            print("-1:-1.0", end=" ", file=obj_file)
                    else:
                        if (used[i] != -1):
                            print("%d:%f" % (bones.index(group_list[used[i].group].name), used[i].weight), end="\n", file=obj_file)
                        else:
                            print("-1:-1.0", end="\n", file=obj_file)
#                print("v %f %f %f" % (vertex.co[0], vertex.co[1], vertex.co[2]), file=obj_file)
            for uv in mesh_data.uv_layers.active.data:
                if exists(uvs, uv.uv, 2) == False:
                    uvs.append(uv.uv)
                    print("vt %f %f" % (uv.uv[0], uv.uv[1]), file=obj_file)
                    
            for polygon in mesh_data.polygons:
                if exists(normals, polygon.normal, 3) == False:
                    normals.append(polygon.normal)
                    print("vn %f %f %f" % (polygon.normal[0], polygon.normal[1], polygon.normal[2]), file=obj_file)

            material = object.active_material
            if material is not None:
                for link in material.node_tree.links:
                    #Look for current output material of object
                    if (link.to_node.bl_idname == 'ShaderNodeOutputMaterial' and link.to_node.is_active_output and link.to_socket == link.to_node.inputs[0]):
                        print("newmtl %s" % (material.name), file=mtl_file)
                        #Check if output material uses bsdf principled
                        if (link.from_node.bl_idname == 'ShaderNodeBsdfPrincipled'):
                            #Extract textures (if they exist) from bsdf principled
                            for input in link.from_node.inputs:
                                if (input.name == 'Base Color'):
                                    for l in material.node_tree.links:
                                        if (l.to_socket == input and l.from_node.bl_idname == 'ShaderNodeTexImage'):
                                            print("map_Kd %s" % (bpy.path.basename(l.from_node.image.filepath)), file=mtl_file)
                                            break
                                elif (input.name == 'Specular'):
                                    for l in material.node_tree.links:
                                        if (l.to_socket == input and l.from_node.bl_idname == 'ShaderNodeTexImage'):
                                            print("map_Ks %s" % (bpy.path.basename(l.from_node.image.filepath)), file=mtl_file)
                                            break
                    break
                print("usemtl %s" % (material.name), file=obj_file)
                
            for polygon in mesh_data.polygons:
                print("f", end =" ", file=obj_file)
                for index in range(polygon.loop_start, polygon.loop_start + polygon.loop_total):
                    if index < polygon.loop_start + polygon.loop_total - 1:
                        print("%d/%d/%d" % (mesh_data.loops[index].vertex_index + 1, get_index(uvs, mesh_data.uv_layers.active.data[index].uv, 2) + 1, get_index(normals, polygon.normal, 3) + 1), end =" ", file=obj_file)
                    else:
                        print("%d/%d/%d" % (mesh_data.loops[index].vertex_index + 1, get_index(uvs, mesh_data.uv_layers.active.data[index].uv, 2) + 1, get_index(normals, polygon.normal, 3) + 1), end ="", file=obj_file)
                print("", file=obj_file)

    for action in bpy.data.actions:
        action_bones = {}
        for fcurve in action.fcurves:
            fcurve_data = fcurve.data_path.split("[\"")[1].split("\"]")
            if fcurve_data[0] not in action_bones:
                action_bones[fcurve_data[0]] = {}
                    
            for point in fcurve.keyframe_points:
                if str(point.co[0]) not in action_bones[fcurve_data[0]]:
                    action_bones[fcurve_data[0]][str(point.co[0])] = {}
                if fcurve_data[1] not in action_bones[fcurve_data[0]][str(point.co[0])]:
                    if fcurve_data[1] == ".rotation_quaternion":
                        action_bones[fcurve_data[0]][str(point.co[0])][fcurve_data[1]] = [ 0.0, 0.0, 0.0, 0.0 ]
                    else:
                        action_bones[fcurve_data[0]][str(point.co[0])][fcurve_data[1]] = [ 0.0, 0.0, 0.0 ]
                action_bones[fcurve_data[0]][str(point.co[0])][fcurve_data[1]][fcurve.array_index] = point.co[1]
        
        print("a %s" % (action.name), file=obj_file)
        for bone in action_bones:
            bone_id = bones.index(bone)
            for frame in action_bones[bone]:
                for attrib in action_bones[bone][frame]:
                    offset = action_bones[bone][frame][attrib]
                    if attrib == ".location":
                        print("l %d %d %f %f %f" % (bone_id, float(frame), offset[0], offset[1], offset[2]), file=obj_file)
                    elif attrib == ".rotation_quaternion":
                        print("r %d %d %f %f %f %f" % (bone_id, float(frame), offset[0], offset[1], offset[2], offset[3]), file=obj_file)
                    else:
                        print("s %d %d %f %f %f" % (bone_id, float(frame), offset[0], offset[1], offset[2]), file=obj_file)
    obj_file.close()
    mtl_file.close()

    return {'FINISHED'}

class ExportRiggedObj(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "rigged_obj.export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export OBJ"

    # ExportHelper mixin class uses this
    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return write_data(self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportRiggedObj.bl_idname, text="Wavefront (rigged) (.obj)")


def register():
    bpy.utils.register_class(ExportRiggedObj)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportRiggedObj)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
