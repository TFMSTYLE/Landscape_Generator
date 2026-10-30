bl_info = {
    "name": "Landscape",
    "author": "Jimmy Hazevoet & The French Monkey",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Landscape",
    "description": "Generate parametric Landscape",
    "category": "Add Mesh",
    "license": "GPL-3.0-or-later",
}

import bpy
import bmesh
import math
import numpy as np
import os
from math import (
    sin, cos, pi, floor, sqrt, radians, tan,
)
from mathutils import Vector, noise
from mathutils import Vector
from mathutils.noise import (
    seed_set, noise, turbulence, turbulence_vector, fractal,
    hybrid_multi_fractal, multi_fractal, ridged_multi_fractal,
    hetero_terrain, random_unit_vector, variable_lacunarity, voronoi,
)
import random
from random import random as rand
from time import time

# ------------------------------------------------------------
# Noise Basis Types
# ------------------------------------------------------------

noise_basis_default = "BLENDER"
noise_basis = [
    ("BLENDER", "Blender", "Blender default noise", 0),
    ("PERLIN_ORIGINAL", "Perlin", "Perlin noise", 1),
    ("PERLIN_NEW", "New Perlin", "New Perlin noise", 2),
    ("VORONOI_F1", "Voronoi F1", "Voronoi F1", 3),
    ("VORONOI_F2", "Voronoi F2", "Voronoi F2", 4),
    ("VORONOI_F3", "Voronoi F3", "Voronoi F3", 5),
    ("VORONOI_F4", "Voronoi F4", "Voronoi F4", 6),
    ("VORONOI_F2F1", "Voronoi F2-F1", "Voronoi F2-F1", 7),
    ("VORONOI_CRACKLE", "Voronoi Crackle", "Voronoi Crackle", 8),
    ("CELLNOISE", "Cell Noise", "Cell noise", 9)
]

# ------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------

GENERATOR_NAME = "Landscape"

def get_active_landscape(context):
    obj = context.active_object
    if obj and obj.type == 'MESH' and "landscape_generator" in obj:
        return obj
    return None

def _make_prop_list(props):
    return [
        props.ant_terrain_name,               # terrain_name
        props.smooth_mesh,                    # smooth_mesh
        props.tri_face,                       # tri_face
        props.sphere_mesh,                    # sphere_mesh
        props.land_material,                  # land_material
        props.water_material,                 # water_material
        props.texture_block,                  # texture_block
        props.subdivision_x,                  # subd_x
        props.subdivision_y,                  # subd_y
        props.mesh_size_x,                    # meshsize_x
        props.mesh_size_y,                    # meshsize_y
        props.mesh_size,                      # meshsize
        props.random_seed,                    # random_seed
        props.noise_offset_x,                 # noise_offset_x
        props.noise_offset_y,                 # noise_offset_y
        props.noise_offset_z,                 # noise_offset_z
        props.noise_size_x,                   # noise_size_x
        props.noise_size_y,                   # noise_size_y
        props.noise_size_z,                   # noise_size_z
        props.noise_size,                     # nsize
        props.noise_type,                     # ntype
        props.basis_type,                     # nbasis
        props.vl_basis_type,                  # vlbasis
        props.distortion,                     # distortion
        props.hard_noise,                     # hard_noise
        props.noise_depth,                    # depth
        props.amplitude,                      # amp
        props.frequency,                      # freq
        props.dimension,                      # dimension
        props.lacunarity,                     # lacunarity
        props.offset,                         # offset
        props.gain,                           # gain
        props.marble_bias,                    # marble_bias
        props.marble_sharp,                   # marble_sharp
        props.marble_shape,                   # marble_shape
        props.height,                         # height
        props.height_invert,                  # height_invert
        props.height_offset,                  # height_offset
        props.maximum,                        # maximum
        props.minimum,                        # minimum
        props.edge_falloff,                   # falloff
        props.edge_level,                     # edge_level
        props.falloff_x,                      # falloff_x
        props.falloff_y,                      # falloff_y
        props.strata_type,                    # stratatype
        props.strata,                         # strata
        props.water_plane,                    # water_plane
        props.water_level,                    # water_level
        props.vert_group,                     # vert_group
        props.remove_double,                  # remove_double
        props.fx_mixfactor,                   # fx_mixfactor
        props.fx_mix_mode,                    # fx_mix_mode
        props.fx_type,                        # fx_type
        props.fx_bias,                        # fx_bias
        props.fx_turb,                        # fx_turb
        props.fx_depth,                       # fx_depth
        props.fx_frequency,                   # fx_frequency
        props.fx_amplitude,                   # fx_amplitude
        props.fx_size,                        # fx_size
        props.fx_loc_x,                       # fx_loc_x
        props.fx_loc_y,                       # fx_loc_y
        props.fx_height,                      # fx_height
        props.fx_offset,                      # fx_offset
        props.fx_invert,                      # fx_invert
    ]

def rebuild_landscape_in_place(context, obj, props):
    prop_list = _make_prop_list(props)

    if props.sphere_mesh:
        verts, faces = sphere_gen(
            props.subdivision_y, props.subdivision_x, props.tri_face,
            props.mesh_size, prop_list, False, 0.0
        )
    else:
        verts, faces = grid_gen(
            props.subdivision_x, props.subdivision_y, props.tri_face,
            props.mesh_size_x, props.mesh_size_y, prop_list, False, 0.0
        )

    old_mesh = obj.data
    new_mesh = bpy.data.meshes.new(old_mesh.name + "_rebuild")
    new_mesh.from_pydata(verts, [], faces)
    new_mesh.update()

    for mat in old_mesh.materials:
        new_mesh.materials.append(mat)

    obj.data = new_mesh

    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)

    water_children = [c for c in obj.children if c.type == 'MESH' and "_Water" in c.name]
    for wc in water_children:
        bpy.data.objects.remove(wc, do_unlink=True)

    if props.water_plane:
        if props.sphere_mesh:
            w_verts, w_faces = sphere_gen(
                props.subdivision_y, props.subdivision_x, props.tri_face,
                props.mesh_size, prop_list, True, props.water_level
            )
        else:
            w_verts, w_faces = grid_gen(
                2, 2, props.tri_face, props.mesh_size_x, props.mesh_size_y,
                prop_list, True, props.water_level
            )
        w_mesh = bpy.data.meshes.new(obj.name + "_water_mesh")
        w_mesh.from_pydata(w_verts, [], w_faces)
        w_obj = bpy.data.objects.new(obj.name + "_Water", w_mesh)
        context.collection.objects.link(w_obj)
        w_obj.parent = obj

        if props.water_material and props.water_material in bpy.data.materials:
            w_obj.data.materials.append(bpy.data.materials[props.water_material])

        if props.smooth_mesh:
            context.view_layer.objects.active = w_obj
            bpy.ops.object.shade_smooth()
            context.view_layer.objects.active = obj 

    if props.smooth_mesh:
        context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

def create_mesh_object(context, verts, edges, faces, name):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    
    from bpy_extras import object_utils
    return object_utils.object_data_add(context, mesh)

# ------------------------------------------------------------
# Grid and Sphere Generators
# ------------------------------------------------------------

def grid_gen(sub_d_x, sub_d_y, tri, meshsize_x, meshsize_y, props, water_plane, water_level):
    verts = []
    faces = []
    vappend = verts.append
    fappend = faces.append
    
    for i in range(0, sub_d_x):
        x = meshsize_x * (i / (sub_d_x - 1) - 1 / 2)
        for j in range(0, sub_d_y):
            y = meshsize_y * (j / (sub_d_y - 1) - 1 / 2)
            if not water_plane:
                z = noise_gen((x, y, 0), props)
            else:
                z = water_level
            vappend((x, y, z))

            if i > 0 and j > 0:
                A = i * sub_d_y + (j - 1)
                B = i * sub_d_y + j
                C = (i - 1) * sub_d_y + j
                D = (i - 1) * sub_d_y + (j - 1)
                if not tri:
                    fappend((A, B, C, D))
                else:
                    fappend((A, B, D))
                    fappend((B, C, D))

    return verts, faces

def sphere_gen(sub_d_x, sub_d_y, tri, meshsize, props, water_plane, water_level):
    verts = []
    faces = []
    vappend = verts.append
    fappend = faces.append
    sub_d_x += 1
    sub_d_y += 1
    
    for i in range(0, sub_d_x):
        for j in range(0, sub_d_y):
            u = sin(j * pi * 2 / (sub_d_y - 1)) * cos(-pi / 2 + i * pi / (sub_d_x - 1)) * meshsize / 2
            v = cos(j * pi * 2 / (sub_d_y - 1)) * cos(-pi / 2 + i * pi / (sub_d_x - 1)) * meshsize / 2
            w = sin(-pi / 2 + i * pi / (sub_d_x - 1)) * meshsize / 2
            if water_plane:
                h = water_level
            else:
                h = noise_gen((u, v, w), props) / meshsize
            vappend(((u + u * h), (v + v * h), (w + w * h)))

    count = 0
    for i in range(0, sub_d_y * (sub_d_x - 1)):
        if count < sub_d_y - 1:
            A = i + 1
            B = i
            C = (i + sub_d_y)
            D = (i + sub_d_y) + 1
            if tri:
                fappend((A, B, D))
                fappend((B, C, D))
            else:
                fappend((A, B, C, D))
            count = count + 1
        else:
            count = 0

    return verts, faces

# ------------------------------------------------------------
# Height scale and effect functions
# ------------------------------------------------------------

def Height_Scale(input, iscale, offset, invert):
    if invert:
        return (1.0 - input) * iscale + offset
    else:
        return input * iscale + offset

def sin_bias(a):
    return 0.5 + 0.5 * sin(a)

def cos_bias(a):
    return 0.5 + 0.5 * cos(a)

def tri_bias(a):
    b = 2 * pi
    a = 1 - 2 * abs(floor((a * (1 / b)) + 0.5) - (a * (1 / b)))
    return a

def saw_bias(a):
    b = 2 * pi
    n = int(a / b)
    a -= n * b
    if a < 0:
        a += b
    return a / b

def no_bias(a):
    return a

Bias_Types = [sin_bias, cos_bias, tri_bias, saw_bias, no_bias]

def soft(a):
    return a

def sharp(a):
    return a**0.5

def sharper(a):
    return sharp(sharp(a))

Sharp_Types = [soft, sharp, sharper]

