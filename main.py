#!/usr/bin/env python
import os
import argparse
import traceback

import numpy as np
import OpenEXR, Imath, array, math
from PIL import Image

def main(args):
    FLOAT_MAX_32 = (2-pow(2,-23)) * pow(2,127)

    # initialize : out_min
    try:
        out_min = float(args.outMin) if args.outMin is not None else 0.1
        if out_min < 0.0 or out_min > 1.0:
            raise Exception()
    except:
        print("Specify 0.0 - 1.0 for out_min option. (outMin: {0})".format(out_min))
        return

    # initialize : out_max
    try:
        out_max = float(args.outMax) if args.outMax is not None else 0.9
        if out_max < 0.0 or out_max > 1.0:
            raise Exception()
    except:
        print("Specify 0.0 - 1.0 for out_max option. (outMax: {0})".format(out_max))
        return

    if out_max < out_min:
        print("OutMax must be greater then or equal to outMin. (outMin: {0}, outMax: {1})".format(out_min,out_max))
        return

    # As EXR is inverted grayscale, swap out range
    tmp = out_max
    out_max = 1 - out_min
    out_min = 1 - tmp

    # initialize : value_max, dtype, pillow_mode
    if args.depth is None or args.depth == '8': # 8bit grayscale
        value_max = pow(2,8) -1
        value_type = np.uint8
        pillow_mode = 'L'
    elif args.depth == '16': # 16bit gray scale
        value_max = pow(2,16) - 1
        value_type = np.uint16
        pillow_mode = 'I;16'
    else:
        print("Specify 8 or 16 for depth option.")
        return

    try:
        exr = OpenEXR.InputFile(args.path)

        #from pprint import pprint
        #pprint(exr.header()) # check channel's name

        # get values
        dw = exr.header()['dataWindow']
        size = (dw.max.y-dw.min.y+1, dw.max.x-dw.min.x+1) # (height, width)
        
        ptype = Imath.PixelType(Imath.PixelType.FLOAT)
        y_bytes = exr.channels('Y', ptype)[0]
        y = np.array(array.array('f', y_bytes))

        # get data range excluding FLOAT_MAX_32
        (y_min, y_max) = (None, None)
        for p in y:
            if math.isclose(p, FLOAT_MAX_32):
                continue
            if y_min is None: # Initialize (min, maz)
                (y_min, y_max) = (p, p)
                continue

            if p < y_min:
                y_min = p
            if p > y_max:
                y_max = p

        if y_min is None: # when all pixels are FLOAT_MAX_32
            (y_min, y_max) = (FLOAT_MAX_32, FLOAT_MAX_32)

        # change values
        post_y = []
        out_range = out_max - out_min

        if math.isclose(y_min, y_max): # if monocolored
            for p in y:
                if math.isclose(p, FLOAT_MAX_32):
                    post_y.append(value_max) # leave pure black pixel
                else:
                    post_y.append(round( (out_min+out_max)*0.5*value_max )) # midpoint of out range, using banker's round might be OK
        else:
            for p in y:
                if math.isclose(p, FLOAT_MAX_32):
                    post_y.append(value_max) # leave pure black pixel
                else:
                    post_y.append(round( ((p-y_min)/(y_max-y_min)) * (out_range*value_max) + out_min*value_max )) # exr is inverted image, using banker's round might be OK

        # create img
        post_y = [value_max - x for x in post_y] # invert color
        data = np.reshape(post_y, size).astype(value_type)
        #print(data)
        img = Image.fromarray(data, pillow_mode)
        #img.show()
        
        # save img
        img_name = os.path.split(args.path)[1]
        img_name = img_name[:img_name.rfind('.')] + '.png' if img_name.rfind('.') >= 0 else img_name + '.png'
        img_name = os.path.join(os.path.split(args.path)[0], img_name)
        img.save(img_name)
        
    except:
        print(traceback.format_exc())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=u'Auto level EXR depth map.')
    parser.add_argument('path', help='/Path/To/InputFile.exr')
    parser.add_argument('--outMin', help="Min of Auto Level range (0.0 - 1.0, default 0.1)", required=False)
    parser.add_argument('--outMax', help="Max of Auto Level range (0.0 - 1.0, default 0.9)", required=False)
    parser.add_argument('--depth', help="Output grayscale's precision (bit) (8 or 16, default 8)", required=False)
    args = parser.parse_args()

    main(args)
