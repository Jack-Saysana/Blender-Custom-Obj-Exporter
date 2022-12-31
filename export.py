import bpy
import mathutils
import math
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
next_id = -1
def traverse_tree(world_mat, bone, parent_id, level, obj_file):
    world_coords = world_mat @ bone.head_local
    global next_id
    next_id += 1
    cur_id = next_id
    print("# %s" % (bone.name), file=obj_file)
    print("b %f %f %f %d %d\n" %(world_coords[1], world_coords[2], world_coords[0], parent_id, len(bone.children)), file=obj_file)
    bones.append(bone.name)
    for child in bone.children:
        traverse_tree(world_mat, child, cur_id, level + 1, obj_file)

def write_data(filepath):
    global next_id
    next_id = -1
    obj_file = open(filepath, 'w', encoding='utf-8')
    mtl_file = open(filepath[0:-4] + ".mtl", 'w', encoding='utf-8')
    
    print("mtllib %s.mtl" % bpy.path.basename(filepath[0:-4]), file=obj_file)
    for object in bpy.data.objects:
        if object.type == 'ARMATURE':
            for bone in object.data.bones:
                if bone.parent == None:
                    traverse_tree(object.matrix_world, bone, -1, 0, obj_file)
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
                        
                world_coords = object.matrix_world @ vertex.co
                print("v %f %f %f " % (world_coords[1], world_coords[2], world_coords[0]), end = "", file=obj_file)
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
            for uv in mesh_data.uv_layers.active.data:
                if exists(uvs, uv.uv, 2) == False:
                    uvs.append(uv.uv)
                    print("vt %f %f" % (uv.uv[0], uv.uv[1]), file=obj_file)
                    
            for polygon in mesh_data.polygons:
                if exists(normals, polygon.normal, 3) == False:
                    normals.append(polygon.normal)
                    print("vn %f %f %f" % (polygon.normal[1], polygon.normal[2], polygon.normal[0]), file=obj_file)

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
        keyframe_chains = {}
        for fcurve in action.fcurves:
            fcurve_data = fcurve.data_path.split("[\"")[1].split("\"]")
            for point in fcurve.keyframe_points:
                chain_id = fcurve_data[0] + "\n" + fcurve_data[1]
                if chain_id not in keyframe_chains:
                    keyframe_chains[chain_id] = { "frame":point.co[0], "queue":{} }
                if str(point.co[0]) not in keyframe_chains[chain_id]["queue"]:
                    if fcurve_data[1] == ".rotation_quaternion":
                        keyframe_chains[chain_id]["queue"][str(point.co[0])] = [ 0.0, 0.0, 0.0, 0.0 ]
                    else:
                        keyframe_chains[chain_id]["queue"][str(point.co[0])] = [ 0.0, 0.0, 0.0 ]

                keyframe_chains[chain_id]["queue"][str(point.co[0])][fcurve.array_index] = point.co[1]
                
        print("\n# %s" % (action.name), file=obj_file)
        print("a %d" % (action.frame_range[1] - action.frame_range[0] + 1), file=obj_file)
        for chain_id in keyframe_chains:
            chain_data = chain_id.split("\n")
            
            print("# %s" % (chain_data[0]), file=obj_file)
            if chain_data[1] == ".location":
                print("cl %d" % (bones.index(chain_data[0])), file=obj_file)
            elif chain_data[1] == ".rotation_quaternion":
                print("cr %d" % (bones.index(chain_data[0])), file=obj_file)
            elif chain_data[1] == ".scale":
                print("cs %d" % (bones.index(chain_data[0])), file=obj_file)

            for keyframe in keyframe_chains[chain_id]["queue"]:
                offset = keyframe_chains[chain_id]["queue"][keyframe]
                
                local_matrix = bpy.data.armatures[0].bones[chain_data[0]].matrix_local
                local_point_mat = mathutils.Matrix([[local_matrix[0][0], local_matrix[0][1], local_matrix[0][2]], [local_matrix[1][0], local_matrix[1][1], local_matrix[1][2]], [local_matrix[2][0], local_matrix[2][1], local_matrix[2][2]]]).to_4x4()
            
                transformation_mat = mathutils.Matrix()
                world_offset = [ -1.0, -1.0, -1.0, -1.0 ]
                if chain_data[1] == ".location":
                    transformation_mat = mathutils.Matrix([[1, 0, 0, offset[0]], [0, 1, 0, offset[1]], [0, 0, 1, offset[2]], [0, 0, 0, 1]]);
                    world_mat = local_point_mat @ transformation_mat
                    world_offset[0] = world_mat[0][3]
                    world_offset[1] = world_mat[1][3]
                    world_offset[2] = world_mat[2][3]
                elif chain_data[1] == ".rotation_quaternion":
                    local_offset_vector = mathutils.Vector((offset[1], offset[2], offset[3], 1))
                    world_offset_vector = local_point_mat @ local_offset_vector
                    
                    world_offset[0] = offset[0]
                    world_offset[1] = world_offset_vector[0]
                    world_offset[2] = world_offset_vector[1]
                    world_offset[3] = world_offset_vector[2]
                elif chain_data[1] == ".scale":
                    world_offset_vector = local_point_mat @ mathutils.Vector((offset[0] - 1.0, offset[1] - 1.0, offset[2] - 1.0, 1.0))
                    
                    world_offset[0] = world_offset_vector[0] + 1.0
                    world_offset[1] = world_offset_vector[1] + 1.0
                    world_offset[2] = world_offset_vector[2] + 1.0

                if chain_data[1] == ".rotation_quaternion":
                    print("kp %d %f %f %f %f" % (int(float(keyframe)), world_offset[2], world_offset[3], world_offset[1], world_offset[0]), file=obj_file)
                else:
                    print("kp %d %f %f %f" % (int(float(keyframe)), world_offset[1], world_offset[2], world_offset[0]), file=obj_file)

    obj_file.close()
    mtl_file.close()

    return {'FINISHED'}

class ExportRiggedObj(Operator, ExportHelper):
    """Save a Wavefront OBJ file with rigging and animation data"""
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