def shapes(x, y, z, shape=0):
    p = pi
    if shape == 1: 
        x = x * p
        y = y * p
        s = cos(x**2 + y**2) / (x**2 + y**2 + 0.5)
    elif shape == 2:  
        x = x * p
        y = y * p
        s = ((x * sin(x * x + y * y) + y * cos(x * x + y * y)) / (x**2 + y**2 + 0.5))
    elif shape == 3:  
        x = x * p
        y = y * p
        z = z * p
        s = 1 - ((cos(x * p) + cos(y * p) + cos(z * p)) - 0.5)
    elif shape == 4:  
        x = x * p * 2
        y = y * p * 2
        s = sin(x + sin(y))
    elif shape == 5:  
        s = (z * p)
    elif shape == 6: 
        s = (y * p)
    elif shape == 7: 
        s = (x * p)
    else:  
        s = ((x + y + z) * 5)
    return s

def marble_noise(x, y, z, origin, size, shape, bias, sharpnes, turb, depth, hard, basis, amp, freq):
    s = shapes(x, y, z, shape)
    x += origin[0]
    y += origin[1]
    z += origin[2]
    value = s + turb * turbulence_vector((x, y, z), depth, hard, noise_basis=basis)[1]

    value = Bias_Types[bias](value)
    
    if sharpnes == 1:
        value = 1.0 - Sharp_Types[0](value)
    elif sharpnes == 2:
        value = 1.0 - Sharp_Types[1](value)
    elif sharpnes == 3:
        value = Sharp_Types[0](value)
    elif sharpnes == 4:
        value = Sharp_Types[1](value)
    elif sharpnes == 5:
        value = Sharp_Types[2](value)
    else:
        value = 1.0 - Sharp_Types[0](value)

    return value

# ------------------------------------------------------------
# Advanced Noise Functions
# ------------------------------------------------------------

def vlnTurbMode(coords, distort, basis, vlbasis, hardnoise):
    if hardnoise:
        return abs(variable_lacunarity(coords, distort, noise_type1=basis, noise_type2=vlbasis))
    else:
        return variable_lacunarity(coords, distort, noise_type1=basis, noise_type2=vlbasis)

def vl_noise_turbulence(coords, distort, depth, basis, vlbasis, hardnoise, amp, freq):
    x, y, z = coords
    value = vlnTurbMode(coords, distort, basis, vlbasis, hardnoise)
    for i in range(1, depth + 1):
        value += vlnTurbMode((x * (freq * i), y * (freq * i), z * (freq * i)),
                         distort, basis, vlbasis, hardnoise) * (amp * 0.5 / i)
    return value

def double_multiFractal(coords, H, lacunarity, octaves, offset, gain, basis, vlbasis):
    x, y, z = coords
    n1 = multi_fractal((x * 1.5 + 1, y * 1.5 + 1, z * 1.5 + 1), 1.0, 1.0, 1.0, noise_basis=basis) * (offset * 0.5)
    n2 = multi_fractal((x - 1, y - 1, z - 1), H, lacunarity, octaves, noise_basis=vlbasis) * (gain * 0.5)
    return (n1 * n1 + n2 * n2) * 0.5

def distorted_heteroTerrain(coords, H, lacunarity, octaves, offset, distort, basis, vlbasis):
    x, y, z = coords
    h1 = hetero_terrain((x, y, z), 1.0, 2.0, 1.0, 1.0, noise_basis=basis) * 0.5
    d = h1 * distort
    h2 = hetero_terrain((x + d, y + d, z + d), H, lacunarity, octaves, offset, noise_basis=vlbasis) * 0.25
    return (h1 * h1 + h2 * h2) * 0.5

def slick_rock(coords, H, lacunarity, octaves, offset, gain, distort, basis, vlbasis):
    x, y, z = coords
    n = multi_fractal((x, y, z), 1.0, 2.0, 2.0, noise_basis=basis) * distort * 0.25
    r = ridged_multi_fractal((x + n, y + n, z + n), H, lacunarity, octaves, offset + 0.1, gain * 2, noise_basis=vlbasis)
    return (n + (n * r)) * 0.5

def vl_hTerrain(coords, H, lacunarity, octaves, offset, basis, vlbasis, distort):
    x, y, z = coords
    ht = hetero_terrain((x, y, z), H, lacunarity, octaves, offset, noise_basis=basis) * 0.25
    vl = ht * variable_lacunarity((x, y, z), distort, noise_type1=basis, noise_type2=vlbasis) * 0.5 + 0.5
    return vl * ht

def ant_turbulence(coords, depth, hardnoise, nbasis, amp, freq, distortion):
    x, y, z = coords
    t = turbulence_vector((x / 2, y / 2, z / 2), depth, 0, noise_basis=nbasis,
                          amplitude_scale=amp, frequency_scale=freq) * 0.5 * distortion
    return turbulence((t[0], t[1], t[2]), 2, hardnoise, noise_basis="VORONOI_F1") * 0.5 + 0.5

def rocks_noise(coords, depth, hardnoise, nbasis, distortion):
    x, y, z = coords
    p = turbulence((x, y, z), 4, 0, noise_basis='BLENDER') * 0.125 * distortion
    a = turbulence((x + p, y + p, z), 2, 0, noise_basis='VORONOI_F2F1')
    pa = a * 0.1875 * distortion
    b = turbulence((x, y, z + pa), depth, hardnoise, noise_basis=nbasis)
    return ((a + 0.5 * (b - a)) * 0.5 + 0.5)

def shattered_hterrain(coords, H, lacunarity, octaves, offset, distort, basis):
    x, y, z = coords
    d = (turbulence_vector(coords, 6, 0)[0] * 0.5 + 0.5) * distort * 0.5
    t1 = (turbulence_vector((x + d, y + d, z + d), 0, 0, noise_basis='VORONOI_F2F1')[0] + 0.5)
    t2 = (hetero_terrain((x * 2, y * 2, z * 2), H, lacunarity, octaves, offset, noise_basis=basis) * 0.5)
    return ((t1 * t2) + t2 * 0.5) * 0.5

def strata_hterrain(coords, H, lacunarity, octaves, offset, distort, basis):
    x, y, z = coords
    value = hetero_terrain((x, y, z), H, lacunarity, octaves, offset, noise_basis=basis) * 0.5
    steps = (sin(value * (distort * 5) * pi) * (0.1 / (distort * 5) * pi))
    return (value * (1.0 - 0.5) + steps * 0.5)

def planet_noise(coords, oct=6, hard=0, noisebasis='PERLIN_ORIGINAL', nabla=0.001):
    x, y, z = coords
    d = 0.001
    offset = nabla * 1000
    x = turbulence((x, y, z), oct, hard, noise_basis=noisebasis)
    y = turbulence((x + offset, y, z), oct, hard, noise_basis=noisebasis)
    z = turbulence((x, y + offset, z), oct, hard, noise_basis=noisebasis)
    xdy = x - turbulence((x, y + d, z), oct, hard, noise_basis=noisebasis)
    xdz = x - turbulence((x, y, z + d), oct, hard, noise_basis=noisebasis)
    ydx = y - turbulence((x + d, y, z), oct, hard, noise_basis=noisebasis)
    ydz = y - turbulence((x, y, z + d), oct, hard, noise_basis=noisebasis)
    zdx = z - turbulence((x + d, y, z), oct, hard, noise_basis=noisebasis)
    zdy = z - turbulence((x, y + d, z), oct, hard, noise_basis=noisebasis)
    return (zdy - ydz), (zdx - xdz), (ydx - xdy)

# ------------------------------------------------------------
# Effect System
# ------------------------------------------------------------

def Mix_Modes(a, b, mixfactor, mode):
    mode = int(mode)
    mixfactor = max(-1.0, min(1.0, mixfactor))
    f = (mixfactor + 1.0) / 2.0  

    if mode == 0:  
        return a * (1.0 - f) + b * f
    elif mode == 1:  
        return a + b * f
    elif mode == 2:  
        return a - b * f
    elif mode == 3:  
        return a * (1.0 + b * f)
    elif mode == 4:  
        return abs(a - b * f)
    elif mode == 5:  
        return 1.0 - (1.0 - a) * (1.0 - b * f)
    elif mode == 6:  
        return (a + b * f) % 1.0
    elif mode == 7:  
        return min(a, b)
    elif mode == 8:  
        return max(a, b)
    else:
        return 0.0

def Trans_Effect(coords, size, loc):
    x, y, z = coords
    x = (x * 2.0 / size) + loc[0] * 0.1
    y = (y * 2.0 / size) + loc[1] * 0.1
    return x, y, z

