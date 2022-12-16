print('start')

import bpy

import sys
site_packages_path = "C:\\Program Files\\Blender Foundation\\Blender 3.3\\3.3\\python\\lib\\site-packages" # the path to your site-packages folder in Blender
packages_path = "c:\\users\\username\\appdata\\roaming\\python\\python310\\site-packages" # the path you see in the blender console

sys.path.insert(0, packages_path )

from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry, Region
from msrest.authentication import ApiKeyCredentials
import os, time, uuid
import random
import numpy as np


#azure set up

project_id = "project_id_guid_here"
# Replace with valid values
ENDPOINT = "azure_CV_endpoint_here"
training_key = "azure_CV_training_key_here"
prediction_key = "azure_CV_prediction_key_here" #not requried yet
prediction_resource_id = "azure_CV_prediction_resource_GUID_here"

credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)
prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
predictor = CustomVisionPredictionClient(ENDPOINT, prediction_credentials)

#get the project id
project = trainer.get_project(project_id)

#get the tags
tag_name = "tennis ball" #change this to the tag you want to use for your selected object

tags = trainer.get_tags(project.id,tag_name)
for tag in tags:
    if tag_name in (tag.name):
        ball_tag = tag

""" credit to https://blender.stackexchange.com/questions/7198/save-the-2d-bounding-box-of-an-object-in-rendered-image-to-a-text-file 
CodeManX and juniorxsound"""
def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))

def camera_view_bounds_2d(scene, cam_ob, me_ob):
    """
    Returns camera space bounding box of mesh object.

    Negative 'z' value means the point is behind the camera.

    Takes shift-x/y, lens angle and sensor size into account
    as well as perspective/ortho projections.

    :arg scene: Scene to use for frame size.
    :type scene: :class:`bpy.types.Scene`
    :arg obj: Camera object.
    :type obj: :class:`bpy.types.Object`
    :arg me: Untransformed Mesh.
    :type me: :class:`bpy.types.Mesh´
    :return: a Box object (call its to_tuple() method to get x, y, width and height)
    :rtype: :class:`Box`
    """

    mat = cam_ob.matrix_world.normalized().inverted()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_eval = me_ob.evaluated_get(depsgraph)
    me = mesh_eval.to_mesh()
    me.transform(me_ob.matrix_world)
    me.transform(mat)

    camera = cam_ob.data
    frame = [-v for v in camera.view_frame(scene=scene)[:3]]
    camera_persp = camera.type != 'ORTHO'

    lx = []
    ly = []

    for v in me.vertices:
        co_local = v.co
        z = -co_local.z

        if camera_persp:
            if z == 0.0:
                lx.append(0.5)
                ly.append(0.5)
            # Does it make any sense to drop these?
            # if z <= 0.0:
            #    continue
            else:
                frame = [(v / (v.z / z)) for v in frame]

        min_x, max_x = frame[1].x, frame[2].x
        min_y, max_y = frame[0].y, frame[1].y

        x = (co_local.x - min_x) / (max_x - min_x)
        y = (co_local.y - min_y) / (max_y - min_y)

        lx.append(x)
        ly.append(y)

    min_x = clamp(min(lx), 0.0, 1.0)
    max_x = clamp(max(lx), 0.0, 1.0)
    min_y = clamp(min(ly), 0.0, 1.0)
    max_y = clamp(max(ly), 0.0, 1.0)

    mesh_eval.to_mesh_clear()

    r = scene.render
    fac = r.resolution_percentage * 0.01
    dim_x = r.resolution_x * fac
    dim_y = r.resolution_y * fac

    # Sanity check
    if round((max_x - min_x) * dim_x) == 0 or round((max_y - min_y) * dim_y) == 0:
        return (0, 0, 0, 0)

    '''return (
        round(min_x * dim_x),            # X
        round(dim_y - max_y * dim_y),    # Y
        round((max_x - min_x) * dim_x),  # Width
        round((max_y - min_y) * dim_y)   # Height
    )'''
    
    #normalised coordinates
    
    x = (min_x * dim_x)             # X
    y = (dim_y - max_y * dim_y)     # Y
    w = ((max_x - min_x) * dim_x)   # Width
    h = ((max_y - min_y) * dim_y)   # Height
        
    n_x = x/dim_x    #normalised x
    n_y = y/dim_y    #normailised y
    n_w = w/dim_x    #normalised w
    n_h = h/dim_y    #normalised h
    
    return(
        n_x,
        n_y,
        n_w,
        n_h)    

# Print the result
print(camera_view_bounds_2d(bpy.context.scene, bpy.context.scene.camera, bpy.context.object))

print('start renders')

step = 0
light_ob = bpy.data.objects.get("Area")
light = light_ob.data

for step in range(4):
    print('run number ', str(step))
    
    path = "your_output_path_here" + str(step) + ".png"
    open(path,'a') #create the file to fill later
    tagged_images_with_regions = []
    
    #randomise x,y locations
    random_locations = random.sample(range(0, 1000), 2)
    
    for count, rand in enumerate(random_locations):
        bpy.context.object.location[count] = (rand/1000)-0.5 #between -0.5 and 0.5
        
    #measure
    x,y,w,h = camera_view_bounds_2d(bpy.context.scene, bpy.context.scene.camera, bpy.context.object)
    regions = [ Region(tag_id=ball_tag.id, left=x,top=y,width=w,height=h) ]
        
    #randomise lighting
    light.energy = random.randrange(10, 120)
    light.color = np.random.random_sample(size = 3)
    
    bpy.context.object.location[1]-=0.1
    
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still = True)
    bpy.ops.render.render()
    
    with open(path, mode="rb") as image_contents:
        tagged_images_with_regions.append(ImageFileCreateEntry(name='test', contents=image_contents.read(), regions=regions))

    upload_result = trainer.create_images_from_files(project.id, ImageFileCreateBatch(images=tagged_images_with_regions))
    print(upload_result)
    
print('renders completed')
