import os
import shutil
from PIL import Image
from PIL import ImageStat
from PIL import ImageDraw
from slugify import slugify
import json
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import copy

img_extensions = ['png', 'jpg', 'jpeg']

def getfilespath(root_path):
    '''
    Get list of files

    Args:
        root_path (str) : path of the root folder

    Returns:
        files (list) : recursively generated list of all files in root folder and its subdirectories
    '''
    files = []
    for (dirpath, dirnames, filenames) in os.walk(root_path):
        files.extend([os.path.join(dirpath, filename) for filename in filenames])
    return files

def flatten_dataset(files):
    '''
    Copy all the images in the dataset into a single directory

    Args:
        files (list) : recursively generated list of all files in root folder and its subdirectories
    '''
    for data in files:
        file_extension = data.split('.')[-1].lower()
        if file_extension in img_extensions:
            filedate = extract_exif(data)[0]
            folder = data.split('/')[1]
            filename = folder + '-' + filedate
            slug = slugify(filename) + '.' + file_extension
            shutil.copyfile(data, new_dataset + '/' + slug)
    print('dataset flattened')

def extract_exif(image_path):
    '''
    Get exif infos

    Args:
        image_path (str) : path of the image we want the exif infos extracted

    Returns:
        a tuple which contains :
            datepic (str) : date in the format YYYY:MM:DD HH:MM:SS
            orientation (int) : from 1 to 8, refer to Exif spec for explanation
            img_ratio (float) : aspect ratio of the image

    '''
    with Image.open(image_path) as image:
        infos = image._getexif()
        # tags identified by ExifTags
        datepic = infos[36867]
        #modelcam = infos[272]
        orientation = infos[274]
        img_ratio = infos[40962]/infos[40963]
    return (datepic, orientation, img_ratio)

class CustomStat(ImageStat.Stat):
    # mathematically correct average of two colors
    def _getmean2(self):
        v = []
        for i in self.bands:
            v.append((self.sum2[i] / self.count[i])**0.5)
        return v

def avg_rgb(image_arg):
    '''
    Calculate the average color (rgb) of an image

    Args:
        image_arg (str) : path of the image
            or
        image_arg(PIL.Image.Image object) : Image object to interact with

    Returns:
        a tuple which contains :
            avg_r (int) between 0 and 255
            avg_g (int) between 0 and 255
            avg_b (int) between 0 and 255
        all averages in the three R,G and B channels
    '''
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
    '''
    Generate the dataset

    Args:
        root_path (str) : path of the root folder

    Returns:
        pics_dict (dict) with
            keys : pic_path (str)
            values : a tuple containing
                        datepic (str)
                        orientation (int)
                        img_ratio (float)
                        avg_color (tuple) : (r, g, b) all floats 0.0 - 255.0
                        avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats

    '''
    print('Generating dataset analysis')
    raw_dataset = getfilespath(root_path)
    pics_dict = {}
    for pic in raw_dataset:
        file_extension = pic.split('.')[-1].lower()
        if file_extension == 'jpg' or file_extension == 'jpeg':
            datepic, orientation, img_ratio = extract_exif(pic)
            try:
                avg_color = sRGBColor(*avg_rgb(pic))
                avg_lab = convert_color(avg_color, LabColor)
                pics_dict[pic] = (datepic, orientation, img_ratio, avg_color.get_value_tuple(), avg_lab.get_value_tuple())
            except TypeError:
                pass
    return pics_dict

def save_dict(datas_dict, file_path):
    with open(file_path, 'w') as datas_file:
        formatted_datas = {str(k): v for k, v in datas_dict.items()}
        datas_file.write(json.dumps(formatted_datas))
    print(file_path, 'saved')

def open_dict(dataset_path):
    with open(dataset_path, 'r') as datas_file:
        datas = json.loads(datas_file.read())
        if list(datas.keys())[0][0] == '(' and list(datas.keys())[0][-1] == ')':
            formatted_datas = {eval(k): v for k, v in datas.items()}
        else:
            formatted_datas = datas
    print(dataset_path, 'imported')
    return formatted_datas