def Effect_Basis_Function(coords, type, bias):
    bias = int(bias)
    type = int(type)
    x, y, z = coords
    iscale = 1.0
    offset = 0.0

    # gradient:
    if type == 1:
        effect = offset + iscale * (Bias_Types[bias](x + y))
    # waves / bumps:
    elif type == 2:
        effect = offset + iscale * 0.5 * (Bias_Types[bias](x * pi) + Bias_Types[bias](y * pi))
    # zigzag:
    elif type == 3:
        effect = offset + iscale * Bias_Types[bias](offset + iscale * sin(x * pi + sin(y * pi)))
    # wavy:
    elif type == 4:
        effect = offset + iscale * (Bias_Types[bias](cos(x) + sin(y) + cos(x * 2 + y * 2) - sin(-x * 4 + y * 4)))
    # sine bump:
    elif type == 5:
        effect = offset + iscale * 1 - Bias_Types[bias]((sin(x * pi) + sin(y * pi)))
    # dots:
    elif type == 6:
        effect = offset + iscale * (Bias_Types[bias](x * pi * 2) * Bias_Types[bias](y * pi * 2)) - 0.5
    # rings:
    elif type == 7:
        effect = offset + iscale * (Bias_Types[bias](1.0 - (x * x + y * y)))
    # spiral:
    elif type == 8:
        effect = offset + iscale * \
            Bias_Types[bias]((x * sin(x * x + y * y) + y * cos(x * x + y * y)) / (x**2 + y**2 + 0.5)) * 2
    # square / piramide:
    elif type == 9:
        effect = offset + iscale * Bias_Types[bias](1.0 - sqrt((x * x)**10 + (y * y)**10)**0.1)
    # blocks:
    elif type == 10:
        effect = (0.5 - max(Bias_Types[bias](x * pi), Bias_Types[bias](y * pi)))
        if effect > 0.0:
            effect = 1.0
        effect = offset + iscale * effect
    # grid:
    elif type == 11:
        effect = (0.025 - min(Bias_Types[bias](x * pi), Bias_Types[bias](y * pi)))
        if effect > 0.0:
            effect = 1.0
        effect = offset + iscale * effect
    # tech:
    elif type == 12:
        a = max(Bias_Types[bias](x * pi), Bias_Types[bias](y * pi))
        b = max(Bias_Types[bias](x * pi * 2 + 2), Bias_Types[bias](y * pi * 2 + 2))
        effect = min(Bias_Types[bias](a), Bias_Types[bias](b)) * 3.0 - 2.0
        if effect > 0.5:
            effect = 1.0
        effect = offset + iscale * effect
    # crackle:
    elif type == 13:
        t = turbulence((x, y, 0), 6, 0, noise_basis="BLENDER") * 0.25
        effect = variable_lacunarity((x, y, t), 0.25, noise_type2='VORONOI_CRACKLE')
        if effect > 0.5:
            effect = 0.5
        effect = offset + iscale * effect
    # sparse cracks noise:
    elif type == 14:
        effect = 2.5 * abs(noise((x, y, 0), noise_basis="PERLIN_ORIGINAL")) - 0.1
        if effect > 0.25:
            effect = 0.25
        effect = offset + iscale * (effect * 2.5)
    # shattered rock noise:
    elif type == 15:
        effect = 0.5 + noise((x, y, 0), noise_basis="VORONOI_F2F1")
        if effect > 0.75:
            effect = 0.75
        effect = offset + iscale * effect
    # lunar noise:
    elif type == 16:
        effect = 0.25 + 1.5 * voronoi((x, y, 0), distance_metric='DISTANCE_SQUARED')[0][0]
        if effect > 0.5:
            effect = 0.5
        effect = offset + iscale * effect * 2
    # cosine noise:
    elif type == 17:
        effect = cos(5 * noise((x, y, 0), noise_basis="BLENDER"))
        effect = offset + iscale * (effect * 0.5)
    # spikey noise:
    elif type == 18:
        n = 0.5 + 0.5 * turbulence((x * 5, y * 5, 0), 8, 0, noise_basis="BLENDER")
        effect = ((n * n)**5)
        effect = offset + iscale * effect
    # stone noise:
    elif type == 19:
        effect = offset + iscale * (noise((x * 2, y * 2, 0), noise_basis="BLENDER") * 1.5 - 0.75)
    # Flat Turb:
    elif type == 20:
        t = turbulence((x, y, 0), 6, 0, noise_basis="BLENDER")
        effect = t * 2.0
        if effect > 0.25:
            effect = 0.25
        effect = offset + iscale * effect
    # Flat Voronoi:
    elif type == 21:
        t = 1 - voronoi((x, y, 0), distance_metric='DISTANCE_SQUARED')[0][0]
        effect = t * 2 - 1.5
        if effect > 0.25:
            effect = 0.25
        effect = offset + iscale * effect
    else:
        effect = 0.0

    if effect < 0.0:
        effect = 0.0

    return effect

def Effect_Function(coords, type, bias, turb, depth, frequency, amplitude):
    x, y, z = coords
    if turb > 0.0:
        t = turb * (0.5 + 0.5 * turbulence(coords, 6, 0, noise_basis="BLENDER"))
        x = x + t
        y = y + t
        z = z + t

    result = Effect_Basis_Function((x, y, z), type, bias) * amplitude
    if depth != 0:
        for i in range(1, depth + 1):
            x *= frequency
            y *= frequency
            result += Effect_Basis_Function((x, y, z), type, bias) * amplitude / i

    return result

# ------------------------------------------------------------
# Main Noise Generator
# ------------------------------------------------------------

def noise_gen(coords, props):
    (terrain_name, smooth_mesh, tri_face, sphere_mesh, land_material,
     water_material, texture_block, subd_x, subd_y, meshsize_x, meshsize_y, meshsize,
     random_seed, noise_offset_x, noise_offset_y, noise_offset_z, noise_size_x,
     noise_size_y, noise_size_z, nsize, ntype, nbasis, vlbasis, distortion,
     hard_noise, depth, amp, freq, dimension, lacunarity, offset, gain,
     marble_bias, marble_sharp, marble_shape, height, height_invert, height_offset,
     maximum, minimum, falloff, edge_level, falloff_x, falloff_y, stratatype,
     strata, water_plane, water_level, vert_group, remove_double, fx_mixfactor,
     fx_mix_mode, fx_type, fx_bias, fx_turb, fx_depth, fx_frequency, fx_amplitude,
     fx_size, fx_loc_x, fx_loc_y, fx_height, fx_offset, fx_invert) = props

    x, y, z = coords

    # Origin setup
    if random_seed == 0:
        origin_x, origin_y, origin_z = noise_offset_x, noise_offset_y, noise_offset_z
    else:
        seed_set(random_seed)
        origin_vec = random_unit_vector()
        origin_x = (origin_vec[0] * 50) + noise_offset_x
        origin_y = (origin_vec[1] * 50) + noise_offset_y  
        origin_z = noise_offset_z

    ncoords = (x / (nsize * noise_size_x) + origin_x, 
               y / (nsize * noise_size_y) + origin_y, 
               z / (nsize * noise_size_z) + origin_z)

    # Noise types
    if ntype == 'multi_fractal':
        value = multi_fractal(ncoords, dimension, lacunarity, depth, noise_basis=nbasis) * 0.5
    elif ntype == 'ridged_multi_fractal':
        value = ridged_multi_fractal(ncoords, dimension, lacunarity, depth, offset, gain, noise_basis=nbasis) * 0.5
    elif ntype == 'hybrid_multi_fractal':
        value = hybrid_multi_fractal(ncoords, dimension, lacunarity, depth, offset, gain, noise_basis=nbasis) * 0.5
    elif ntype == 'hetero_terrain':
        value = hetero_terrain(ncoords, dimension, lacunarity, depth, offset, noise_basis=nbasis) * 0.25
    elif ntype == 'fractal':
        value = fractal(ncoords, dimension, lacunarity, depth, noise_basis=nbasis)
    elif ntype == 'turbulence_vector':
        value = turbulence_vector(ncoords, depth, hard_noise, noise_basis=nbasis,
                                  amplitude_scale=amp, frequency_scale=freq)[0]
    elif ntype == 'variable_lacunarity':
        value = variable_lacunarity(ncoords, distortion, noise_type1=nbasis, noise_type2=vlbasis)
    elif ntype == 'marble_noise':
        value = marble_noise(
            ncoords[0] - origin_x + noise_offset_x,
            ncoords[1] - origin_y + noise_offset_y, 
            ncoords[2] - origin_z + noise_offset_z,
            (origin_x, origin_y, origin_z), nsize, marble_shape, marble_bias, 
            marble_sharp, distortion, depth, hard_noise, nbasis, amp, freq
        )
    elif ntype == 'shattered_hterrain':
        value = shattered_hterrain(ncoords, dimension, lacunarity, depth, offset, distortion, nbasis)
    elif ntype == 'strata_hterrain':
        value = strata_hterrain(ncoords, dimension, lacunarity, depth, offset, distortion, nbasis)
    elif ntype == 'ant_turbulence':
        value = ant_turbulence(ncoords, depth, hard_noise, nbasis, amp, freq, distortion)
    elif ntype == 'vl_noise_turbulence':
        value = vl_noise_turbulence(ncoords, distortion, depth, nbasis, vlbasis, hard_noise, amp, freq)
    elif ntype == 'vl_hTerrain':
        value = vl_hTerrain(ncoords, dimension, lacunarity, depth, offset, nbasis, vlbasis, distortion)
    elif ntype == 'distorted_heteroTerrain':
        value = distorted_heteroTerrain(ncoords, dimension, lacunarity, depth, offset, distortion, nbasis, vlbasis)
    elif ntype == 'double_multiFractal':
        value = double_multiFractal(ncoords, dimension, lacunarity, depth, offset, gain, nbasis, vlbasis)
    elif ntype == 'rocks_noise':
        value = rocks_noise(ncoords, depth, hard_noise, nbasis, distortion)
    elif ntype == 'slick_rock':
        value = slick_rock(ncoords, dimension, lacunarity, depth, offset, gain, distortion, nbasis, vlbasis)
    elif ntype == 'planet_noise':
        planet_result = planet_noise(ncoords, depth, hard_noise, nbasis)
        value = planet_result[2] * 0.5 + 0.5
    elif ntype == 'blender_texture':
        if texture_block != "" and texture_block in bpy.data.textures:
            value = bpy.data.textures[texture_block].evaluate(ncoords)[3]
        else:
            value = 0.0
    else:
        value = 0.5

    # Effect mix
    if fx_type != "0":
        fxcoords = Trans_Effect((x, y, z), fx_size, (fx_loc_x, fx_loc_y))
        effect = Effect_Function(fxcoords, int(fx_type), int(fx_bias), fx_turb, fx_depth, fx_frequency, fx_amplitude)
        effect = Height_Scale(effect, fx_height, fx_offset, fx_invert)
        value = Mix_Modes(value, effect, fx_mixfactor, fx_mix_mode)

    # Adjust height
    value = Height_Scale(value, height, height_offset, height_invert)

    # Edge falloff for flat terrain
    if not sphere_mesh and falloff != "0":
        ratio_x, ratio_y = abs(x) * 2 / meshsize_x, abs(y) * 2 / meshsize_y
        if falloff == "1":  # Y falloff
            dist = sqrt(ratio_y**falloff_y)
        elif falloff == "2":  # X falloff  
            dist = sqrt(ratio_x**falloff_x)
        else:  # X Y falloff
            dist = sqrt(ratio_x**falloff_x + ratio_y**falloff_y)
            
        value -= edge_level
        if dist < 1.0:
            dist = (dist * dist * (3 - 2 * dist))
            value = (value - value * dist) + edge_level
        else:
            value = edge_level

    # Strata/terracing
    if stratatype != "0":
        strata_adj = strata / height if height != 0 else strata
        if stratatype == "1":  # Smooth
            steps = (sin(value * strata_adj * pi) * (0.1 / strata_adj * pi))
            value = (value * (1.0 - 0.5) + steps * 0.5) * 2.0
        elif stratatype == "2":  # Sharp Sub
            steps = -abs(sin(value * strata_adj * pi) * (0.1 / strata_adj * pi))
            value = (value * (1.0 - 0.5) + steps * 0.5) * 2.0
        elif stratatype == "3":  # Sharp Add
            steps = abs(sin(value * strata_adj * pi) * (0.1 / strata_adj * pi))
            value = (value * (1.0 - 0.5) + steps * 0.5) * 2.0
        elif stratatype == "4":  # Quantize
            value = floor(value * strata_adj) * 1.0 / strata_adj
        elif stratatype == "5":  # Quantize Mix
            steps = floor(value * strata_adj) * 1.0 / strata_adj
            value = (value * (1.0 - 0.5) + steps * 0.5)

    # Clamp values
    value = max(minimum, min(maximum, value))

    return value

# ------------------------------------------------------------
# Erosion System
# ------------------------------------------------------------

try:
    import psutil
    psutil_available = True
