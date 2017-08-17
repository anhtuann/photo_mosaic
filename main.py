import os
from PIL import Image

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
    return (datepic, orientation)

def avg_rgb(image_path):
    with Image.open(image_path) as image:
        try:
            image.thumbnail((52, 52))
        except OSError:
            print(image_path, 'corrupted')
            return 'corrupted'
        colors = image.getcolors(maxcolors=((2**8)**3))
        total_pixels = len(colors)
        avg_r = 0
        avg_g = 0
        avg_b = 0
        for color in colors:
            count = color[0]
            r, g, b = color[1]
            avg_r += (count/total_pixels)*r**2
            avg_g += (count/total_pixels)*g**2
            avg_b += (count/total_pixels)*b**2
    return (int(avg_r**0.5), int(avg_g**0.5), int(avg_b**0.5))

dataset = getfilespath('dataset')
pics_dict = {}
orientation_dict = {}
for pic in dataset:
    file_extension = pic.split('.')[-1].lower()
    if file_extension == 'jpg' or file_extension == 'jpeg':
        datepic, orientation = extract_exif(pic)
        avg_color = avg_rgb(pic)
        pics_dict[pic] = (datepic, orientation, avg_color)
        try:
            orientation_dict[orientation] += 1
        except KeyError:
            orientation_dict[orientation] = 1
