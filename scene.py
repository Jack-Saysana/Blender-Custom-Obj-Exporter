import bpy
import re
import os
import struct
from mathutils import Vector
from mathutils import Matrix
entity = bpy.data.texts["entity.py"].as_module()

CHUNK_RE = re.compile(r"chunk_(.+)")
ENTITY_RE = re.compile(r"entity_(.+)")
MODEL_ID_BASE = 8

OPENGL_MAT = entity.opengl_mat
OPENGL_MAT_4 = OPENGL_MAT.to_4x4()

HITBOX_COLLECTION_NAMES = {"hit_boxes", "colliders", "hurt_boxes"}

def clear_dir(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)

def get_collection_id(name, pattern):
    split = entity.split_extensions(name)
    col_name = split["name"]
    match = pattern.match(col_name)
    return int(match.group(1)) if match else None

def get_entity_id(name, pattern):
    split = entity.split_extensions(name)
    col_name = split["name"]
    match = pattern.match(col_name)
    return col_name if match else None

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
    return OPENGL_MAT @ center, OPENGL_MAT @ half_extents


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
        split = entity.split_extensions(name)
        cat_name = split["name"]

        if cat_name == "hit_boxes":
            hit_boxes.extend([o for o in child.objects if o.type == 'MESH'])
        elif cat_name == "colliders":
            colliders.extend([o for o in child.objects if o.type == 'MESH'])
        elif cat_name == "hurt_boxes":
            hurt_boxes.extend([o for o in child.objects if o.type == 'MESH'])

    split = entity.split_extensions(entity_collection.name)
    col_name = split["name"]

    return {
        "name": col_name,
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
            obj_split = entity.split_extensions(obj.name)
            col_split = entity.split_extensions(collection.name)
            if obj_split["name"] == col_split["name"] and obj.type == 'MESH':
                chunk_mesh_obj = obj
                break

        if chunk_mesh_obj is None:
            print(f"Warning: Chunk {collection.name} missing mesh")
            continue

        chunk_center, chunk_half = get_world_bounds(chunk_mesh_obj)

        chunk_entry = {
            "id": chunk_id,
            "center": chunk_center,
            "half_width": chunk_half.x,
            "entities": []
        }

        used_entity_ids = set()

        for obj in collection.all_objects:
            if obj.users_collection:
                ent_col = obj.users_collection[0]
                ent_name = ent_col.name
                entity_id = get_entity_id(ent_name, ENTITY_RE)

                if entity_id is None:
                    continue

                used_entity_ids.add(entity_id)

                if entity_id not in entity_registry:
                    entity_registry[entity_id] = get_entity_definition(ent_col)

                mat = OPENGL_MAT_4 @ obj.matrix_world @ OPENGL_MAT_4.transposed()
                loc, rot, scale = mat.decompose()

                chunk_entry["entities"].append({
                    "entity_id": entity_id,
                    "loc": loc,
                    "rot": rot,
                    "scale": scale
                })

        chunk_entry["used_entity_ids"] = list(used_entity_ids)
        chunks_data.append(chunk_entry)

    result = {
        "chunks": chunks_data,
        "entities": entity_registry
    }

    return result

def serialize_scene_entity(directory, ent):
    obj_file = open(directory + "/" + ent["name"] + ".obj", 'w', encoding='utf-8')
    mtl_file = open(directory + "/" + ent["name"] + ".mtl", 'w', encoding='utf-8')

    geometry = ent["geometry"]
    hit_boxes = ent["hit_boxes"]
    colliders = ent["colliders"]
    hurt_boxes = ent["hurt_boxes"]
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

    basename = ent["name"]
    print(f"mtllib {basename}.mtl", file=obj_file)

    bones = []
    if geometry is not None and geometry.parent and geometry.parent.type == 'ARMATURE':
        armature = geometry.parent
        for bone in armature.data.bones:
            if bone.parent == None:
                entity.traverse_armature(armature, entity_origin, bones, bone, Matrix.Identity(3), -1, obj_file)

    if geometry is not None:
        entity.serialize_mesh(Matrix.Identity(4), geometry, bones, obj_file, mtl_file)
    print("", file=obj_file)

    # Ouput collider data
    cur_col = 0
    for hb in hit_boxes:
        entity.serialize_collider(cur_col, entity_origin, "hit_boxes", hb, bones, obj_file)
        cur_col = cur_col + 1
    for cb in colliders:
        entity.serialize_collider(cur_col, entity_origin, "colliders", cb, bones, obj_file)
        cur_col = cur_col + 1
    for hb in hurt_boxes:
        entity.serialize_collider(cur_col, entity_origin, "hurt_boxes", hb, bones, obj_file)
        cur_col = cur_col + 1

    # TODO Figure out world_mat and getting actions of entity
    #for action in bpy.data.actions:
    #    serialize_action(action, bones, obj_file)

    obj_file.close()
    mtl_file.close()

    return {'FINISHED'}

def serialize_chunk_metadata(directory, chunks):
    with open(directory + "/md.bin", "wb") as md_file:
        num_chunks = struct.pack("<Q", len(chunks))
        md_file.write(num_chunks)
        for chunk in chunks:
            chunk_origin = chunk["center"]
            chunk_size = chunk["half_width"]
            phys_data = struct.pack("<ffff", chunk_origin.x, chunk_origin.y, chunk_origin.z, float(chunk_size))
            md_file.write(phys_data)
            # Neighbors will have to be manually calculated in map editor
            md_file.write(b"\x00" * len(chunks))

def serialize_chunk(directory, chunk_id, chunk, entity_data):
    with open(directory + f"/{chunk_id}.bin", "wb") as chunk_file:
        entities = chunk["entities"]
        # Nav mesh added in map editor
        nav_data = struct.pack("<QQ", 0, 0)
        # NPCs added in map editor
        num_npcs = struct.pack("<Q", 0)
        num_sps = struct.pack("<Q", len(entities))
        chunk_file.write(nav_data + num_npcs + num_sps)
        for entity in entities:
            l = entity["loc"]
            r = entity["rot"]
            s = entity["scale"]
            loc = struct.pack("<fff", l.x, l.y, l.z)
            rot = struct.pack("<ffff", r.x, r.y, r.z, r.w)
            scale = struct.pack("<fff", s.x, s.y, s.z)
            # Entity mass manually set in map editor
            inv_mass = struct.pack("<f", 0)
            model_id = list(entity_data).index(entity["entity_id"]) + MODEL_ID_BASE
            chunk_file.write(rot + loc + scale)
            chunk_file.write(struct.pack("<i", model_id) + inv_mass)

def serialize_scene(dir_path):
    scene_data = aggregate_scene()

    chunks = scene_data["chunks"]
    entities = scene_data["entities"]

    chunk_dir = dir_path + "/chunks"
    entity_dir = dir_path + "/entities"
    os.makedirs(chunk_dir, exist_ok=True)
    os.makedirs(entity_dir, exist_ok=True)

    clear_dir(chunk_dir)
    clear_dir(entity_dir)

    for entity_id in entities:
        serialize_scene_entity(entity_dir, entities[entity_id])

    serialize_chunk_metadata(chunk_dir, chunks)
    for index, chunk in enumerate(chunks):
        serialize_chunk(chunk_dir, index, chunk, entities)

    return {'FINISHED'}