except ImportError:
    psutil_available = False

class Stats:
    def __init__(self):
        self.memstats_available = False
        if psutil_available:
            self.process = psutil.Process()
            self.memstats_available = True
        self.reset()

    def reset(self):
        self.lasttime = self._gettime()
        self.lastmem = self._getmem()
        self.basemem = self.lastmem
        self.maxmem = 0
        self.elapsedtime = 0

    def _gettime(self):
        if psutil_available:
            if hasattr(self.process, "get_cpu_times"):
                m = self.process.get_cpu_times()
            else:
                m = self.process.cpu_times()
            return m.user + m.system
        return time()

    def _getmem(self):
        if psutil_available:
            if hasattr(self.process, "get_memory_info"):
                m = self.process.get_memory_info()
            else:
                m = self.process.memory_info()
            return m.rss
        return 0

    def time(self):
        old = self.lasttime
        self.lasttime = self._gettime()
        self.elapsedtime = self.lasttime - old
        return self.elapsedtime

    def memory(self):
        self.lastmem = self._getmem()
        d = self.lastmem - self.basemem
        if d > self.maxmem:
            self.maxmem = d
        return self.maxmem

try:
    import numexpr
    numexpr_available = True
except ImportError:
    numexpr_available = False

# ------------------------------------------------------------
# Grid Class 
# ------------------------------------------------------------

class Grid:
    def __init__(self, size=10, dtype=np.float32):
        self.center = np.zeros([size, size], dtype)
        self.water = None
        self.sediment = None
        self.scour = None
        self.flowrate = None
        self.sedimentpct = None
        self.capacity = None
        self.avalanced = None
        self.minx = None
        self.miny = None
        self.maxx = None
        self.maxy = None
        self.zscale = 1
        self.maxrss = 0.0
        self.sequence = [0, 1, 2, 3]
        self.watermax = 1.0
        self.flowratemax = 1.0
        self.scourmax = 1.0
        self.sedmax = 1.0
        self.scourmin = 1.0
        self.rainmap = None

    def init_water_and_sediment(self):
        if self.water is None:
            self.water = np.zeros(self.center.shape, dtype=np.float32)
        if self.sediment is None:
            self.sediment = np.zeros(self.center.shape, dtype=np.float32)
        if self.scour is None:
            self.scour = np.zeros(self.center.shape, dtype=np.float32)
        if self.flowrate is None:
            self.flowrate = np.zeros(self.center.shape, dtype=np.float32)
        if self.sedimentpct is None:
            self.sedimentpct = np.zeros(self.center.shape, dtype=np.float32)
        if self.capacity is None:
            self.capacity = np.zeros(self.center.shape, dtype=np.float32)
        if self.avalanced is None:
            self.avalanced = np.zeros(self.center.shape, dtype=np.float32)

    @staticmethod
    def fromBlenderMesh(me, vg, expfact):
        g = Grid()
        g.center = np.asarray([(v.co.x, v.co.y, v.co.z) for v in me.vertices], dtype=np.float32)
        g.rainmap = None
        
        if vg is not None:
            rainmap_weights = np.zeros(len(me.vertices), dtype=np.float32)
            
            vg_index = vg.index
            
            for i, v in enumerate(me.vertices):
                weight = 0.0
                for vg_elem in v.groups:
                    if vg_elem.group == vg_index:
                        weight = vg_elem.weight
                        break
                rainmap_weights[i] = weight
            
            g.rainmap = np.asarray([
                (v.co.x, v.co.y, rainmap_weights[i]) 
                for i, v in enumerate(me.vertices)
            ], dtype=np.float32)
        
        g._sort(expfact)
        return g

    def _sort(self, expfact):
        verts = sorted(list({tuple(t) for t in self.center}))
        x = set(c[0] for c in verts)
        y = set(c[1] for c in verts)
        nx = len(x)
        ny = len(y)
        self.minx = min(x)
        self.maxx = max(x)
        self.miny = min(y)
        self.maxy = max(y)
        
        self.center = np.array([c[2] for c in verts], dtype=np.float32).reshape(nx, ny)
        self.center = (self.center - np.amin(self.center)) * self.zscale
        
        if self.rainmap is not None:
            rmscale = np.max(self.center)
            self.rainmap = expfact + (1 - expfact) * (self.center / rmscale)

    def toBlenderMesh(self, me):
        nrow, ncol = self.center.shape
        minx = 0.0 if self.minx is None else self.minx
        miny = 0.0 if self.miny is None else self.miny
        maxx = 1.0 if self.maxx is None else self.maxx
        maxy = 1.0 if self.maxy is None else self.maxy
        dx = (maxx - minx) / (nrow - 1)
        dy = (maxy - miny) / (ncol - 1)
        
        verts = []
        for row in range(nrow):
            row0 = miny + row * dy
            for col in range(ncol):
                col0 = minx + col * dx
                verts.append((row0, col0, self.center[row, col] / self.zscale))
        
        faces = []
        for row in range(nrow - 1):
            for col in range(ncol - 1):
                vi = row * ncol + col
                faces.append((vi, vi + ncol, vi + 1))
                faces.append((vi + 1, vi + ncol, vi + ncol + 1))
        
        me.clear_geometry()
        me.from_pydata(verts, [], faces)

    def zeroedge(self, quantity=None):
        c = self.center if quantity is None else quantity
        c[0, :] = 0
        c[-1, :] = 0
        c[:, 0] = 0
        c[:, -1] = 0

    def diffuse(self, Kd, IterDiffuse, numexpr):
        self.zeroedge()
        c = self.center[1:-1, 1:-1]
        up = self.center[:-2, 1:-1]
        down = self.center[2:, 1:-1]
        left = self.center[1:-1, :-2]
        right = self.center[1:-1, 2:]
        
        if numexpr and numexpr_available:
            import numexpr as ne
            self.center[1:-1, 1:-1] = ne.evaluate('c + Kd * (up + down + left + right - 4.0 * c)')
        else:
            self.center[1:-1, 1:-1] = c + (Kd / IterDiffuse) * (up + down + left + right - 4.0 * c)
        
        return self.center

    def avalanche(self, delta, iterava, prob, numexpr):
        self.zeroedge()
        c = self.center[1:-1, 1:-1]
        up = self.center[:-2, 1:-1]
        down = self.center[2:, 1:-1]
        left = self.center[1:-1, :-2]
        right = self.center[1:-1, 2:]
        
        if numexpr and numexpr_available:
            import numexpr as ne
            self.center[1:-1, 1:-1] = ne.evaluate('''c + 
                where((up - c) > delta, (up - c - delta)/2, 0) +
                where((down - c) > delta, (down - c - delta)/2, 0) +
                where((left - c) > delta, (left - c - delta)/2, 0) +
                where((right - c) > delta, (right - c - delta)/2, 0) +
                where((up - c) < -delta, (up - c + delta)/2, 0) +
                where((down - c) < -delta, (down - c + delta)/2, 0) +
                where((left - c) < -delta, (left - c + delta)/2, 0) +
                where((right - c) < -delta, (right - c + delta)/2, 0)''')
        else:
            sa = (
                np.where((up - c) > delta, (up - c - delta) / 2, 0) +
                np.where((down - c) > delta, (down - c - delta) / 2, 0) +
                np.where((left - c) > delta, (left - c - delta) / 2, 0) +
                np.where((right - c) > delta, (right - c - delta) / 2, 0) +
                np.where((up - c) < -delta, (up - c + delta) / 2, 0) +
                np.where((down - c) < -delta, (down - c + delta) / 2, 0) +
                np.where((left - c) < -delta, (left - c + delta) / 2, 0) +
                np.where((right - c) < -delta, (right - c + delta) / 2, 0)
            )
            randarray = np.random.randint(0, 100, sa.shape) * 0.01
            sa = np.where(randarray < prob, sa, 0)
            self.avalanced[1:-1, 1:-1] = self.avalanced[1:-1, 1:-1] + sa / iterava
            self.center[1:-1, 1:-1] = c + sa / iterava
        
        return self.center

    def rain(self, amount=1, variance=0, userainmap=False):
        if self.water is None:
            self.init_water_and_sediment()
        
        if userainmap and self.rainmap is not None:
            self.water += (1.0 - np.random.random(self.water.shape) * variance) * self.rainmap * amount
        else:
            self.water += (1.0 - np.random.random(self.water.shape) * variance) * amount

    def river(self, Kc, Ks, Kdep, Ka, Kev, numexpr):
        self.init_water_and_sediment()
        
        center = (slice(1, -1, None), slice(1, -1, None))
        up = (slice(None, -2, None), slice(1, -1, None))
        down = (slice(2, None, None), slice(1, -1, None))
        left = (slice(1, -1, None), slice(None, -2, None))
        right = (slice(1, -1, None), slice(2, None, None))

        water = self.water
        rock = self.center
        sediment = self.sediment
        height = rock + water

        verysmallnumber = 0.0000000001
        water += verysmallnumber
        sc = np.where(water > verysmallnumber, sediment / water, 0)

        sdw = np.zeros(water[center].shape)
        svdw = np.zeros(water[center].shape)
        sds = np.zeros(water[center].shape)
        angle = np.zeros(water[center].shape)
        
        for d in (up, down, left, right):
            hdd = height[d]
            hcc = height[center]
            dw = hdd - hcc
            inflow = dw > 0
            wdd = water[d]
            wcc = water[center]
            dw = np.where(inflow, np.minimum(wdd, dw), np.maximum(-wcc, dw)) / 4.0
            sdw = sdw + dw
            scd = sc[d]
            scc = sc[center]
            sds = sds + dw * np.where(inflow, scd, scc)
            svdw = svdw + np.abs(dw)
            rockd = rock[d]
            rockc = rock[center]
            angle = angle + np.arctan(np.abs(rockd - rockc))

        wcc = water[center]
        scc = sediment[center]
        rcc = rock[center]
        
        water[center] = wcc * (1 - Kev) + sdw
        sediment[center] = scc + sds
        sc = np.where(wcc > 0, scc / wcc, 2 * Kc)
        fKc = Kc * svdw
        ds = np.where(fKc > sc, (fKc - sc) * Ks, (fKc - sc) * Kdep) * wcc
        
        self.flowrate[center] = svdw
        self.scour[center] = ds
        self.sedimentpct[center] = sc
        self.capacity[center] = fKc
        sediment[center] = scc + ds + sds

    def flow(self, Kc, Ks, Kz, Ka, numexpr):
        center = (slice(1, -1, None), slice(1, -1, None))
        rock = self.center
        ds = self.scour[center]
        rcc = rock[center]
        rock[center] = rcc - ds * Kz
        rock[center] = np.where(rcc < 0, 0, rcc)

    def rivergeneration(self, rainamount, rainvariance, userainmap, Kc, Ks, Kdep, Ka, Kev, Kspring, Kspringx, Kspringy, Kspringr, numexpr):
        self.init_water_and_sediment()
        self.rain(rainamount, rainvariance, userainmap)
        self.zeroedge(self.water)
        self.zeroedge(self.sediment)
        self.river(Kc, Ks, Kdep, Ka, Kev, numexpr)
        self.watermax = np.max(self.water)

    def fluvial_erosion(self, rainamount, rainvariance, userainmap, Kc, Ks, Kdep, Ka, Kspring, Kspringx, Kspringy, Kspringr, numexpr):
        self.flow(Kc, Ks, Kdep, Ka, numexpr)
        self.flowratemax = np.max(self.flowrate)
        self.scourmax = np.max(self.scour)
        self.scourmin = np.min(self.scour)
        self.sedmax = np.max(self.sediment)

    def analyze(self):
        up = np.roll(self.center, -1, 0)
        left = np.roll(self.center, -1, 1)
        slopes = np.concatenate((np.abs(left - self.center), np.abs(up - self.center)))
        
        return '\n'.join(["%-15s: %.3f" % t for t in [
            ('height average', np.average(self.center)),
            ('height median', np.median(self.center)),
            ('height max', np.max(self.center)),
            ('height min', np.min(self.center)),
            ('height std', np.std(self.center)),
            ('slope average', np.average(slopes)),
            ('slope median', np.median(slopes)),
            ('slope max', np.max(slopes)),
            ('slope min', np.min(slopes)),
            ('slope std', np.std(slopes))
        ]])

