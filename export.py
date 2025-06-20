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

def split_extensions(name):
    extensions = []
    index = len(name) - 1
    end = len(name)
    extension = ""
    r_name = name[::-1]
    for i in range(0, len(name)):
        if r_name[i] == '.':
            extensions.append(name[index + 1:end:1])
            end = index
        index = index - 1
    name = name[0:end:1]
    split = {
        "name": name,
        "extensions": extensions
    }
    return split

def compare_group(group):
    return group.weight

# matrix to transform blender world coordinates to opengl's coordinate system
opengl_mat = mathutils.Matrix([(0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)])

bones = []
next_id = -1
def traverse_tree(parent_mat, bone, parent_id, obj_file):
    global world_mat
    global next_id
    next_id += 1
    cur_id = next_id
    world_head = opengl_mat @ (world_mat @ bone.head_local)
    world_tail = opengl_mat @ (world_mat @ bone.tail_local)
    parent_mat = parent_mat @ bone.matrix
    # Armature space to world space to opengl space
    opengl_bone_mat = opengl_mat @ (world_mat.to_3x3() @ parent_mat)
    bone_basis_x = mathutils.Vector((opengl_bone_mat[0][0], opengl_bone_mat[1][0], opengl_bone_mat[2][0])).normalized()
    bone_basis_y = mathutils.Vector((opengl_bone_mat[0][1], opengl_bone_mat[1][1], opengl_bone_mat[2][1])).normalized()
    bone_basis_z = mathutils.Vector((opengl_bone_mat[0][2], opengl_bone_mat[1][2], opengl_bone_mat[2][2])).normalized()
    print("# %s" % (bone.name), file=obj_file)
    #print("b %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %d %d\n" %(world_tail[0], world_tail[1], world_tail[2], \
    print("b %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %d %d\n" %(world_tail[0], world_tail[1], world_tail[2], \
                                                                     world_head[0], world_head[1], world_head[2], \
                                                                     bone_basis_x[0], bone_basis_x[1], bone_basis_x[2], \
                                                                     bone_basis_y[0], bone_basis_y[1], bone_basis_y[2], \
                                                                     bone_basis_z[0], bone_basis_z[1], bone_basis_z[2], \
                                                                     parent_id, len(bone.children)), file=obj_file)
    bones.append(bone.name)
    for child in bone.children:
        traverse_tree(parent_mat, child, cur_id, obj_file)

