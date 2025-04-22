bl_info = {
    "name": "Radical Play 3D .r3d",
    "author": "oteek",
    "version": (0, 1, 6),
    "blender": (2, 80, 0),
    "location": "File > Import/Export > Radical Play .r3d",
    "description": "Import/Export Radical Play's .r3d files",
    "category": "Import-Export",
}

import bpy
import math
import os
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.types import Operator
from bpy.props import StringProperty

# --- Importer ---
class ImportR3D(Operator, ImportHelper):
    bl_idname = "import_scene.r3d"
    bl_label = "Import .r3d"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".r3d"
    filter_glob: StringProperty(default="*.r3d", options={'HIDDEN'})

    def execute(self, context):
        fname = os.path.splitext(os.path.basename(self.filepath))[0]
        verts, normals, uvs, triplets = [], [], [], []
        is_car = False
        is_grouptexture = False
        def parse_floats(s): return [float(v) for v in s.split(',') if v]
        def parse_ints(s): return [int(v) for v in s.split(',') if v]
        for line in open(self.filepath):
            line = line.strip()
            if line.startswith('car()'):
                is_car = True
            elif line.startswith('grouptexture('):
                is_grouptexture = True
            elif line.startswith('v(') and ')v' in line:
                vals = parse_floats(line[2:line.index(')v')])
                verts += [(vals[i], vals[i+1], vals[i+2]) for i in range(0, len(vals), 3)]
            elif line.startswith('n(') and ')n' in line:
                vals = parse_floats(line[2:line.index(')n')])
                normals += [(vals[i], vals[i+1], vals[i+2]) for i in range(0, len(vals), 3)]
            elif line.startswith('t(') and ')t' in line:
                vals = parse_floats(line[2:line.index(')t')])
                # importer flips non-car UVs
                if is_car or is_grouptexture:
                    uvs += [(vals[i], vals[i+1]) for i in range(0, len(vals), 2)]
                else:
                    uvs += [(vals[i], 1.0 - vals[i+1]) for i in range(0, len(vals), 2)]
            elif line.startswith('p(') and ')p' in line:
                idx = parse_ints(line[2:line.index(')p')])
                # each triple: vert_idx, norm_idx, uv_idx
                for i in range(0, len(idx), 3):
                    triplets.append((idx[i], idx[i+1], idx[i+2]))

        faces, uv_inds, normal_inds = [], [], []
        for i in range(0, len(triplets), 3):
            tri = triplets[i:i+3]
            faces.append((tri[0][0], tri[1][0], tri[2][0]))
            uv_inds.append((tri[0][2], tri[1][2], tri[2][2]))
            normal_inds.append((tri[0][1], tri[1][1], tri[2][1]))

        mesh = bpy.data.meshes.new(name=fname)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(fname, mesh)
        # correct orientation
        obj.rotation_euler = (math.radians(90), 0, 0)
        context.collection.objects.link(obj)

        # apply UVs
        if uvs and uv_inds:
            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly in mesh.polygons:
                for li_idx, li in enumerate(poly.loop_indices):
                    ui = uv_inds[poly.index][li_idx]
                    if 0 <= ui < len(uvs):
                        uv_layer.data[li].uv = uvs[ui]

        # apply normals
        if normals and normal_inds:
            # mesh.use_auto_smooth = True
            loop_normals = [None] * len(mesh.loops)
            for poly in mesh.polygons:
                for li_idx, li in enumerate(poly.loop_indices):
                    ni = normal_inds[poly.index][li_idx]
                    if 0 <= ni < len(normals):
                        loop_normals[li] = normals[ni]
            mesh.normals_split_custom_set([n if n else (0,0,1) for n in loop_normals])
        return {'FINISHED'}

# --- Exporter ---
class ExportR3D(Operator, ExportHelper):
    bl_idname = "export_scene.r3d"
    bl_label = "Export .r3d"
    bl_options = {'PRESET'}

    filename_ext = ".r3d"
    filter_glob: StringProperty(default="*.r3d", options={'HIDDEN'})

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        fname = os.path.splitext(os.path.basename(self.filepath))[0]
        is_car = obj.name.lower().startswith('car')
        is_grouptexture = any(mat.name.startswith('g') for mat in mesh.materials)

        # gather data
        verts = [v.co.copy() for v in mesh.vertices]
        loop_normals = [loop.normal.copy() for loop in mesh.loops]
        uvs = []
        if mesh.uv_layers.active:
            uv_data = mesh.uv_layers.active.data
            uvs = [uv.uv.copy() for uv in uv_data]

        with open(self.filepath, 'w') as f:
            if is_car: f.write('car()\n')
            if is_grouptexture: f.write(f'grouptexture({0})\n')

            # vertices
            f.write('v(')
            for v in verts:
                f.write(f'{v.x},{v.y},{v.z},')
            f.write(')v\n')

            # normals
            f.write('n(')
            for n in loop_normals:
                f.write(f'{n.x},{n.y},{n.z},')
            f.write(')n\n')

            # UVs
            if uvs:
                f.write('t(')
                for uv in uvs:
                    u, v_ = uv.x, uv.y
                    v_out = v_ if (is_car or is_grouptexture) else 1.0 - v_
                    f.write(f'{u},{v_out},')
                f.write(')t\n')

            # faces (vertex, normal, uv indices)
            f.write('p(')
            for poly in mesh.polygons:
                for li in poly.loop_indices:
                    lv = mesh.loops[li]
                    f.write(f'{lv.vertex_index},{li},{li},')
            f.write(')p\n')

        return {'FINISHED'}

# register
classes = [ImportR3D, ExportR3D]

def menu_func_import(self, context):
    self.layout.operator(ImportR3D.bl_idname, text="Radical Play 3D .r3d (.r3d)")

def menu_func_export(self, context):
    self.layout.operator(ExportR3D.bl_idname, text="Radical Play 3D .r3d (.r3d)")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
