import os
import fractions
from PIL import Image
from PIL import ImageStat

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
        img_ratio = fractions.Fraction(infos[40962], infos[40963])
    return (datepic, orientation, img_ratio)

class CustomStat(ImageStat.Stat):
    def _getmean2(self):
        v = []
        for i in self.bands:
            v.append((self.sum2[i] / self.count[i])**0.5)
        return v

def avg_rgb(image_path):
    with Image.open(image_path) as image:
        try:
            image.thumbnail((512, 512))
        except OSError:
            print(image_path, 'corrupted')
            return 'corrupted'
        avg_r, avg_g, avg_b = map(int, CustomStat(image)._getmean2())
    return (avg_r, avg_g, avg_b)

dataset = getfilespath('dataset')
pics_dict = {}
orientation_dict = {}
common_aspect_ratios = [fractions.Fraction(1, 1),
                        fractions.Fraction(5, 4),
                        fractions.Fraction(4, 3),
                        fractions.Fraction(3, 2),
                        fractions.Fraction(5, 3),
                        fractions.Fraction(16, 9),
                        fractions.Fraction(3, 1)]

for pic in dataset:
    file_extension = pic.split('.')[-1].lower()
    if file_extension == 'jpg' or file_extension == 'jpeg':
        datepic, orientation, img_ratio = extract_exif(pic)
        #avg_color = 1
        avg_color = avg_rgb(pic)
        pics_dict[pic] = (datepic, orientation, img_ratio, avg_color)
        try:
            orientation_dict[orientation] += 1
        except KeyError:
            orientation_dict[orientation] = 1