# ------------------------------------------------------------
# Landscape Generation Functions
# ------------------------------------------------------------

def generate_landscape_mesh(context, props):
    active = get_active_landscape(context)
    existing = active and active.get("landscape_generator")
    terrain_name = active.name if existing else props.ant_terrain_name or "Landscape"

    try:
        prop_list = _make_prop_list(props)
        if props.sphere_mesh:
            verts, faces = sphere_gen(props.subdivision_y, props.subdivision_x, props.tri_face, props.mesh_size, prop_list, False, 0.0)
        else:
            verts, faces = grid_gen(props.subdivision_x, props.subdivision_y, props.tri_face, props.mesh_size_x, props.mesh_size_y, prop_list, False, 0.0)
    except Exception as e:
        print("Landscape generation failed:", e)
        return active or None

    if existing:
        obj, mesh = active, active.data
        mesh.clear_geometry()
    else:
        mesh = bpy.data.meshes.new(terrain_name + "_mesh")
        obj = bpy.data.objects.new(terrain_name, mesh)
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        obj["landscape_generator"] = True

    if verts and faces:
        mesh.from_pydata(verts, [], faces)
        mesh.update()
    else:
        print("No geometry generated.")
        return obj

    for attr in dir(props):
        if not attr.startswith(("_", "bl_")) and attr not in {'rna_type', 'refresh', 'auto_refresh'}:
            try: obj[attr] = getattr(props, attr)
            except: pass

    if props.smooth_mesh:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

    if props.land_material and props.land_material in bpy.data.materials:
        mat = bpy.data.materials[props.land_material]
        if obj.data.materials: obj.data.materials[0] = mat
        else: obj.data.materials.append(mat)

    if props.water_plane:
        try:
            if props.sphere_mesh:
                wv, wf = sphere_gen(props.subdivision_y, props.subdivision_x, props.tri_face, props.mesh_size, prop_list, True, props.water_level)
            else:
                wv, wf = grid_gen(2, 2, props.tri_face, props.mesh_size_x, props.mesh_size_y, prop_list, True, props.water_level)
        except Exception as e:
            print("Water generation failed:", e)
            wv, wf = [], []

        water_obj = next((c for c in obj.children if c.name.endswith("_Water")), None)
        if not water_obj:
            wmesh = bpy.data.meshes.new(terrain_name + "_water")
            water_obj = bpy.data.objects.new(terrain_name + "_Water", wmesh)
            context.collection.objects.link(water_obj)
            water_obj.parent = obj
        else:
            wmesh = water_obj.data
            wmesh.clear_geometry()

        if wv and wf:
            wmesh.from_pydata(wv, [], wf)
            wmesh.update()

        if props.water_material and props.water_material in bpy.data.materials:
            wmat = bpy.data.materials[props.water_material]
            if water_obj.data.materials: water_obj.data.materials[0] = wmat
            else: water_obj.data.materials.append(wmat)

        if props.smooth_mesh:
            bpy.context.view_layer.objects.active = water_obj
            bpy.ops.object.shade_smooth()
            bpy.context.view_layer.objects.active = obj

    return obj

def update_landscape(self, context):
    if not context.scene.landscape_props.live_update: return
    obj = context.active_object
    if not (obj and obj.type == "MESH" and "landscape_generator" in obj): return
    props = context.scene.landscape_props
    old_loc, old_rot, old_scale = obj.location.copy(), obj.rotation_euler.copy(), obj.scale.copy()
    try: rebuild_landscape_in_place(context, obj, props)
    except Exception as e:
        print("Live update failed:", e)
        return
    obj.location, obj.rotation_euler, obj.scale = old_loc, old_rot, old_scale

# ------------------------------------------------------------
# Property Groups
# ------------------------------------------------------------

