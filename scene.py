import bpy
import re
from mathutils import Vector
from mathutils import Matrix
entity = bpy.data.texts["entity.py"].as_module()

# -----------------------------
# Helpers
# -----------------------------

CHUNK_RE = re.compile(r"chunk_(\d+)")
ENTITY_RE = re.compile(r"entity_(\d+)")

HITBOX_COLLECTION_NAMES = {"hit_boxes", "colliders", "hurt_boxes"}

def get_collection_id(name, pattern):
    match = pattern.match(name)
    return int(match.group(1)) if match else None


def get_world_bounds(obj):
    """Returns (center, half_extents) in world space"""
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector((min(v.x for v in bbox),
                         min(v.y for v in bbox),
                         min(v.z for v in bbox)))
    max_corner = Vector((max(v.x for v in bbox),
                         max(v.y for v in bbox),
                         max(v.z for v in bbox)))
    center = (min_corner + max_corner) / 2.0
    half_extents = (max_corner - min_corner) / 2.0
    return center, half_extents


def get_entity_definition(entity_collection):
    geometry_obj = None
    armature = None
    hit_boxes = []
    colliders = []
    hurt_boxes = []

    for obj in entity_collection.objects:
        if obj.type == 'MESH':
            geometry_obj = obj
            break

    for child in entity_collection.children:
        name = child.name.lower()

        if name == "hit_boxes":
            hit_boxes.extend([o for o in child.objects if o.type == 'MESH'])
        elif name == "colliders":
            colliders.extend([o for o in child.objects if o.type == 'MESH'])
        elif name == "hurt_boxes":
            hurt_boxes.extend([o for o in child.objects if o.type == 'MESH'])

    return {
        "geometry": geometry_obj,
        "hit_boxes": hit_boxes,
        "colliders": colliders,
        "hurt_boxes": hurt_boxes
    }


def aggregate_scene():
    entity_registry = {}
    chunks_data = []

    for collection in bpy.data.collections:
        chunk_id = get_collection_id(collection.name, CHUNK_RE)
        if chunk_id is None:
            continue

        chunk_mesh_obj = None
        for obj in collection.objects:
            if obj.name == collection.name and obj.type == 'MESH':
                chunk_mesh_obj = obj
                break

        if chunk_mesh_obj is None:
            print(f"Warning: Chunk {collection.name} missing mesh")
            continue

        chunk_center, chunk_half = get_world_bounds(chunk_mesh_obj)

        chunk_entry = {
            "id": chunk_id,
            "center": chunk_center,
            "half_width": chunk_half,
            "entities": []
        }

        used_entity_ids = set()

        for obj in collection.all_objects:
            if obj.instance_collection:
                entity_col = obj.instance_collection
                entity_id = get_collection_id(entity_col.name, ENTITY_RE)

                if entity_id is None:
                    continue

                used_entity_ids.add(entity_id)

                if entity_id not in entity_registry:
                    entity_registry[entity_id] = get_entity_definition(entity_col)

                world_pos = obj.matrix_world.translation
                local_pos = world_pos - chunk_center

                chunk_entry["entities"].append({
                    "entity_id": entity_id,
                    "position": local_pos
                })

        chunk_entry["used_entity_ids"] = list(used_entity_ids)
        chunks_data.append(chunk_entry)


    result = {
        "chunks": chunks_data,
        "entities": entity_registry
    }

    return result

def serialize_scene_entity(directory, name, entity):
    obj_file = open(directory + "/" + name + ".obj", 'w', encoding='utf-8')
    mtl_file = open(directory + "/" + name + ".mtl", 'w', encoding='utf-8')

    geometry = entity["geometry"]
    hit_boxes = entity["hit_boxes"]
    colliders = entity["colliders"]
    hurt_boxes = entity["hurt_boxes"]
    armature = None

    entity_origin = Vector((0.0, 0.0, 0.0))
    if geometry is not None:
        entity_origin = geometry.matrix_world.translation
    elif len(colliders) > 0:
        entity_origin = colliders[0].matrix_world.translation
    elif len(hit_boxes) > 0:
        entity_origin = hit_boxes[0].matrix_world.translation
    elif len(hurt_boxes) > 0:
        entity_origin = hurt_boxes[0].matrix_world.translation

    print("mtllib %s.mtl" % bpy.path.basename(filepath[0:-4]), file=obj_file)

    bones = []
    if geometry is not None and geometry.parent and geometry.parent.type == 'ARMATURE':
        armature = geometry.parent
        for bone in armature.data.bones:
            if bone.parent == None:
                traverse_armature(armature, entity_origin, bones, bone, Matrix.Identity(3), -1, obj_file)

    if geometry is not None:
        serialize_mesh(Matrix.Identity(4), geometry, bones, obj_file, mtl_file)
    print("", file=obj_file)

    # Ouput collider data
    cur_col = 0
    cur_col = serialize_collider_collection(entity_origin, cur_col, hit_boxes, bones, obj_file)
    cur_col = serialize_collider_collection(entity_origin, cur_col, colliders, bones, obj_file)
    cur_col = serialize_collider_collection(entity_origin, cur_col, hurt_boxes, bones, obj_file)

    # TODO Figure out world_mat and getting actions of entity
    #for action in bpy.data.actions:
    #    serialize_action(action, bones, obj_file)

    obj_file.close()
    mtl_file.close()

    return {'FINISHED'}

def serialize_scene(dir_path):
    scene_data = aggregate_scene()

    chunks = scene_data["chunks"]
    entities = scene_data["entities"]

    for entity_id in entities:
        serialize_scene_entity(dir_path, entity_id, entities[entity_id])

    # TODO Export chunks
