
# OpenGL Rendering Engine

## Introduction/Overview:

This project serves as the codebase for my OpenGL based graphics engine, developed in C utilizing [GLFW](https://www.glfw.org/), [GLAD](https://glad.dav1d.de/), [cglm](https://github.com/recp/cglm), and [STB](https://github.com/nothings/stb). The goal of this project is to serve as a lightweight suite of tools for realtime graphics applications that may utilize lighting, physics or animation, such as games. Below explains a very basic overview of the core features of the engine, as well as some functions to actually use the engine. This is not a tutorial on how to use the engine, but instead a broad overview of its methodologies and plans.

## Current Features
### Model/Entity paradigm
#### Motivation
The entire purpose of the engine is based around the manipulation of objects in 3D space. It is very convenient to import premade 3D models with mesh, animation and physics data to represent these objects when rendered to the screen. With this, inevitably comes the instance where a program utilizes multiple instances of a singular 3D model, say a simple character mesh, for purposes such as a physics simulation. These characters will have identical 3D models, animations and hitboxes, but should have the ability to have differing spatial positions, animation state, and physical properties. As such, a system must be devised to separate information that is uniform across all simulated objects represented by the same model, and object specific information.

These individual objects are referred to as **entities** by the engine, and they can be thought of as instances of **models**, which contain the entity's integral, essential information. 

Each **entity** in the world has their own:
- Spatial attributes (position, rotation, scale)
- Skeletal bone orientations
- Physical properties

While each **model** contains:
- Mesh data
- Available animations
- Hitboxes
- Bone structure

With this structure, objects that are all instances of the same 3D model do not have to needlessly hold an instance of repetitive mesh information, and instead, only need to maintain information that is exclusive to the state of that object. 

#### Entity initialization:
``ENTITY *init_entity(MODEL *model)``
This will return a pointer to an entity, which is an instance of the model, ``model``.
A basic overview of importing a model can be found in [Model preprocessing and loading](#Model-preprocessing-and-loading).

#### Rendering the entity:
``void draw_entity(unsigned int shader, ENTITY *entity)``
Will draw the entity to the screen, given an OpenGL shader program is provided.

### Model preprocessing and loading
Initially, the project supported the Wavefront .obj file format for models due to the simplicity and ease of parsing. However, upon branching out into subjects such as animation and physics, it became apparent more than just vertex, material and face information was needed in model files. Looking to other file formats that supported animation info proved somewhat daunting from a parsing perspective, so I decided to modify the .obj file format for the purposes of this engine. As such, I've also written a [python script](https://github.com/Jack-Saysana/Blender-Custom-Obj-Exporter) that, when imported into blender, will allow for the exporting of models with animation and physics data.
Additionally, because the chosen file format is text based, although it is simple to parse, it is rather slow when importing complex models. As such, a preprocessor system has been developed as a part of the engine's model loader, which preprocess the modified .obj files to binaries that will be automatically detected and read from the next time the model is loaded. Ultimately, with this custom model format and preprocessor, the workflow of developing models in blender and rendering them in engine is quite easy. Furthermore, because the entire process is custom, from exporting in blender and importing in engine, additional features and support can be added with relative ease.

#### Usage:
The interface for loading models is relatively straightforward:
``MODEL *load_model(char *path)``
``load_model`` will load the file located at ``path`` if it has already been preprocessed, or automatically preprocess the file if it has not yet been preprocessed before loading.

### Animation/Bone system
A skeletal system is integrated into the **entity** structure, providing a simple way for displaying joint orientations of 3D meshes for animation or physical purposes. Furthermore, since actual keyframe data is supported in the custom .obj file format, the engine also fully supports display of predefined animations.

#### The Skeleton:
The bones which define the rigged skeleton of the mesh in blender also represent the bones of an entity in the engine. Each bone has its own scale, rotation and position model matrices, and are organized in a hierarchical, tree-like structure. These matrices can be manipulated by predefined animation keyframes, or ragdoll-like physical simulation, ultimately giving the mesh the appearance of joint movement. 

#### Animations:
A simple interface has been designed for the display of entity animations.
``int animate(ENTITY *entity, unsigned int animation_index, unsigned int frame)``
``animation_index`` represents the index of the animation to be shown from ``entity``'s model. ``frame`` indicates which from of the animation to show. If successful, the function will update ``entity``'s bone matricies such that when rendering ``entity``, the joints are oriented correctly.

### Collision Detection
When looking to physical simulation, collision detection is the first step. Collider/hitbox information for a given 3D model is supported by the custom .obj file format. The two types of colliders supported by the engine are
**spheres** and **polyhedrons of 8 vertices**. 

#### Simulation Loop
The engine maintains a **simulation system**, which consists of individual colliders organized in an oct-tree data structure. Each frame of the engine is a step in the simulation, where collider positions are updated based on movement, and collision checking is done. A variety of functions are available for interfacing with the simulation system, such as adding an entity's colliders to the simulation, removing an entity's colliders from the simulation, etc.

#### Collision
Collision detection is achieved via the Gilbert-Johnson-Keerthi (GJK) algorithm. Collision depth and direction are found via the Expanding Polytope Algorithm (EPA).

### Collision Response
Currently, an impulse based collision response mechanism is implemented for simple rigid bodies, and works quite well. However, this system does not support rag-doll physics like those seen in entities with colliders that are interconnected via bone connections. As such, this system will most likely be replaced/integrated into a Featherstone based approach.

### Spatial Algebra
Because the engine intends to implement ragdoll physics via Featherstone's algorithm, and cglm only supports up to 4D vectors, custom 6D matrix and vector math functions have been developed and integrated into the engine. Furthermore, specialized 6D operations such as the spatial inner product, spatial transformation and spatial transpose have been implemented.
## In Progress
### Rigid Body Dynamics and Ragdolls
The most recent development has been focused on developing a robust ragdoll/joint based physics simulation for the engine, utilizing Featherstone's ABM.
## Future Plans
### Serialization
As the final major component of the engine before it may be used for future projects such as game development, serialization will be developed to enable the saving and loading of world state. 
### Misc Graphics Features
On top of the existing graphical utilities that abstract rendering meshes and loading shaders, additional utilities will be developed to assist in implementing other OpenGL features such as framebuffers and mapping (bump, environment, parallax, shadow). Furthermore, additional, more complex shaders will be developed as well.