def write_data(filepath):
    obj_file = open(filepath, 'w', encoding='utf-8')
    mtl_file = open(filepath[0:-4] + ".mtl", 'w', encoding='utf-8')

    print("mtllib %s.mtl" % bpy.path.basename(filepath[0:-4]), file=obj_file)
    global world_mat
    for object in bpy.data.objects:
        if object.type == 'ARMATURE':
            for bone in object.data.bones:
                if bone.parent == None:
                    world_mat = object.matrix_world
                    traverse_tree(mathutils.Matrix.Identity(3), bone, -1, obj_file)
    for object in bpy.data.objects:
        collections = object.users_collection
        hit_box = False
        for collection in collections:
            if collection.name == "colliders" or collection.name == "hit_boxes" or collection.name == "hurt_boxes":
                hit_box = True

        if object.type == 'MESH' and hit_box == False:
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

                world_coords = opengl_mat @ (object.matrix_world @ vertex.co)
                print("v %f %f %f " % (world_coords[0], world_coords[1], world_coords[2]), end = "", file=obj_file)
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

                    normal_matrix = object.matrix_world.to_3x3().inverted_safe().transposed()
                    world_norm = opengl_mat @ (normal_matrix @ polygon.normal)
                    print("vn %f %f %f" % (world_norm[0], world_norm[1], world_norm[2]), file=obj_file)

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
                        if (index < len(mesh_data.uv_layers.active.data)):
                            print("%d/%d/%d" % (mesh_data.loops[index].vertex_index + 1, get_index(uvs, mesh_data.uv_layers.active.data[index].uv, 2) + 1, get_index(normals, polygon.normal, 3) + 1), end =" ", file=obj_file)
                        else:
                            print("%d//%d" % (mesh_data.loops[index].vertex_index + 1, get_index(normals, polygon.normal, 3) + 1), end =" ", file=obj_file)
                    else:
                        if (index < len(mesh_data.uv_layers.active.data)):
                            print("%d/%d/%d" % (mesh_data.loops[index].vertex_index + 1, get_index(uvs, mesh_data.uv_layers.active.data[index].uv, 2) + 1, get_index(normals, polygon.normal, 3) + 1), end ="", file=obj_file)
                        else:
                            print("%d//%d" % (mesh_data.loops[index].vertex_index + 1, get_index(normals, polygon.normal, 3) + 1), end ="", file=obj_file)
                print("", file=obj_file)

    print("", file=obj_file)
    cur_col = 0
    for collection in bpy.data.collections:
        if collection.name == "colliders" or collection.name == "hit_boxes" or collection.name == "hurt_boxes":
            for object in collection.all_objects:
                if object.type == 'MESH' :
                    vertices = object.data.vertices
                    split = split_extensions(object.name)
                    name = split["name"]
                    extensions = split["extensions"]
                    if extensions[len(extensions) - 1] == "L" or extensions[len(extensions) - 1] == "R":
                        name = name + "." + extensions[len(extensions) - 1]

                    category = -1
                    if collection.name == "colliders":
                        category = 0
                    elif collection.name == "hit_boxes":
                        category = 1
                    elif collection.name == "hurt_boxes":
                        category = 2

                    if name in bones:
                        if "p" in extensions and len(vertices) <= 8:
                            print("hp %d %d %d " % (category, bones.index(name), len(vertices)), end="", file=obj_file)
                        if "s" in extensions:
                            print("hs %d %d " % (category, bones.index(name)), end="", file=obj_file)
                    else:
                        if "p" in extensions and len(vertices) <= 8:
                            print("hp %d -1 %d " % (category, len(vertices)), end="", file=obj_file)
                        if "s" in extensions:
                            print("hs %d -1 " % (category), end="", file=obj_file)

                    if "p" in extensions and len(vertices) <= 8:
                        for i in range(0, 8):
                            world_coords = opengl_mat @ (object.matrix_world @ vertices[i].co)
                            if i < 7:
                                print("%f %f %f" % (world_coords[0], world_coords[1], world_coords[2]), end=" ", file=obj_file)
                            elif len(vertices) == 8:
                                print("%f %f %f" % (world_coords[0], world_coords[1], world_coords[2]), end="\n", file=obj_file)
                            else:
                                print("0.0, 0.0, 0.0", end="\n", file=obj_file)
                    if "s" in extensions:
                        local_bbox_center = 0.125 * sum((mathutils.Vector(b) for b in object.bound_box), mathutils.Vector())
                        global_bbox_center = opengl_mat @ (object.matrix_world @ local_bbox_center)
                        world_coords = opengl_mat @ (object.matrix_world @ vertices[0].co)
                        radius = abs((global_bbox_center - world_coords).magnitude)
                        print("%f %f %f %f" % (global_bbox_center[0], global_bbox_center[1], global_bbox_center[2], radius), end="\n", file=obj_file)
                    # Write a single dof for the collider: a revolute joint about it's x axis
                    print("dof %d 1 1.0 0.0 0.0" % (cur_col), end="\n", file=obj_file)
                    cur_col = cur_col + 1
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
                    world_quat = mathutils.Quaternion((offset[0], world_offset_vector[0], world_offset_vector[1], world_offset_vector[2])).normalized()
                    
                    world_offset[0] = world_quat.w
                    world_offset[1] = world_quat.x
                    world_offset[2] = world_quat.y
                    world_offset[3] = world_quat.z
                elif chain_data[1] == ".scale":
                    world_offset_vector = local_point_mat @ mathutils.Vector((offset[0] - 1.0, offset[1] - 1.0, offset[2] - 1.0, 1.0))
                    
                    world_offset[0] = world_offset_vector[0] + 1.0
                    world_offset[1] = world_offset_vector[1] + 1.0
                    world_offset[2] = world_offset_vector[2] + 1.0

                if chain_data[1] == ".rotation_quaternion":
                    translation_offset = opengl_mat @ mathutils.Vector((world_offset[1], world_offset[2], world_offset[3]))
                    print("kp %d %f %f %f %f" % (int(float(keyframe)), translation_offset[0], translation_offset[1], translation_offset[2], world_offset[0]), file=obj_file)
                else:
                    world_offset = opengl_mat @ mathutils.Vector((world_offset[0], world_offset[1], world_offset[2]))
                    print("kp %d %f %f %f" % (int(float(keyframe)), world_offset[0], world_offset[1], world_offset[2]), file=obj_file)

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
