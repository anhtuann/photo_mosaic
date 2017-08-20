import os
from PIL import Image
from PIL import ImageStat
from PIL import ImageDraw
import json
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

# Analysis of the dataset

def getfilespath(root_path):
    files = []
    for (dirpath, dirnames, filenames) in os.walk(root_path):
        files.extend([os.path.join(dirpath, filename) for filename in filenames])
    return files

def extract_exif(image_path):
    with Image.open(image_path) as image:
        infos = image._getexif()
        # tags identified by ExifTags
        datepic = infos[36867]
        #modelcam = infos[272]
        orientation = infos[274]
        img_ratio = infos[40962]/infos[40963]
    return (datepic, orientation, img_ratio)

class CustomStat(ImageStat.Stat):
    def _getmean2(self):
        v = []
        for i in self.bands:
            v.append((self.sum2[i] / self.count[i])**0.5)
        return v

def avg_rgb(image_arg):
    if type(image_arg) is str:
        with Image.open(image_arg) as image:
            try:
                image.thumbnail((512, 512))
            except OSError:
                print(image_arg, 'corrupted')
                return 'corrupted'
            avg_r, avg_g, avg_b = map(int, CustomStat(image)._getmean2())
    else:
        avg_r, avg_g, avg_b = map(int, CustomStat(image_arg)._getmean2())
    return (avg_r, avg_g, avg_b)

def gen_dataset(root_path):
    print('Generating dataset analysis')
    raw_dataset = getfilespath(root_path)
    pics_dict = {}
    for pic in raw_dataset:
        file_extension = pic.split('.')[-1].lower()
        if file_extension == 'jpg' or file_extension == 'jpeg':
            datepic, orientation, img_ratio = extract_exif(pic)
            #avg_r, avg_g, avg_b = avg_rgb(pic)
            try:
                avg_color = sRGBColor(*avg_rgb(pic))
                avg_lab = convert_color(avg_color, LabColor)
                pics_dict[pic] = (datepic, orientation, img_ratio, avg_color.get_value_tuple(), avg_lab.get_value_tuple())
            except TypeError:
                pass
    return pics_dict

def save_datas(datas, file_path):
    with open(file_path, 'w') as datas_file:
        datas_file.write(json.dumps(datas))
    print(file_path, 'saved')

def open_datas(dataset_path):
    with open(dataset_path, 'r') as datas_file:
        datas = json.loads(datas_file.read())
    print(dataset_path, 'imported')
    return datas

if not os.path.exists('analyzed_dataset.txt'):
    datas = gen_dataset('dataset')
    save_datas(datas, 'analyzed_dataset.txt')
    pics_dict = datas
else:
    pics_dict = open_datas('analyzed_dataset.txt')

def gen_palette(pics_dict):
    palette_dict = {}
    for pic, datas in pics_dict.items():
        datepic, orientation, img_ratio, avg_color, avg_lab = datas
        try:
            palette_dict[tuple(avg_lab)].append(pic)
        except KeyError:
            palette_dict[tuple(avg_lab)] = [pic]
    print('dataset palette generated')
    return palette_dict

#if not os.path.exists('dataset_palette.txt'):
#    datas = gen_palette(pics_dict)
#    save_datas(datas, 'dataset_palette.txt')
#    palette_dict = datas
#else:
#    palette_dict = open_datas('dataset_palette.txt')

palette_dict = gen_palette(pics_dict)

# Analysis of the model image

def resize_model(model_path, tile_ratio, tile_width, thumbnail_maxsize):
    with Image.open(model_path) as model:
        model.thumbnail(thumbnail_maxsize)
        tile_height = int(tile_width/tile_ratio)
        resized_width = (model.width//tile_width)*tile_width
        resized_height = (model.height//tile_height)*tile_height
        resized_model = model.resize((resized_width, resized_height))
    return resized_model

def tiling(model_path, tile_ratio, tile_width, thumbnail_maxsize):
    tile_height = int(tile_width/tile_ratio)
    tiles_boxes = []
    resized_model = resize_model(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    for y in range(0, resized_model.height, tile_height):
        for x in range(0, resized_model.width, tile_width):
            tiles_boxes.append((x, y, x+tile_width, y+tile_height))
    return tiles_boxes

def model_analysis(model_path, tile_ratio, tile_width, thumbnail_maxsize):
    tiles = tiling(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    resized_model = resize_model(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    tiles_dict = {}
    for tile in tiles:
        model_tile = resized_model.crop(tile)
        tiles_dict[tile] = avg_rgb(model_tile)
    return tiles_dict

model_path = 'dataset/Tram/DSC_0809.JPG'

def basic_mosaic(model_path, tile_ratio=4/3, tile_width=12, thumbnail_maxsize=(2048, 2048)):
    tiles_dict = model_analysis(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    resized_model = resize_model(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    mosaic = Image.new(resized_model.mode, resized_model.size)
    draw_mosaic = ImageDraw.Draw(mosaic)
    for tile in tiles_dict.keys():
        draw_mosaic.rectangle(tile, fill=tiles_dict[tile])
    mosaic.save('basic_mosaic.png')
    return 'basic mosaic created'

def photo_mosaic(model_path, palette_dict, tile_ratio=4/3, tile_width=12, thumbnail_maxsize=(1024, 1024)):
    tiles_dict = model_analysis(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    resized_model = resize_model(model_path, tile_ratio, tile_width, thumbnail_maxsize)
    mosaic = Image.new(resized_model.mode, resized_model.size)
    for tile in tiles_dict.keys():
        tile_color = convert_color(sRGBColor(*tiles_dict[tile]), LabColor)
        deltaE_threshold = 4
        min_deltaE = 100
        close_pic = ''
        for color, path in palette_dict.items():
            new_deltaE = delta_e_cie2000(tile_color, LabColor(*color))
            if new_deltaE <= deltaE_threshold:
                close_pic = path[0]
                break
            elif new_deltaE < min_deltaE:
                min_deltaE = new_deltaE
                close_pic = path[0]
        with Image.open(close_pic) as pic:
            tile_pic = pic.resize((tile_width, int(tile_width/tile_ratio)))
            mosaic.paste(tile_pic, tile)
    mosaic.save('photo_mosaic.png')
    return('photo mosaic created')

print(basic_mosaic(model_path))
print(photo_mosaic(model_path, palette_dict))

