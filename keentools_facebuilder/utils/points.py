# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

import bpy
import gpu
import bgl
from gpu_extras.batch import batch_for_shader
from .. config import config


class FBShaderPoints:
    """ Base class for Point Drawing Shaders """
    point_size = config.default_pin_size

    # Store all draw handlers registered by class objects
    handler_list = []

    @classmethod
    def add_handler_list(cls, handler):
        cls.handler_list.append(handler)

    @classmethod
    def remove_handler_list(cls, handler):
        if handler in cls.handler_list:
            cls.handler_list.remove(handler)

    @classmethod
    def is_handler_list_empty(cls):
        return len(cls.handler_list) == 0

    def __init__(self):
        self.draw_handler = None  # for 3d shader
        self.shader = None
        self.batch = None

        self.vertices = []
        self.vertices_colors = []

    @classmethod
    def set_point_size(cls, ps):
        cls.point_size = ps

    def _create_batch(self, vertices, vertices_colors,
                      shadername='2D_FLAT_COLOR'):
        if shadername == 'CUSTOM_3D':
            # 3D_FLAT_COLOR
            vertex_shader = '''
                uniform mat4 ModelViewProjectionMatrix;
                #ifdef USE_WORLD_CLIP_PLANES
                uniform mat4 ModelMatrix;
                #endif

                in vec3 pos;
                #if defined(USE_COLOR_U32)
                in uint color;
                #else
                in vec4 color;
                #endif

                flat out vec4 finalColor;

                void main()
                {
                    vec4 pos_4d = vec4(pos, 1.0);
                    gl_Position = ModelViewProjectionMatrix * pos_4d;

                #if defined(USE_COLOR_U32)
                    finalColor = vec4(
                        ((color      ) & uint(0xFF)) * (1.0f / 255.0f),
                        ((color >>  8) & uint(0xFF)) * (1.0f / 255.0f),
                        ((color >> 16) & uint(0xFF)) * (1.0f / 255.0f),
                        ((color >> 24)             ) * (1.0f / 255.0f));
                #else
                    finalColor = color;
                #endif

                #ifdef USE_WORLD_CLIP_PLANES
                    world_clip_planes_calc_clip_distance((ModelMatrix * pos_4d).xyz);
                #endif
                }
            '''
            fragment_shader = '''
                flat in vec4 finalColor;
                out vec4 fragColor;
                void main() {
                        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                        float r = dot(cxy, cxy);
                        float delta = fwidth(r);
                        float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
                        fragColor = finalColor * alpha;
                }
            '''

            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors},
                indices=None
            )
        elif shadername == 'CUSTOM_2D':
            vertex_shader = '''
                uniform mat4 ModelViewProjectionMatrix;

                in vec2 pos;
                in vec4 color;

                flat out vec4 finalColor;

                void main()
                {
                    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
                    finalColor = color;
                }
            '''
            fragment_shader = '''
                flat in vec4 finalColor;
                out vec4 fragColor;
                void main() {
                        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
                        float r = dot(cxy, cxy);
                        float delta = fwidth(r);
                        float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
                        fragColor = finalColor * alpha;
                }
            '''
            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors},
                indices=None
            )
        else:
            self.shader = gpu.shader.from_builtin(shadername)
            self.batch = batch_for_shader(
                self.shader, 'POINTS',
                {"pos": vertices, "color": vertices_colors}
            )

    def create_batch(self):
        self._create_batch(self.vertices, self.vertices_colors)

    def register_handler(self, args):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_VIEW")
        # Add to handler list
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self):
        if self.draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handler, "WINDOW")
            # Remove from handler list
            self.remove_handler_list(self.draw_handler)

        self.draw_handler = None

    def add_color_vertices(self, color, verts):
        for i, v in enumerate(verts):
            self.vertices.append(verts[i])
            self.vertices_colors.append(color)

    def add_vertices_colors(self, verts, colors):
        for i, v in enumerate(verts):
            self.vertices.append(verts[i])
            self.vertices_colors.append(colors[i])

    def set_color_vertices(self, color, verts):
        self.clear_vertices()
        self.add_color_vertices(color, verts)

    def set_vertices_colors(self, verts, colors):
        self.clear_vertices()
        self.add_vertices_colors(verts, colors)

    def clear_vertices(self):
        self.vertices = []
        self.vertices_colors = []

    def draw_callback(self, op, context):
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        if self.shader is not None:
            bgl.glPointSize(self.point_size)
            bgl.glEnable(bgl.GL_BLEND)
            self.shader.bind()
            self.batch.draw(self.shader)
            bgl.glDisable(bgl.GL_BLEND)


class FBPoints2D(FBShaderPoints):
    """ 2D Shader for 2D-points drawing """
    def create_batch(self):
        self._create_batch(
            # 2D_FLAT_COLOR
            self.vertices, self.vertices_colors, 'CUSTOM_2D')

    def register_handler(self, args):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, "WINDOW", "POST_PIXEL")
        # Add to handler list
        self.add_handler_list(self.draw_handler)


class FBPoints3D(FBShaderPoints):
    """ 3D Shader wrapper for 3d-points draw """
    def create_batch(self):
        # 3D_FLAT_COLOR
        self._create_batch(self.vertices, self.vertices_colors, 'CUSTOM_3D')

    def __init__(self):
        super().__init__()
        self.set_point_size(
            config.default_pin_size * config.surf_pin_size_scale)