class LandscapeProperties(bpy.types.PropertyGroup):
    
    # Live Update
    live_update: bpy.props.BoolProperty(name="Live Update", default=False, description="Update landscape in real-time as parameters change", update=update_landscape)

    # Main Settings
    ant_terrain_name: bpy.props.StringProperty(name="Name", default="Landscape", update=update_landscape)
    smooth_mesh: bpy.props.BoolProperty(name="Smooth", default=False, description="Shade smooth", update=update_landscape)
    tri_face: bpy.props.BoolProperty(name="Triangulate", default=False, description="Triangulate faces", update=update_landscape)
    sphere_mesh: bpy.props.BoolProperty(name="Sphere", default=False, description="Generate sphere instead of plane", update=update_landscape)
    remove_double: bpy.props.BoolProperty(name="Remove Doubles", default=False, description="Remove duplicate vertices", update=update_landscape)

    # Mesh Settings
    subdivision_x: bpy.props.IntProperty(name="Subdivisions X", default=128, min=4, max=2000, update=update_landscape)
    subdivision_y: bpy.props.IntProperty(name="Subdivisions Y", default=128, min=4, max=2000, update=update_landscape)
    mesh_size_x: bpy.props.FloatProperty(name="Size X", default=2.0, min=0.1, max=100.0, update=update_landscape)
    mesh_size_y: bpy.props.FloatProperty(name="Size Y", default=2.0, min=0.1, max=100.0, update=update_landscape)
    mesh_size: bpy.props.FloatProperty(name="Size", default=2.0, min=0.1, max=100.0, update=update_landscape)

    # Material Settings
    land_material: bpy.props.StringProperty(name="Land Material", default="", update=update_landscape)
    water_material: bpy.props.StringProperty(name="Water Material", default="", update=update_landscape)
    texture_block: bpy.props.StringProperty(name="Texture", default="", update=update_landscape)
    water_plane: bpy.props.BoolProperty(name="Water Plane", default=False, update=update_landscape)
    water_level: bpy.props.FloatProperty(name="Water Level", default=0.0, update=update_landscape)

    # Noise Settings
    random_seed: bpy.props.IntProperty(name="Seed", default=0, min=0, max=10000, update=update_landscape)
    noise_type: bpy.props.EnumProperty(name="Noise Type", items=[('multi_fractal',"Multi Fractal","Blender: Multi Fractal algorithm"),('ridged_multi_fractal',"Ridged MFractal","Blender: Ridged Multi Fractal"),('hybrid_multi_fractal',"Hybrid MFractal","Blender: Hybrid Multi Fractal"),('hetero_terrain',"Hetero Terrain","Blender: Hetero Terrain"),('fractal',"fBm Fractal","Blender: fBm - Fractional Brownian motion"),('turbulence_vector',"Turbulence","Blender: Turbulence Vector"),('variable_lacunarity',"Distorted Noise","Blender: Distorted Noise"),('marble_noise',"Marble","A.N.T.: Marble Noise"),('shattered_hterrain',"Shattered hTerrain","A.N.T.: Shattered hTerrain"),('strata_hterrain',"Strata hTerrain","A.N.T: Strata hTerrain"),('ant_turbulence',"Another Noise","A.N.T: Turbulence variation"),('vl_noise_turbulence',"vlNoise turbulence","A.N.T: Real vlNoise turbulence"),('vl_hTerrain',"vlNoise hTerrain","A.N.T: vlNoise hTerrain"),('distorted_heteroTerrain',"Distorted hTerrain","A.N.T distorted hTerrain"),('double_multiFractal',"Double MultiFractal","A.N.T: double multiFractal"),('rocks_noise',"Noise Rocks","A.N.T: turbulence variation"),('slick_rock',"Slick Rock","A.N.T: slick rock"),('planet_noise',"Planet Noise","Planet Noise by: Farsthary"),('blender_texture',"Blender Texture","Blender texture data block")], default='hetero_terrain', update=update_landscape)
    basis_type: bpy.props.EnumProperty(name="Basis", items=noise_basis, default=noise_basis_default, update=update_landscape)
    vl_basis_type: bpy.props.EnumProperty(name="VL Basis", items=noise_basis, default=noise_basis_default, update=update_landscape)

    # Noise Parameters
    noise_offset_x: bpy.props.FloatProperty(name="Offset X", default=0.0, update=update_landscape)
    noise_offset_y: bpy.props.FloatProperty(name="Offset Y", default=0.0, update=update_landscape)
    noise_offset_z: bpy.props.FloatProperty(name="Offset Z", default=0.0, update=update_landscape)
    noise_size_x: bpy.props.FloatProperty(name="Size X", default=1.0, min=0.01, max=10.0, update=update_landscape)
    noise_size_y: bpy.props.FloatProperty(name="Size Y", default=1.0, min=0.01, max=10.0, update=update_landscape)
    noise_size_z: bpy.props.FloatProperty(name="Size Z", default=1.0, min=0.01, max=10.0, update=update_landscape)
    noise_size: bpy.props.FloatProperty(name="Noise Size", default=1.0, min=0.01, max=10.0, update=update_landscape)
    noise_depth: bpy.props.IntProperty(name="Depth", default=8, min=1, max=16, update=update_landscape)
    dimension: bpy.props.FloatProperty(name="Dimension", default=1.0, min=0.01, max=2.0, update=update_landscape)
    lacunarity: bpy.props.FloatProperty(name="Lacunarity", default=2.0, min=0.01, max=6.0, update=update_landscape)
    offset: bpy.props.FloatProperty(name="Offset", default=1.0, min=0.01, max=6.0, update=update_landscape)
    gain: bpy.props.FloatProperty(name="Gain", default=1.0, min=0.01, max=6.0, update=update_landscape)
    distortion: bpy.props.FloatProperty(name="Distortion", default=1.0, min=0.01, max=10.0, update=update_landscape)
    hard_noise: bpy.props.EnumProperty(name="Noise Type", items=[("0","Soft","Soft Noise"),("1","Hard","Hard noise")], default="0", update=update_landscape)
    amplitude: bpy.props.FloatProperty(name="Amplitude", default=0.5, min=0.01, max=1.0, update=update_landscape)
    frequency: bpy.props.FloatProperty(name="Frequency", default=2.0, min=0.01, max=5.0, update=update_landscape)

    # Marble Settings
    marble_bias: bpy.props.EnumProperty(name="Marble Bias", items=[("0","Sin","Sin"),("1","Cos","Cos"),("2","Tri","Tri"),("3","Saw","Saw")], default="0", update=update_landscape)
    marble_sharp: bpy.props.EnumProperty(name="Marble Sharp", items=[("0","Soft","Soft"),("1","Sharp","Sharp"),("2","Sharper","Sharper"),("3","Soft inv.","Soft"),("4","Sharp inv.","Sharp"),("5","Sharper inv.","Sharper")], default="0", update=update_landscape)
    marble_shape: bpy.props.EnumProperty(name="Marble Shape", items=[("0","Default","Default"),("1","Ring","Ring"),("2","Swirl","Swirl"),("3","Bump","Bump"),("4","Wave","Wave"),("5","Z","Z"),("6","Y","Y"),("7","X","X")], default="0", update=update_landscape)

    # Height Settings
    height: bpy.props.FloatProperty(name="Height", default=0.5, min=0, max=10.0, update=update_landscape)
    height_invert: bpy.props.BoolProperty(name="Invert", default=False, update=update_landscape)
    height_offset: bpy.props.FloatProperty(name="Offset", default=0.0, min=-10, max=10.0, update=update_landscape)
    maximum: bpy.props.FloatProperty(name="Maximum", default=1.0, min=-10, max=10.0, update=update_landscape)
    minimum: bpy.props.FloatProperty(name="Minimum", default=-1.0, min=-10, max=10.0, update=update_landscape)

    # Edge Falloff
    edge_falloff: bpy.props.EnumProperty(name="Falloff", items=[("0","None","None"),("1","Y","Y Falloff"),("2","X","X Falloff"),("3","X Y","X Y Falloff")], default="0", update=update_landscape)
    edge_level: bpy.props.FloatProperty(name="Edge Level", default=0.0, update=update_landscape)
    falloff_x: bpy.props.FloatProperty(name="Falloff X", default=4.0, min=0.1, max=100.0, update=update_landscape)
    falloff_y: bpy.props.FloatProperty(name="Falloff Y", default=4.0, min=0.1, max=100.0, update=update_landscape)

    # Strata Settings
    strata_type: bpy.props.EnumProperty(name="Strata", items=[("0","None","No strata"),("1","Smooth","Smooth transitions"),("2","Sharp Sub","Sharp subtract transitions"),("3","Sharp Add","Sharp add transitions"),("4","Quantize","Quantize"),("5","Quantize Mix","Quantize mixed")], default="0", update=update_landscape)
    strata: bpy.props.FloatProperty(name="Strata Amount", default=5.0, min=0.1, max=50.0, update=update_landscape)

    # Effect Settings
    fx_mixfactor: bpy.props.FloatProperty(name="Mix Factor", default=0.0, min=-1.0, max=1.0, update=update_landscape)
    fx_mix_mode: bpy.props.EnumProperty(name="Mix Mode", items=[("0","Mix","Mix"),("1","Add","Add"),("2","Subtract","Subtract"),("3","Multiply","Multiply"),("4","Absolute","Absolute"),("5","Screen","Screen"),("6","Modulo","Modulo"),("7","Minimum","Minimum"),("8","Maximum","Maximum")], default="0", update=update_landscape)
    fx_type: bpy.props.EnumProperty(name="Effect Type", items=[("0","None","No effect"),("1","Gradient","Gradient"),("2","Waves","Waves - Bumps"),("3","Zigzag","Zigzag"),("4","Wavy","Wavy"),("5","Bump","Bump"),("6","Dots","Dots"),("7","Rings","Rings"),("8","Spiral","Spiral"),("9","Square","Square"),("10","Blocks","Blocks"),("11","Grid","Grid"),("12","Tech","Tech"),("13","Crackle","Crackle"),("14","Cracks","Cracks"),("15","Rock","Rock noise"),("16","Lunar","Craters"),("17","Cosine","Cosine"),("18","Spikey","Spikey"),("19","Stone","Stone"),("20","Flat Turb","Flat turbulence"),("21","Flat Voronoi","Flat voronoi")], default="0", update=update_landscape)
    fx_bias: bpy.props.EnumProperty(name="Effect Bias", items=[("0","Sin","Sin"),("1","Cos","Cos"),("2","Tri","Tri"),("3","Saw","Saw"),("4","None","None")], default="0", update=update_landscape)
    fx_turb: bpy.props.FloatProperty(name="Turbulence", default=0.0, min=0.0, max=10.0, update=update_landscape)
    fx_depth: bpy.props.IntProperty(name="Effect Depth", default=0, min=0, max=16, update=update_landscape)
    fx_frequency: bpy.props.FloatProperty(name="Effect Frequency", default=2.0, min=0.01, max=5.0, update=update_landscape)
    fx_amplitude: bpy.props.FloatProperty(name="Effect Amplitude", default=0.5, min=0.01, max=1.0, update=update_landscape)
    fx_size: bpy.props.FloatProperty(name="Effect Size", default=1.0, min=0.01, max=10.0, update=update_landscape)
    fx_loc_x: bpy.props.FloatProperty(name="Effect X", default=0.0, update=update_landscape)
    fx_loc_y: bpy.props.FloatProperty(name="Effect Y", default=0.0, update=update_landscape)
    fx_height: bpy.props.FloatProperty(name="Effect Height", default=1.0, min=0, max=10.0, update=update_landscape)
    fx_offset: bpy.props.FloatProperty(name="Effect Offset", default=0.0, min=-10.0, max=10.0, update=update_landscape)
    fx_invert: bpy.props.BoolProperty(name="Effect Invert", default=False, update=update_landscape)

    # Other
    vert_group: bpy.props.StringProperty(name="Vertex Group", default="", update=update_landscape)

    # UI Toggles
    show_main_settings: bpy.props.BoolProperty(name="Show Main Settings", default=False)
    show_noise_settings: bpy.props.BoolProperty(name="Show Noise Settings", default=False)
    show_height_settings: bpy.props.BoolProperty(name="Show Height Settings", default=False)
    show_effect_settings: bpy.props.BoolProperty(name="Show Effect Settings", default=False)
    show_advanced_settings: bpy.props.BoolProperty(name="Show Advanced Settings", default=False)
    show_tools: bpy.props.BoolProperty(name="Show Tools", description="Show or hide the tools section", default=False)
    show_erosion_settings: bpy.props.BoolProperty(name="Show Erosion Settings", default=False)
    
    # Erosion Settings
    use_erosion: bpy.props.BoolProperty(name="Enable Erosion", description="Enable terrain erosion simulation", default=False, update=update_landscape)
    Iterations: bpy.props.IntProperty(name="Iterations", description="Number of overall iterations", default=1, min=1, soft_max=100)
    IterRiver: bpy.props.IntProperty(name="River Iterations", description="Number of river iterations", default=30, min=1, soft_max=1000)
    IterAva: bpy.props.IntProperty(name="Avalanche Iterations", description="Number of avalanche iterations", default=5, min=1, soft_max=10)
    IterDiffuse: bpy.props.IntProperty(name="Diffuse Iterations", description="Number of diffuse iterations", default=5, min=1, soft_max=10)
    Ef: bpy.props.FloatProperty(name="Rain on Plains", description="1 gives equal rain across the terrain, 0 rains more at mountain tops", default=0.0, min=0, max=1)
    Kd: bpy.props.FloatProperty(name="Kd (Thermal Diffusion Rate)", description="Thermal diffusion rate", default=0.1, min=0, soft_max=100)
    Kt: bpy.props.FloatProperty(name="Kt (Max Stable Talus Angle)", description="Maximum stable talus angle", default=radians(60), min=0, max=radians(90), subtype='ANGLE')
    Kr: bpy.props.FloatProperty(name="Rain Amount", description="Total rain amount", default=0.01, min=0, soft_max=1, precision=3)
    Kv: bpy.props.FloatProperty(name="Rain Variance", description="Rain variance (0 is constant, 1 is uniform)", default=0.0, min=0, max=1)
    userainmap: bpy.props.BoolProperty(name="Use Rain Map", description="Use active vertex group as a rain map", default=True)
    Ks: bpy.props.FloatProperty(name="Soil Solubility", description="Soil solubility", default=0.5, min=0, soft_max=1)
    Kdep: bpy.props.FloatProperty(name="Deposition Rate", description="Sediment deposition rate", default=0.1, min=0, soft_max=1)
    Kz: bpy.props.FloatProperty(name="Fluvial Erosion Rate", description="Amount of sediment moved each main iteration", default=0.3, min=0, soft_max=20)
    Kc: bpy.props.FloatProperty(name="Carrying Capacity", description="Base sediment carrying capacity", default=0.9, min=0, soft_max=1)
    Ka: bpy.props.FloatProperty(name="Slope Dependence", description="Slope dependence of carrying capacity", default=1.0, min=0, soft_max=2)
    Kev: bpy.props.FloatProperty(name="Evaporation", description="Evaporation rate per grid square in %", default=0.5, min=0, soft_max=2)
    numexpr: bpy.props.BoolProperty(name="Numexpr", description="Use numexpr module (if available)", default=True)
    Pd: bpy.props.FloatProperty(name="Diffusion Amount", description="Diffusion probability", default=0.2, min=0, max=1)
    Pa: bpy.props.FloatProperty(name="Avalanche Amount", description="Avalanche amount", default=0.5, min=0, max=1)
    Pw: bpy.props.FloatProperty(name="River Amount", description="Water erosion probability", default=1.0, min=0, max=1)
    smooth: bpy.props.BoolProperty(name="Smooth", description="Set smooth shading", default=True)
    showiterstats: bpy.props.BoolProperty(name="Iteration Stats", description="Show iteration statistics", default=False)
    showmeshstats: bpy.props.BoolProperty(name="Mesh Stats", description="Show mesh statistics", default=False)

