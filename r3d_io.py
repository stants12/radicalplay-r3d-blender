bl_info = {
    "name": "Radical Play 3D .r3d",
    "author": "oteek",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import/Export > Radical Play .r3d",
    "description": "Import/Export Radical Play's .r3d files",
    "category": "Import-Export",
}

import bpy
import math
import os
import bmesh
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
        def parse_floats(s): return [float(v) for v in s.split(',') if v]
        def parse_ints(s): return [int(v) for v in s.split(',') if v]
        for line in open(self.filepath):
            line = line.strip()
            if line.startswith('v(') and ')v' in line:
                vals = parse_floats(line[2:line.index(')v')])
                verts += [(vals[i], vals[i+1], vals[i+2]) for i in range(0, len(vals), 3)]
            elif line.startswith('n(') and ')n' in line:
                vals = parse_floats(line[2:line.index(')n')])
                normals += [(vals[i], vals[i+1], vals[i+2]) for i in range(0, len(vals), 3)]
            elif line.startswith('t(') and ')t' in line:
                vals = parse_floats(line[2:line.index(')t')])
                uvs += [(vals[i], vals[i+1]) for i in range(0, len(vals), 2)]
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
                    uv_layer.data[li].uv = uvs[ui]

        # apply normals
        if normals and normal_inds:
            loop_normals = [None] * len(mesh.loops)
            for poly in mesh.polygons:
                for li_idx, li in enumerate(poly.loop_indices):
                    ni = normal_inds[poly.index][li_idx]
                    loop_normals[li] = normals[ni]
            mesh.normals_split_custom_set(loop_normals)

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
        # triangulate mesh copy
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        temp_mesh = bpy.data.meshes.new("_tmp")
        bm.to_mesh(temp_mesh)
        bm.free()

        verts = [v.co for v in temp_mesh.vertices]
        loops = temp_mesh.loops
        uvs = []
        uv_layer = temp_mesh.uv_layers.active
        if uv_layer:
            uvs = [uv.uv.copy() for uv in uv_layer.data]

        with open(self.filepath, 'w') as f:
            f.write('v(')
            for v in verts:
                f.write(f"{v.x},{v.y},{v.z},")
            f.write(')v\n')

            f.write('n(')
            for l in loops:
                n = l.normal
                f.write(f"{n.x},{n.y},{n.z},")
            f.write(')n\n')

            if uvs:
                f.write('t(')
                for uv in uvs:
                    f.write(f"{uv.x},{uv.y},")
                f.write(')t\n')

            f.write('p(')
            for poly in temp_mesh.polygons:
                for li in poly.loop_indices:
                    l = loops[li]
                    f.write(f"{l.vertex_index},{li},{li},")
            f.write(')p\n')

        bpy.data.meshes.remove(temp_mesh)
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
