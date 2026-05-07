# Chunked Entity Scene Format

This scene organization format is designed for Blender projects which contain:

- Spatially partitioned **chunks**
- Reusable **entity definitions**
- Optional hit-box geometry for gameplay/collision systems

The exported data is intended for serialization into a runtime-friendly format.

---

# Overview

The Blender scene is organized into two primary collection types:

| Type | Naming Format | Purpose |
|---|---|---|
| Chunk Collection | `chunk_[ID]...` | Defines a spatial chunk and contains entity instances |
| Entity Collection | `entity_[ID]...` | Defines reusable entity data |

An entity may be instanced in multiple chunks.

---

# Chunk Collections

Chunk collections define world-space partitions.

## Naming

```text
chunk_[ID]
```

Examples:

```text
chunk_0
chunk_forest
chunk_city_block_a
```

---

## Chunk Contents

Each chunk collection must contain:

### 1. Chunk Bounds Mesh

A mesh object whose name exactly matches the collection name.

Example:

```text
Collection: chunk_forest
Mesh Object: chunk_forest
```

This mesh must be:

- A cube
- Axis-aligned
- Used to define the chunk bounds

The exporter derives:

- Chunk world position
- Chunk half-width

from this object.

---

### 2. Entity Collections

Chunk collections may contain child collections named:

```text
entity_[ID]
```

These represent entity instances within the chunk.

---

# Entity Collections

Entity collections define reusable entity data.

## Naming

```text
entity_[ID]
```

Examples:

```text
entity_tree
entity_enemy
entity_crate_large
```

The `[ID]` portion is treated as the runtime entity identifier.

---

## Entity Structure

An entity collection contains:

| Content | Required | Description |
|---|---|---|
| Geometry Mesh | Yes | Main render/visual mesh |
| `hit_boxes` Collection | Optional | Offensive hit geometry |
| `colliders` Collection | Optional | Collision geometry |
| `hurt_boxes` Collection | Optional | Damage receiver geometry |

---

# Geometry Mesh

The entity collection should contain exactly one primary mesh object representing the entity geometry.

Example:

```text
entity_tree
└── TreeMesh
```

The exporter automatically identifies the geometry mesh as:

> Any mesh object directly inside the entity collection that is NOT part of a hit-box subcollection.

---

# Hit Box Collections

The following optional child collections are recognized:

| Collection Name | Purpose |
|---|---|
| `hit_boxes` | Attack / damage volumes |
| `colliders` | Physics / collision geometry |
| `hurt_boxes` | Damage receiver volumes |

Each collection may contain one or more mesh objects.

Example:

```text
entity_enemy
├── EnemyMesh
├── hit_boxes
│   ├── SwordHit
│   └── KickHit
├── colliders
│   └── BodyCollider
└── hurt_boxes
    └── BodyHurt
```

---
# Exported Chunk Data

The exporter writes chunk data into a `chunks` subdirectory inside the selected export directory.

Example:

```text
ExportDirectory/
├── chunks/
│   ├── chunk_forest.bin
│   ├── chunk_city.bin
│   └── chunk_cave.bin
└── entities/
```

Each chunk file contains serialized runtime. The actual binary layout is determined by the runtime serializer (Game engine).

---

# Exported Entity Data

The exporter writes entity definitions into an `entities` subdirectory inside the selected export directory.

Each entity receives its own directory named after the entity ID.

Example:

```text
ExportDirectory/
├── chunks/
└── entities/
    ├── tree/
    │   ├── tree.obj
    │
    ├── enemy/
    │   ├── enemy.obj
    │
    └── crate/
        └── crate.obj
```

---

## Serialized Entity Contents

Each entity directory may contain:

| File Type | Description |
|---|---|
| Geometry Mesh | Main entity render geometry |
| Hit Box Meshes | Offensive interaction geometry |
| Collider Meshes | Physics/collision geometry |
| Hurt Box Meshes | Damage receiver geometry |

The exact serialization format is determined by the export pipeline and runtime importer.

---

## Entity Deduplication

Entities are exported only once regardless of how many chunks reference them.

Chunk files reference entities by ID.

This allows:

- Efficient storage
- Runtime instancing
- Shared entity definitions
- Chunk streaming

---

# Coordinate Spaces

## World Space

Entities and Chunk positions are stored in world space.

---

# Important Constraints

## Chunk Bounds

Chunk meshes must be:

- Cubes
- Axis-aligned

Non-cubic or rotated meshes may produce incorrect bounds.

---

## Entity Reuse

Entities are treated as reusable definitions.

The same entity collection may appear in multiple chunk collections.

---

## Geometry Detection

Only mesh objects are exported.

Non-mesh Blender objects are ignored.

---

# Example Scene Hierarchy

```text
chunk_forest
├── chunk_forest
├── entity_tree
├── entity_enemy

entity_tree
├── TreeMesh
└── colliders
    └── TreeCollider

entity_enemy
├── EnemyMesh
├── hit_boxes
│   └── SwordHit
├── colliders
│   └── EnemyCollider
└── hurt_boxes
    └── EnemyHurt
```

---

# Intended Runtime Structure

The format is designed to separate:

## Static Definitions

Entity geometry and collision data.

## Spatial Instances

Chunk-local entity placement.

This allows:

- Entity deduplication
- Chunk streaming
- Efficient serialization
- Runtime instancing

---

This README was vibecoded lol :3