import os
from PIL import Image

# Analysis of the dataset

def getfilespath(root_path):
    files = []
    for (dirpath, dirnames, filenames) in os.walk(root_path):
        files.extend([os.path.join(dirpath, filename) for filename in filenames])
    return files

def extract_exif(image_path):
    image = Image.open(image_path)
    infos = image._getexif()
    # tags identified by ExifTags
    datepic = infos[36867]
    #modelcam = infos[272]
    orientation = infos[274]
    return (datepic, orientation)

dataset = getfilespath('dataset')
datas_dict = {}
orientation_dict = {}
for pic in dataset:
    file_extension = pic.split('.')[-1].lower()
    if file_extension == 'jpg' or file_extension == 'jpeg':
        datepic, orientation = extract_exif(pic)
        datas_dict[pic] = (datepic, orientation)
        try:
            orientation_dict[orientation] += 1
        except KeyError:
            orientation_dict[orientation] = 1
print(orientation_dict.items())
        