# ------------------------------------------------------------
# Operators
# ------------------------------------------------------------

class LANDSCAPE_OT_generate(bpy.types.Operator):
    bl_idname = "landscape.generate"
    bl_label = "Generate Landscape"
    bl_description = "Create a landscape if none is selected, otherwise update the selected landscape"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.landscape_props
        obj = context.active_object

        keys = (
            "mesh_size_x", "mesh_size_y",
            "subdivision_x", "subdivision_y",
            "height", "height_offset",
            "amplitude", "frequency",
            "noise_type", "basis_type", "vl_basis_type",
            "noise_size", "noise_offset_x", "noise_offset_y",
            "fx_mixfactor", "fx_mix_mode", "fx_type",
            "fx_height", "fx_offset", "fx_invert",
        )

        if obj and obj.type == "MESH" and "landscape_generator" in obj and obj.select_get():
            for k in keys:
                obj[k] = getattr(props, k)
            rebuild_landscape_in_place(context, obj, props)
            obj.name = obj.data.name = f"Landscape_{props.noise_type}"
            self.report({'INFO'}, f"Updated Landscape: {obj.name}")
            return {"FINISHED"}

        mesh = bpy.data.meshes.new("LandscapeMesh")
        new_obj = bpy.data.objects.new("Landscape", mesh)
        context.collection.objects.link(new_obj)
        context.view_layer.objects.active = new_obj
        new_obj.select_set(True)

        for k in keys:
            new_obj[k] = getattr(props, k)

        new_obj["landscape_generator"] = True
        rebuild_landscape_in_place(context, new_obj, props)
        new_obj.name = new_obj.data.name = f"Landscape_{props.noise_type}"

        self.report({'INFO'}, f"Created new Landscape: {new_obj.name}")
        return {"FINISHED"}

    
class LANDSCAPE_OT_reset_settings(bpy.types.Operator):
    bl_idname = "landscape.reset_settings"
    bl_label = "Reset Sliders"
    bl_description = "Reset only modified sliders to their default values (excluding Live Update and UI toggles)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.landscape_props
        live = p.live_update

        globals()["_BATCH_EDIT"] = True
        try:
            prop_defs = type(p).bl_rna.properties
            changed_keys = []

            exclude_keys = {
                "live_update",
                "show_main_settings", "show_noise_settings", "show_height_settings",
                "show_effect_settings", "show_advanced_settings", "show_tools",
                "show_erosion_settings",
            }

            for key, prop in prop_defs.items():
                if key in exclude_keys or key.startswith(("bl_", "_")) or key in {'rna_type', 'refresh', 'auto_refresh'}:
                    continue

                if not hasattr(prop, "default"):
                    continue

                try:
                    current_value = getattr(p, key)
                    default_value = prop.default

                    if current_value != default_value:
                        setattr(p, key, default_value)
                        changed_keys.append(key)
                except Exception:
                    pass

        finally:
            globals()["_BATCH_EDIT"] = False

        if live and changed_keys:
            obj = context.active_object
            if obj and obj.type == "MESH" and "landscape_generator" in obj and obj.select_get():
                update_landscape(p, context)

        if changed_keys:
            self.report({'INFO'}, f"Reset {len(changed_keys)} changed sliders to default.")
        else:
            self.report({'INFO'}, "No sliders were changed (already at defaults).")

        return {'FINISHED'}

class LANDSCAPE_OT_delete(bpy.types.Operator):
    bl_idname = "landscape.delete"
    bl_label = "Delete Landscape"
    bl_description = "Delete selected landscape object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if obj and "landscape_generator" in obj:
            children = [child for child in obj.children if "Water" in child.name]
            for child in children:
                bpy.data.objects.remove(child, do_unlink=True)
            bpy.data.objects.remove(obj, do_unlink=True)
        return {'FINISHED'}

# ------------------------------------------------------------
# Operators - Fix poll methods
# ------------------------------------------------------------

class LANDSCAPE_OT_refresh(bpy.types.Operator):
    bl_idname = "landscape.refresh"
    bl_label = "Refresh Landscape"
    bl_description = "Refresh landscape with current settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        props = getattr(context.scene, "landscape_props", None)
        return bool(obj and obj.type == 'MESH' and "landscape_generator" in obj and props and not props.sphere_mesh)
    
    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.type == 'MESH' or "landscape_generator" not in obj:
            return {'CANCELLED'}
            
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        props = context.scene.landscape_props
        prop_list = _make_prop_list(props)
        
        mesh = obj.data
        if props.vert_group != "" and props.vert_group in obj.vertex_groups:
            vertex_group = obj.vertex_groups[props.vert_group]
            gi = vertex_group.index
            for v in mesh.vertices:
                for g in v.groups:
                    if g.group == gi:
                        v.co.z = vertex_group.weight(v.index) * noise_gen(v.co, prop_list)
        else:
            for v in mesh.vertices:
                v.co.z = noise_gen(v.co, prop_list)
                
        mesh.update()
        return {'FINISHED'}

class LANDSCAPE_OT_regenerate(bpy.types.Operator):
    bl_idname = "landscape.regenerate"
    bl_label = "Regenerate Landscape"
    bl_description = "Regenerate landscape with current settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and "landscape_generator" in obj)
    
    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.type == 'MESH' or "landscape_generator" not in obj:
            return {'CANCELLED'}
            
        old_location = obj.location.copy()
        old_rotation = obj.rotation_euler.copy()
        
        props = context.scene.landscape_props
        new_obj = generate_landscape_mesh(context, props)
        
        new_obj.location = old_location
        new_obj.rotation_euler = old_rotation
        
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        bpy.data.objects.remove(obj, do_unlink=True)
        
        return {'FINISHED'}

# ------------------------------------------------------------
# Erosion Operator 
# ------------------------------------------------------------

class LANDSCAPE_OT_eroder(bpy.types.Operator):
    bl_idname = "landscape.eroder"
    bl_label = "Landscape Eroder"
    bl_description = "Apply erosion to landscape"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        props = getattr(context.scene, "landscape_props", None)
        return obj and obj.type == 'MESH' and "landscape_generator" in obj and props and not props.sphere_mesh

    def execute(self, context):
        props = context.scene.landscape_props
        ob = context.active_object
        if not ob or ob.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected")
            return {'CANCELLED'}

        oldMesh = ob.data
        stats = Stats(); stats.reset()

        maps = {
            'rainmap': lambda g, r, c: g.rainmap[r, c] if g.rainmap is not None else 0,
            'scree': lambda g, r, c: g.avalanced[r, c],
            'avalanced': lambda g, r, c: -g.avalanced[r, c],
            'water': lambda g, r, c: g.water[r, c] / g.watermax if g.watermax > 0 else 0,
            'scour': lambda g, r, c: g.scour[r, c] / max(g.scourmax, -g.scourmin) if max(g.scourmax, -g.scourmin) > 0 else 0,
            'deposit': lambda g, r, c: g.scour[r, c] / min(-g.scourmax, g.scourmin) if min(-g.scourmax, g.scourmin) > 0 else 0,
            'flowrate': lambda g, r, c: g.flowrate[r, c],
            'sediment': lambda g, r, c: g.sediment[r, c],
            'sedimentpct': lambda g, r, c: g.sedimentpct[r, c],
            'capacity': lambda g, r, c: g.capacity[r, c]
        }

        for name in maps:
            if name not in ob.vertex_groups:
                ob.vertex_groups.new(name=name)
        rainmap_vg = ob.vertex_groups.get('rainmap')
        g = Grid.fromBlenderMesh(oldMesh, rainmap_vg, props.Ef)

        for i in range(props.Iterations):
            if props.IterRiver > 0:
                for _ in range(props.IterRiver):
                    g.rivergeneration(props.Kr, props.Kv, props.userainmap, props.Kc, props.Ks, props.Kdep, props.Ka, props.Kev / 100, 0, 0, 0, 0, props.numexpr)
            if props.Kd > 0.0:
                for _ in range(props.IterDiffuse):
                    g.diffuse(props.Kd / 5, props.IterDiffuse, props.numexpr)
            if props.Kt < radians(90) and props.Pa > 0:
                for _ in range(props.IterAva):
                    g.avalanche(tan(props.Kt), props.IterAva, props.Pa, props.numexpr)
            if props.Kz > 0:
                g.fluvial_erosion(props.Kr, props.Kv, props.userainmap, props.Kc, props.Ks, props.Kz * 50, props.Ka, 0, 0, 0, 0, props.numexpr)

        newMesh = bpy.data.meshes.new(oldMesh.name)
        g.toBlenderMesh(newMesh)
        ob.data = newMesh

        for r in range(g.center.shape[0]):
            for c in range(g.center.shape[1]):
                i = r * g.center.shape[1] + c
                for name, fn in maps.items():
                    vg = ob.vertex_groups.get(name)
                    if vg:
                        vg.add([i], fn(g, r, c), 'REPLACE')

        cap_vg = ob.vertex_groups.get('capacity')
        if cap_vg:
            ob.vertex_groups.active = cap_vg

        bpy.ops.object.shade_smooth() if props.smooth else bpy.ops.object.shade_flat()
        stats.time(); stats.memory()
        if props.showmeshstats:
            self.report({'INFO'}, f"Mesh stats:\n{g.analyze()}")
        return {'FINISHED'}

# ------------------------------------------------------------
# Displacement Operator
# ------------------------------------------------------------

class LANDSCAPE_OT_displace(bpy.types.Operator):
    bl_idname = "landscape.displace"
    bl_label = "Mesh Displace"
    bl_description = "Displace mesh vertices using noise"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ("NORMAL", "Normal", "Displace along vertex normal"),
            ("Z", "Z", "Displace in Z direction"),
            ("Y", "Y", "Displace in Y direction"),
            ("X", "X", "Displace in X direction")
        ],
        default="NORMAL"
    )
    
    def execute(self, context):
        ob = context.active_object
        if not ob or ob.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected")
            return {'CANCELLED'}
            
        props = context.scene.landscape_props
        prop_list = _make_prop_list(props)
        
        mesh = ob.data
        
        if props.vert_group != "" and props.vert_group in ob.vertex_groups:
            vertex_group = ob.vertex_groups[props.vert_group]
            gi = vertex_group.index
            
            if self.direction == "X":
                for v in mesh.vertices:
                    for g in v.groups:
                        if g.group == gi:
                            v.co.x += vertex_group.weight(v.index) * noise_gen(v.co, prop_list)
            elif self.direction == "Y":
                for v in mesh.vertices:
                    for g in v.groups:
                        if g.group == gi:
                            v.co.y += vertex_group.weight(v.index) * noise_gen(v.co, prop_list)
            elif self.direction == "Z":
                for v in mesh.vertices:
                    for g in v.groups:
                        if g.group == gi:
                            v.co.z += vertex_group.weight(v.index) * noise_gen(v.co, prop_list)
            else:  
                for v in mesh.vertices:
                    for g in v.groups:
                        if g.group == gi:
                            v.co += v.normal * vertex_group.weight(v.index) * noise_gen(v.co, prop_list)
        else:
            if self.direction == "X":
                for v in mesh.vertices:
                    v.co.x += noise_gen(v.co, prop_list)
            elif self.direction == "Y":
                for v in mesh.vertices:
                    v.co.y += noise_gen(v.co, prop_list)
            elif self.direction == "Z":
                for v in mesh.vertices:
                    v.co.z += noise_gen(v.co, prop_list)
            else:  
                for v in mesh.vertices:
                    v.co += v.normal * noise_gen(v.co, prop_list)
                    
        mesh.update()
        return {'FINISHED'}

