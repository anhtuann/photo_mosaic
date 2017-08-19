import os
from PIL import Image
from PIL import ImageStat
import json

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
    raw_dataset = getfilespath(root_path)
    pics_dict = {}
    for pic in raw_dataset:
        file_extension = pic.split('.')[-1].lower()
        if file_extension == 'jpg' or file_extension == 'jpeg':
            datepic, orientation, img_ratio = extract_exif(pic)
            avg_color = avg_rgb(pic)
            pics_dict[pic] = (datepic, orientation, img_ratio, avg_color)
    return pics_dict

def save_dataset(dataset):
    with open('analyzed_dataset.txt', 'w') as analyzed_dataset:
        analyzed_dataset.write(json.dumps(dataset))
    return 'Dataset analyzed and saved'

def open_dataset(dataset_path):
    with open(dataset_path, 'r') as analyzed_dataset:
        pics_dict = json.loads(analyzed_dataset.read())
    return pics_dict

if not os.path.exists('analyzed_dataset.txt'):
    print('Generating dataset analysis')
    data = gen_dataset('dataset')
    save_dataset(data)
    pics_dict = data
else:
    pics_dict = open_dataset('analyzed_dataset.txt')
    print('Analyzed dataset imported')


# Analysis of the model image

def tiling(model_path):
    tile_ratio = 4/3
    tile_width = 12
    tile_height = int(tile_width/tile_ratio)
    tiles_boxes = []
    with Image.open(model_path) as model:
        resized_width = (model.width//tile_width)*tile_width
        resized_height = (model.height//tile_height)*tile_height
        for x in range(0, resized_width, resized_width//tile_width - 1):
            for y in range(0, resized_height, resized_height//tile_height - 1):
                tiles_boxes.append((x, y, x+tile_width, y+tile_height))
    return tiles_boxes

def model_analysis(model_path):
    tiles = tiling(model_path)
    tiles_dict = {}
    with Image.open(model_path) as model:
        for tile in tiles:
            model_tile = model.crop(tile)
            tiles_dict[tile] = avg_rgb(model_tile)
    return tiles_dict

print(model_analysis(list(pics_dict.keys())[3]))