def NN_delta(dataset):
    '''
    Sort dataset using Nearest neighbour algorithm on DeltaE distance

    Args:
        dataset (dict) with
            keys : pic_path (str)
            values : a tuple containing
                        datepic (str)
                        orientation (int)
                        img_ratio (float)
                        avg_color (tuple) : (r, g, b) all floats 0.0 - 1.0
                        avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats

    Returns:
        sorted_datas (list) : list of tuples containing
                                   pic_path (str) : path of the pic in the dataset
                                   pic_datas (tuple) containing
                                        datepic (str)
                                        orientation (int)
                                        img_ratio (float)
                                        avg_color (tuple) : (r, g, b) all floats 0.0 - 255.0
                                        avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats
    '''
    unsorted_datas = copy.copy(dataset)
    black_rgb_color = sRGBColor(0, 0, 0)
    black_lab_color = convert_color(black_rgb_color, LabColor)
    darkest_pic, darkest_pic_datas = list(unsorted_datas.items())[0]
    darkest_pic_color = LabColor(*darkest_pic_datas[-1])
    for pic, pic_datas in unsorted_datas.items():
        pic_lab_color = LabColor(*pic_datas[-1])
        if delta_e_cie2000(black_lab_color, pic_lab_color) < delta_e_cie2000(black_lab_color, darkest_pic_color):
            darkest_pic = pic
            darkest_pic_color = pic_lab_color
    sorted_datas = []
    first_key = darkest_pic
    sorted_datas.append((first_key, unsorted_datas[first_key]))
    del(unsorted_datas[first_key])
    while len(unsorted_datas.keys()) > 0:
        last_pic, last_pic_datas = sorted_datas[-1]
        min_deltaE = 100
        closest_pic = ''
        for pic, data in unsorted_datas.items():
            new_deltaE = delta_e_cie2000(LabColor(*last_pic_datas[-1]), LabColor(*data[-1]))
            if new_deltaE < min_deltaE:
                closest_pic = pic
                min_deltaE = new_deltaE
        try:
            sorted_datas.append((closest_pic, unsorted_datas[closest_pic]))
        except KeyError:
            for pic, pic_data in unsorted_datas.items():
                sorted_datas.append((pic, pic_data))
            return sorted_datas
        del(unsorted_datas[closest_pic])
    return sorted_datas

def gen_sorted_palette(sorted_datas):
    '''
    Args:
        sorted_datas (list) : list of tuples containing
                               pic_path (str) : path of the pic in the dataset
                               pic_datas (tuple) containing
                                    datepic (str)
                                    orientation (int)
                                    img_ratio (float)
                                    avg_color (tuple) : (r, g, b) all floats 0.0 - 255.0
                                    avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats
    Returns:
    '''
    color_width = 2
    palette_width = len(sorted_datas)*color_width
    palette_height = 200
    palette = Image.new('RGB', (palette_width, palette_height))
    draw_palette = ImageDraw.Draw(palette)
    left_top_corner = (0, 0)
    right_bottom_corner = (color_width, palette_height)
    for pic, pic_datas in sorted_datas:
        pic_rgb_color = tuple(map(int, pic_datas[-2]))
        draw_palette.rectangle(left_top_corner+right_bottom_corner, fill=pic_rgb_color)
        left_top_corner = (left_top_corner[0]+color_width, 0)
        right_bottom_corner = (right_bottom_corner[0]+color_width, palette_height)
    palette.save('sorted_palette.png')