# ------------------------------------------------------------
# Slope Map Operator
# ------------------------------------------------------------

class LANDSCAPE_OT_slope_map(bpy.types.Operator):
    bl_idname = "landscape.slope_map"
    bl_label = "Weight from Slope"
    bl_description = "Generate vertex group from slope"
    bl_options = {'REGISTER', 'UNDO'}
    
    z_method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('SLOPE_Z', "Z Slope", "Slope for planar mesh"),
            ('SLOPE_XYZ', "Sphere Slope", "Slope for spherical mesh")
        ],
        default='SLOPE_Z'
    )
    group_name: bpy.props.StringProperty(
        name="Vertex Group Name",
        default="Slope"
    )
    select_flat: bpy.props.BoolProperty(
        name="Select Flat",
        default=True,
        description="Select vertices on flat surface"
    )
    select_range: bpy.props.FloatProperty(
        name="Select Range",
        default=0.0,
        min=0.0,
        max=1.0,
        description="Increase to select more vertices on slopes"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        ob = context.active_object
        if not ob or ob.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected")
            return {'CANCELLED'}
            
        bpy.ops.object.mode_set(mode='OBJECT')
        
        if self.select_flat:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.context.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.object.mode_set(mode='OBJECT')

        if self.group_name in ob.vertex_groups:
            vg_normal = ob.vertex_groups[self.group_name]
        else:
            vg_normal = ob.vertex_groups.new(name=self.group_name)
            
        ob.vertex_groups.active = vg_normal

        for v in ob.data.vertices:
            if self.z_method == 'SLOPE_XYZ':
                zval = (v.co.normalized() @ v.normal.normalized()) * 2 - 1
            else:
                zval = v.normal.z
                
            vg_normal.add([v.index], zval, 'REPLACE')

            if self.select_flat:
                if zval >= (1.0 - self.select_range):
                    v.select = True

        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        return {'FINISHED'}

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

class VIEW3D_PT_landscape_generator(bpy.types.Panel):
    bl_label = "Landscape"
    bl_idname = "VIEW3D_PT_landscape_generator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Landscape"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.landscape_props
        obj = context.object
        active_land = get_active_landscape(context)

        layout.operator("landscape.generate", icon='MESH_GRID', text="Generate Landscape")

        row = layout.row(align=True)
        row.prop(props, "live_update", toggle=True)
        row.operator("landscape.reset_settings", text="Reset")

        layout.separator()

        layout.prop(props, "show_main_settings", text="Main Settings", toggle=True)
        if props.show_main_settings:
            box = layout.box()
            col = box.column(align=True)

            row = col.row(align=True)
            row.prop(props, "smooth_mesh", toggle=True)
            row.prop(props, "tri_face", toggle=True)

            row = col.row(align=True)
            row.prop(props, "sphere_mesh", toggle=True)
            if props.sphere_mesh:
                row.prop(props, "remove_double", toggle=True)

            col.separator(factor=0.5)
            col.prop(props, "subdivision_x", slider=True)
            col.prop(props, "subdivision_y", slider=True)

            if props.sphere_mesh:
                col.prop(props, "mesh_size", slider=True)
            else:
                col.prop(props, "mesh_size_x", slider=True)
                col.prop(props, "mesh_size_y", slider=True)

        layout.prop(props, "show_noise_settings", text="Noise Settings", toggle=True)
        if props.show_noise_settings:
            box = layout.box()
            col = box.column(align=True)

            col.prop(props, "noise_type")
            if props.noise_type == 'blender_texture':
                col.prop_search(props, "texture_block", bpy.data, "textures")
            else:
                col.prop(props, "basis_type")
                if props.noise_type in {
                    'vl_noise_turbulence',
                    'vl_hTerrain',
                    'distorted_heteroTerrain',
                    'double_multiFractal',
                    'slick_rock'
                }:
                    col.prop(props, "vl_basis_type")

            col.separator(factor=0.5)
            col.prop(props, "random_seed", slider=True)
            col.prop(props, "noise_offset_x", slider=True)
            col.prop(props, "noise_offset_y", slider=True)
            if props.sphere_mesh:
                col.prop(props, "noise_offset_z", slider=True)
            col.prop(props, "noise_size_x", slider=True)
            col.prop(props, "noise_size_y", slider=True)
            if props.sphere_mesh:
                col.prop(props, "noise_size_z", slider=True)
            col.prop(props, "noise_size", slider=True)

        layout.prop(props, "show_height_settings", text="Height Settings", toggle=True)
        if props.show_height_settings:
            box = layout.box()
            col = box.column(align=True)

            row = col.row(align=True)
            row.prop(props, "height", slider=True)
            row.prop(props, "height_invert", toggle=True, text="", icon='ARROW_LEFTRIGHT')

            col.prop(props, "height_offset", slider=True)
            col.prop(props, "maximum", slider=True)
            col.prop(props, "minimum", slider=True)

            if not props.sphere_mesh:
                col.separator(factor=0.5)
                col.prop(props, "edge_falloff")
                if props.edge_falloff != "0":
                    col.prop(props, "edge_level", slider=True)
                    if props.edge_falloff in {"2", "3"}:
                        col.prop(props, "falloff_x", slider=True)
                    if props.edge_falloff in {"1", "3"}:
                        col.prop(props, "falloff_y", slider=True)

            col.separator(factor=0.5)
            col.prop(props, "strata_type")
            if props.strata_type != "0":
                col.prop(props, "strata", slider=True)

            if obj:
                col.separator(factor=0.5)
                col.prop_search(props, "vert_group", obj, "vertex_groups")

        layout.prop(props, "show_effect_settings", text="Effect Settings", toggle=True)
        if props.show_effect_settings:
            box = layout.box()
            col = box.column(align=True)

            col.prop(props, "fx_type")
            if props.fx_type != "0":
                if int(props.fx_type) <= 12:
                    col.prop(props, "fx_bias", slider=True)
                col.prop(props, "fx_mix_mode")
                col.prop(props, "fx_mixfactor", slider=True)

                col.separator(factor=0.5)
                col.prop(props, "fx_loc_x", slider=True)
                col.prop(props, "fx_loc_y", slider=True)
                col.prop(props, "fx_size", slider=True)
                col.prop(props, "fx_depth", slider=True)
                if props.fx_depth != 0:
                    col.prop(props, "fx_frequency", slider=True)
                    col.prop(props, "fx_amplitude", slider=True)
                col.prop(props, "fx_turb", slider=True)

                col.separator(factor=0.5)
                row = col.row(align=True)
                row.prop(props, "fx_height", slider=True)
                row.prop(props, "fx_invert", toggle=True, text="", icon='ARROW_LEFTRIGHT')
                col.prop(props, "fx_offset", slider=True)

        layout.prop(props, "show_erosion_settings", text="Erosion Settings", toggle=True)
        if props.show_erosion_settings:
            box = layout.box()
            col = box.column(align=True)

            if obj and "landscape_generator" in obj:
                col.operator("landscape.eroder", text="Run Erosion", icon="MOD_FLUIDSIM")

            col.separator(factor=0.5)
            col.prop(props, "Iterations", slider=True)
            col.prop(props, "IterRiver", slider=True)
            col.prop(props, "IterAva", slider=True)
            col.prop(props, "IterDiffuse", slider=True)
            col.prop(props, "Ef", slider=True)
            col.prop(props, "Kd", slider=True)
            col.prop(props, "Kt", slider=True)
            col.prop(props, "Kr", slider=True)
            col.prop(props, "Kv", slider=True)
            col.prop(props, "Ks", slider=True)
            col.prop(props, "Kdep", slider=True)
            col.prop(props, "Kz", slider=True)
            col.prop(props, "Kc", slider=True)
            col.prop(props, "Ka", slider=True)
            col.prop(props, "Kev", slider=True)
            col.prop(props, "Pd", slider=True)
            col.prop(props, "Pa", slider=True)
            col.prop(props, "Pw", slider=True)

            col.separator(factor=1.5)
            col.prop(props, "userainmap", toggle=True)
            col.prop(props, "numexpr", toggle=True)
            col.prop(props, "smooth", toggle=True)
            col.prop(props, "showiterstats", toggle=True)
            col.prop(props, "showmeshstats", toggle=True)

        layout.prop(props, "show_tools", text="Landscape Tools", toggle=True)
        if props.show_tools:
            box = layout.box()
            col = box.column(align=True)
            col.operator("landscape.displace", text="Mesh Displace", icon="MOD_DISPLACE")
            col.operator("landscape.slope_map", text="Slope Map", icon="TEXTURE_DATA")

        layout.separator(factor=0.5)

        if (
            obj
            and obj.type == "MESH"
            and "landscape_generator" in obj
            and obj.select_get()
        ):
            row = layout.row(align=True)
            row.operator("landscape.delete", icon="TRASH", text="Delete Landscape")
            layout.label(text=f"Editing Landscape: {obj.name}", icon="EDITMODE_HLT")
        else:
            layout.label(text="No landscape selected", icon="INFO")

# ------------------------------------------------------------
# Registration
# ------------------------------------------------------------

classes = (
    LandscapeProperties,
    LANDSCAPE_OT_generate,
    LANDSCAPE_OT_delete,
    LANDSCAPE_OT_refresh,
    LANDSCAPE_OT_regenerate,
    LANDSCAPE_OT_eroder,
    LANDSCAPE_OT_displace,
    LANDSCAPE_OT_slope_map,
    LANDSCAPE_OT_reset_settings,  
    VIEW3D_PT_landscape_generator, 
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.landscape_props = bpy.props.PointerProperty(type=LandscapeProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.landscape_props

if __name__ == "__main__":
    register()