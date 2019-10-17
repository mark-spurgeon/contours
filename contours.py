bl_info = {
    "name": "Generate Contour",
    "description": "Contour",
    "author": "Mark Spurgeon",
    "version": (0, 1, 0),
    "blender": (2, 8, 0),
    "location": "Info Header > Engine dropdown menu",
    "wiki_url": "https://github.com/TheBounty/Blender-Exporter/wiki",
    "tracker_url": "https://github.com/TheBounty/Blender-Exporter/issues",
    "category": "Object"
}

import bpy
import bgl
import bmesh
import math

def create_contour(context, original_object, position = 0.0, collection = 'ContourCollection', name = 'Contour', simplify_distance = 0):
    # VIEW : set mode to OBJECT 
    if context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    # SCENE : create copy mesh
    contour_object = bpy.data.objects.new(
        name, 
        original_object.data.copy()
        )
    contour_object.location = original_object.location
    contour_object.scale = original_object.scale
    
    ##  SCENE : link to collection 
    bpy.data.collections[collection].objects.link(contour_object)

    # MESH : bisect
    contour_mesh = contour_object.data
    
    bm = bmesh.new()
    bm.from_mesh(contour_mesh)
    geom = bm.verts[:]+bm.edges[:]+bm.faces[:]
    bmesh.ops.bisect_plane(
        bm,
        geom = geom,
        plane_co = (0.0, 0.0, position),
        plane_no = (0, 0, 1),
        clear_inner = True,
        clear_outer = True
    ) # could be assigned to a variable, check if work has been done
    bmesh.ops.automerge(
        bm,
        verts = bm.verts,
        dist = simplify_distance
    )
    bm.to_mesh(contour_mesh)
    
    return contour_object.name
    
class ContourOperator(bpy.types.Operator):
    '''Generate a contour of the object'''
    
    bl_idname = "object.generate_contour"
    bl_label = "Generate Contour"
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator 
    
    #####
    ## Add-on's properties
    #####
    contour_name: bpy.props.StringProperty(name="Contour name (group)", default = 'Contour')
    contour_name_pattern: bpy.props.StringProperty(name="Contour name pattern", default = '{object}_Contour_{position}m')
    sea_level: bpy.props.FloatProperty(name="Sea Level", default = 0.0)
    interval_units: bpy.props.FloatProperty(name="Distance", default = 1)
    simplify_distance: bpy.props.FloatProperty(name="Simplify Vertices Distance", default = 4, min = 0)
    join: bpy.props.BoolProperty(name="Join contours")
    
    #####
    ## 
    #####
    def execute(self, context):
        # GLOBAL : get object for future reference
        og_object = context.active_object
        og_object_height = og_object.dimensions.z
        layer_number = math.floor(og_object_height / math.fabs(self.interval_units)) + 1 # really just to set a maximum value
        
        # NEW COLLECTION
        collection = bpy.data.collections.new(self.contour_name) 
        bpy.context.scene.collection.children.link(collection) 
        
        
        contour_objects_list = []
        
        for i in range(0, layer_number):
            pos = i * self.interval_units + self.sea_level
            try:
                name = self.contour_name_pattern.format(
                    object = og_object.name, 
                    position = pos,
                    index = i
                    )
            except KeyError as e:
                self.report({'ERROR'}, e)
                self.report({'INFO'}, "Choosing default name")
                name = "GeneratedContour_" + position
                
            context.view_layer.objects.active = og_object
            new_contour_object = create_contour(
                        context, 
                        og_object, 
                        position = pos,
                        collection = collection.name, 
                        name = name,
                        simplify_distance = self.simplify_distance
                        )
            contour_objects_list.append(new_contour_object)
                    
        # SELECT the new objects 
        og_object.select_set(False) # deselect the og object
        for contour_name in contour_objects_list: 
            contour_object = bpy.data.objects[contour_name]
            contour_object.select_set(True)
            
            #####
            ## Object operations
            #####

            # set object to active
            context.view_layer.objects.active = contour_object
            # convert to curve
            bpy.ops.object.convert(target = "CURVE", keep_original = False)
            #  smooth
            # bpy.ops.curve.select_all(action = "SELECT")
            if context.active_object.mode != 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        
                
            if contour_object.type == "CURVE":
                for spline in contour_object.data.splines:
                    spline.type = "NURBS"
                context.view_layer.objects.active = contour_object
                #bpy.ops.curve.spline_type_set(type = "NURBS")
                      
        bpy.context.view_layer.objects.active = bpy.data.objects[contour_objects_list[0]]
        
        if context.active_object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
                
        if self.join == True:
            if context.active_object.mode == 'OBJECT':
                bpy.ops.object.join()
                joined_object = bpy.data.objects[contour_objects_list[0]]
                joined_object.name = self.contour_name
                bpy.data.collections[collection.name].objects.unlink(joined_object)
                context.scene.collection.objects.link(joined_object)
                bpy.data.collections.remove(collection)
            
            #joined_object.select_set(state = True)
            #context.view_layer.objects.active = joined_object
            #bpy.ops.object.convert(target = "CURVE", keep_original = False)

        return {'FINISHED'}
    
    #####
    ## Display panel on invoke
    #####
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    ## Panel layout
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Naming")

        col.prop(self, "contour_name")
        col.prop(self, "contour_name_pattern")
        
        row = col.row()
        row.prop(self, "sea_level")
        row.prop(self, "interval_units")
        
        row2 = col.row()
        row2.prop(self, "simplify_distance")
        
        col.prop(self, "join")

def register():
    # Register the RenderEngine
    bpy.utils.register_class(ContourOperator)

def unregister():
    bpy.utils.unregister_class(ContourOperator)

if __name__ == "__main__":
    register()