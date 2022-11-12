# Blender-Custom-Obj-Exporter
A blender script that allows the exporting of .obj files containing model rigging information

## Motivation
By default, the Wavefront .obj file format does not support animation/rigging data. However, with the development of my own graphics engine and model loader, I am in need of a simple means of importing such information without requiring the need of a hacky solution such as rendering a completely different model for each frame of animation, or support of multiple (and vastly different) 3d model file formats. As such, this is a simple python script which enables blender to export a modified version of the .obj file format, which will contain the rigging information in a scene.

## Usage
In the scripting tab in blender, simply import and run the repo's `export.py` file. From there, an additional export option will now appear under the `File->Export` tab, labeled `Wavefront (rigged) (.obj)`.