def gen_palette(pics_dict):
    '''
    Generate palette of colors according to dataset

    Args:
        pics_dict (dict) with
            keys : pic_path (str)
            values : a tuple containing
                        datepic (str)
                        orientation (int)
                        img_ratio (float)
                        avg_color (tuple) : (r, g, b) all floats 0.0 - 1.0
                        avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats

    Returns:
        palette_dict (dict) :
            keys : avg_lab (tuple) containing
                    (lab_l, lab_a, lab_b) all floats
            values : a list containing
                        pic_path (str) : path of the pic
    '''
    palette_dict = {}
    for pic, datas in pics_dict.items():
        datepic, orientation, img_ratio, avg_color, avg_lab = datas
        try:
            palette_dict[tuple(avg_lab)].append(pic)
        except KeyError:
            palette_dict[tuple(avg_lab)] = [pic]
    print('dataset palette generated')
    return palette_dict

def resize_model(model_path, tile_width, tile_height, pic_maxsize):
    '''
    Resize image to a good size for tiling process

    Args:
        model_path (str) : path of the image to resize
        tile_width (int) : width of the tile
        tile_height (int) : height of the tile
        pic_maxsize (tuple) containing
                maxwidth (int) : maximal width of the resized pic
                maxheight (int) : maximal height of the resized pic

    Returns:
        resize_model (PIL.Image.Image object) : the resized image
    '''
    with Image.open(model_path) as model:
        model.thumbnail(pic_maxsize)
        resized_width = (model.width//tile_width)*tile_width
        resized_height = (model.height//tile_height)*tile_height
        resized_model = model.resize((resized_width, resized_height))
    return resized_model

def tiling(model_path, tile_width, tile_height, pic_maxsize):
    '''
    Tiling the model image for matching process against dataset

    Args:
        model_path (str) : path of the image to resize
        tile_width (int) : width of the tile
        tile_height (int) : height of the tile
        pic_maxsize (tuple) containing
                maxwidth (int) : maximal width of the resized pic
                maxheight (int) : maximal height of the resized pic

    Returns:
        tiles_boxes (list) containing
            tile (tuple), a rectangle defined by
                x_left_top_corner (int) : x coordinate of the tile's left top corner
                y_left_top_corner (int) : y coordinate of the tile's left top corner
                x_right_bottom_corner (int) : x coordinate of the tile's right bottom corner
                y_right_bottom_corner (int) : y coordinated of the tile's right bottom corner
    '''
    tiles_boxes = []
    resized_model = resize_model(model_path, tile_width, tile_height, pic_maxsize)
    for y in range(0, resized_model.height, tile_height):
        for x in range(0, resized_model.width, tile_width):
            tiles_boxes.append((x, y, x+tile_width, y+tile_height))
    return tiles_boxes

def model_analysis(model_path, tile_width, tile_height, pic_maxsize):
    '''
    Compute the average color of each tile in the model image

    Args:
        model_path (str) : path of the image to resize
        tile_width (int) : width of the tile
        tile_height (int) : height of the tile
        pic_maxsize (tuple) containing
                maxwidth (int) : maximal width of the resized pic
                maxheight (int) : maximal height of the resized pic

    Returns:
        tiles_dict (dict) containing
                keys : tile (tuple), a rectangle defined by
                            x_left_top_corner (int) : x coordinate of the tile's left top corner
                            y_left_top_corner (int) : y coordinate of the tile's left top corner
                            x_right_bottom_corner (int) : x coordinate of the tile's right bottom corner
                            y_right_bottom_corner (int) : y coordinated of the tile's right bottom corner
                values : a tuple which contains
                            avg_r (int)
                            avg_g (int)
                            avg_b (int)
                            all averages in the three R,G and B channels

    '''
    tiles = tiling(model_path, tile_width, tile_height, pic_maxsize)
    resized_model = resize_model(model_path, tile_width, tile_height, pic_maxsize)
    tiles_dict = {}
    for tile in tiles:
        model_tile = resized_model.crop(tile)
        tiles_dict[tile] = avg_rgb(model_tile)
    return tiles_dict

def basic_mosaic(model_path, tile_width, tile_height, pic_maxsize):
    '''
    Generate basic mosaic with computed colors

    Args:
        model_path (str) : path of the image to resize
        tile_width (int) : width of the tile
        tile_height (int) : height of the tile
        pic_maxsize (tuple) containing
                maxwidth (int) : maximal width of the resized pic
                maxheight (int) : maximal height of the resized pic

    Returns:
        message -> basic mosaic created
    '''
    tiles_dict = model_analysis(model_path, tile_width, tile_height, pic_maxsize)
    resized_model = resize_model(model_path, tile_width, tile_height, pic_maxsize)
    mosaic = Image.new(resized_model.mode, resized_model.size)
    draw_mosaic = ImageDraw.Draw(mosaic)
    for tile in tiles_dict.keys():
        draw_mosaic.rectangle(tile, fill=tiles_dict[tile])
    mosaic.save('basic_mosaic.png')
    return 'basic mosaic created'

def closest_pic(tile_color, sorted_palette):
    '''
    Get the path of the pic with the closest color to the color in argument

    Args:
        tile_color (colormath.color_objects.LabColor object) : color to compare the sorted_palette to
        sorted_palette (list) : list of tuples containing
                                   pic_path (str) : path of the pic in the dataset
                                   pic_datas (tuple) containing
                                        datepic (str)
                                        orientation (int)
                                        img_ratio (float)
                                        avg_color (tuple) : (r, g, b) all floats 0.0 - 1.0
                                        avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats

    Returns:
        pic_path (str) : path of the pic with the closest color
    '''
    min_idx = 0
    max_idx = len(sorted_palette) - 1
    deltaE_threshold = 1
    while max_idx - min_idx > 1:
        min_path, min_datas = sorted_palette[min_idx]
        min_color = LabColor(*min_datas[-1])
        max_path, max_datas = sorted_palette[max_idx]
        max_color = LabColor(*max_datas[-1])
        middle_idx = (min_idx + max_idx)//2
        delta_to_min = delta_e_cie2000(min_color, tile_color)
        delta_to_max = delta_e_cie2000(max_color, tile_color)
        if delta_to_min < deltaE_threshold:
            chosen_idx = min_idx
            break
        elif delta_to_max < deltaE_threshold:
            chosen_idx = max_idx
            break
        elif delta_to_min < delta_to_max:
            max_idx = middle_idx
        else:
            min_idx = middle_idx
    if max_idx - min_idx == 1:
        chosen_idx = max_idx
    pic_path, pic_datas = sorted_palette[chosen_idx]
    return pic_path

def photo_mosaic_datas(model_path, sorted_pics_list, tile_width, tile_height, pic_maxsize):
    '''
    Generates the datas for the result image by matching tiles from the model image with pics from the dataset

    Args:
        model_path (str) : path of the image to resize
        sorted_pics_list (list) : list of tuples containing
                                   pic_path (str) : path of the pic in the dataset
                                   pic_datas (tuple) containing
                                        datepic (str)
                                        orientation (int)
                                        img_ratio (float)
                                        avg_color (tuple) : (r, g, b) all floats 0.0 - 1.0
                                        avg_lab (tuple) : (lab_l, lab_a, lab_b) all floats
        tile_width (int) : width of the tile
        tile_height (int) : height of the tile
        pic_maxsize (tuple) containing
                maxwidth (int) : maximal width of the resized pic
                maxheight (int) : maximal height of the resized pic

    Returns:
        mosaic_datas (dict) with
                keys : tile (tuple), a rectangle defined by
                            x_left_top_corner (int) : x coordinate of the tile's left top corner
                            y_left_top_corner (int) : y coordinate of the tile's left top corner
                            x_right_bottom_corner (int) : x coordinate of the tile's right bottom corner
                            y_right_bottom_corner (int) : y coordinated of the tile's right bottom corner
                values:
                    close_pic (str) : path of a pic with a color close to the one from the model image's tile
    '''
    tiles_dict = model_analysis(model_path, tile_width, tile_height, pic_maxsize)
    mosaic_datas = {}
    for tile in tiles_dict.keys():
        tile_color = convert_color(sRGBColor(*tiles_dict[tile]), LabColor)
        close_pic = closest_pic(tile_color, sorted_pics_list)
        mosaic_datas[tile] = close_pic
    print('photo_mosaic_data generated')
    return mosaic_datas

def gen_photo_mosaic(photo_mosaic_data, tile_width, tile_height, pic_maxsize, scale=1):
    '''
    Generate the photo mosaic picture

    Args:
        photo_mosaic_data (dict) with
                keys : tile (tuple), a rectangle defined by
                            x_left_top_corner (int) : x coordinate of the tile's left top corner
                            y_left_top_corner (int) : y coordinate of the tile's left top corner
                            x_right_bottom_corner (int) : x coordinate of the tile's right bottom corner
                            y_right_bottom_corner (int) : y coordinated of the tile's right bottom corner
                values:
                    close_pic (str) : path of a pic with a color close to the one from the model image's tile
        tile_width (int) : width of the tile
        tile_height (int) : height of the tile
        pic_maxsize (tuple) containing
                maxwidth (int) : maximal width of the resized pic
                maxheight (int) : maximal height of the resized pic
        scale (int) : scale factor between the tile's size and the actual tile's picture's size

    Returns: message -> photo mosaic created

    '''
    new_width = pic_maxsize[0]
    new_height = int(new_width/(tile_width/tile_height))
    new_width = (new_width//tile_width)*tile_width*scale
    new_height = (new_height//tile_height)*tile_height*scale
    mosaic = Image.new('RGB', (new_width, new_height))
    for box, path in photo_mosaic_data.items():
        with Image.open(path) as pic:
            new_tile_width = tile_width*scale
            new_tile_height = tile_height*scale
            pic.draft(pic.mode, (new_tile_width*2, new_tile_height*2))
            tile_pic = pic.resize((tile_width*scale, tile_height*scale))
            new_box = tuple(coord*scale for coord in box)
            mosaic.paste(tile_pic, new_box)
    mosaic.save('photo_mosaic.png')
    return('photo mosaic created')

if __name__ == '__main__':

    new_dataset = 'new_dataset'
    if not os.path.exists(new_dataset):
        flatten_dataset(getfilespath('dataset'))
    else:
        print('dataset flattened already')

    if not os.path.exists('analyzed_dataset.txt'):
        datas = gen_dataset('dataset')
        save_dict(datas, 'analyzed_dataset.txt')
        pics_dict = datas
    else:
        pics_dict = open_dict('analyzed_dataset.txt')

    if not os.path.exists('sorted_dataset.txt'):
        with open('sorted_dataset.txt', 'w') as dataset_file:
            sorted_pics_list = NN_delta(pics_dict)
            dataset_file.write(json.dumps(sorted_pics_list))
            print('dataset sorted by DeltaE00')
    else:
        with open('sorted_dataset.txt', 'r') as dataset_file:
            sorted_pics_list = [tuple(data) for data in json.loads(dataset_file.read())]

    gen_sorted_palette(sorted_pics_list)

    model_path = 'dataset/Tram/DSC_0809.JPG'
    tile_ratio = 4/3
    tile_width = 12
    tile_height = int(tile_width/tile_ratio)
    pic_maxsize = (1024, 1024)

    print(basic_mosaic(model_path, tile_width, tile_height, pic_maxsize))

    if not os.path.exists('mosaic_datas.txt'):
        mosaic_dict = photo_mosaic_datas(model_path, sorted_pics_list, tile_width, tile_height, pic_maxsize)
        save_dict(mosaic_dict, 'mosaic_datas.txt')
    else:
        mosaic_dict = open_dict('mosaic_datas.txt')

    print(gen_photo_mosaic(mosaic_dict, tile_width, tile_height, pic_maxsize, scale=10))
