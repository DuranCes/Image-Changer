#!/usr/bin/env python3

import sys
import math
import base64
import tkinter

from io import BytesIO
from PIL import Image as PILImage


class Image:
    def __init__(self, width, height, pixels):
        self.width = width
        self.height = height
        self.pixels = pixels

    def get_pixel(self, x, y):
        # turns 2 dimensional ordering into 1 dimensional for access
        return self.pixels[x+y*self.width]

    #Gets the new correlated pixel without rounding or capping using kernel
    def get_corr_pixel(self, x, y, kernel):
        edge = math.floor(len(kernel)/2)
        kern_x = 0
        kern_y = 0
        final = 0
        for r in range(x-edge, x+edge+1):

            #If r is out of bounds, then it is set to the bound
            if r < 0:
                r = 0
            if r >= self.width:
                r = self.width-1
            kern_y = 0
            for c in range(y-edge, y+edge+1):
                #If c is out of bounds, then i t is set to the bound
                if c < 0:
                    c = 0
                if c >= self.height:
                    c = self.height-1
                final += kernel[kern_x][kern_y]*self.get_pixel(r, c)
                kern_y+=1
            kern_x+=1
        return final

    def set_pixel(self, x, y, c):
        self.pixels[x+y*self.width] = c

    def apply_per_pixel(self, func):
        result = Image.new(self.width, self.height)
        for x in range(result.width):
            for y in range(result.height):
                color = self.get_pixel(x, y)
                newcolor = func(color)
                result.set_pixel(x, y, newcolor)
        return result

    def inverted(self):
        return self.apply_per_pixel(lambda c: 255-c)

    def blurred(self, n):
        kernel = [[float(1)/(n*n) for x in range(n)] for x in range(n)]
        return self.corr(kernel)

    def sharpened(self, n):
        middle = int(n/2)
        kernel = [[-float(1)/(n*n) for x in range(n)] for x in range(n)]
        kernel[middle][middle] = kernel[middle][middle] + 2
        return self.corr(kernel)

    def edges(self):
        kernel_1 = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
        kernel_2 = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
        result = Image.new(self.width, self.height)
        for x in range(self.width):
            for y in range(self.height):
                new_pixel_1 = self.get_corr_pixel(x, y, kernel_1)
                new_pixel_2 = self.get_corr_pixel(x, y, kernel_2)
                new_pixel = math.sqrt(new_pixel_2**2+new_pixel_1**2)
                if new_pixel > 255:
                    new_pixel = 255
                if new_pixel < 0:
                    new_pixel = 0
                new_pixel = round(new_pixel)
                result.set_pixel(x, y, new_pixel)
        return result


    # Below this point are utilities for loading, saving, and displaying
    # images, as well as for testing.

    def __eq__(self, other):
        return all(getattr(self, i) == getattr(other, i)
                   for i in ('height', 'width', 'pixels'))

    def __repr__(self):
        return "Image(%s, %s, %s)" % (self.width, self.height, self.pixels)

    @classmethod
    def load(cls, fname):
        """
        Loads an image from the given file and returns an instance of this
        class representing that image.  This also performs conversion to
        grayscale.

        Invoked as, for example:
           i = Image.load('test_images/cat.png')
        """
        with open(fname, 'rb') as img_handle:
            img = PILImage.open(img_handle)
            img_data = img.getdata()
            if img.mode.startswith('RGB'):
                pixels = [round(.299*p[0] + .587*p[1] + .114*p[2]) for p in img_data]
            elif img.mode == 'LA':
                pixels = [p[0] for p in img_data]
            elif img.mode == 'L':
                pixels = list(img_data)
            else:
                raise ValueError('Unsupported image mode: %r' % img.mode)
            w, h = img.size
            return cls(w, h, pixels)

    @classmethod
    def new(cls, width, height):
        """
        Creates a new blank image (all 0's) of the given height and width.

        Invoked as, for example:
            i = Image.new(640, 480)
        """
        return cls(width, height, [0 for i in range(width*height)])

    def save(self, fname, mode='PNG'):
        """
        Saves the given image to disk or to a file-like object.  If fname is
        given as a string, the file type will be inferred from the given name.
        If fname is given as a file-like object, the file type will be
        determined by the 'mode' parameter.
        """
        out = PILImage.new(mode='L', size=(self.width, self.height))
        out.putdata(self.pixels)
        if isinstance(fname, str):
            out.save(fname)
        else:
            out.save(fname, mode)
        out.close()

    def gif_data(self):
        """
        Returns a base 64 encoded string containing the given image as a GIF
        image.

        Utility function to make show_image a little cleaner.
        """
        buff = BytesIO()
        self.save(buff, mode='GIF')
        return base64.b64encode(buff.getvalue())

    def show(self):
        """
        Shows the given image in a new Tk window.
        """
        global WINDOWS_OPENED
        if tk_root is None:
            # if tk hasn't been properly initialized, don't try to do anything.
            return
        WINDOWS_OPENED = True
        toplevel = tkinter.Toplevel()
        # highlightthickness=0 is a hack to prevent the window's own resizing
        # from triggering another resize event (infinite resize loop).  see
        # https://stackoverflow.com/questions/22838255/tkinter-canvas-resizing-automatically
        canvas = tkinter.Canvas(toplevel, height=self.height,
                                width=self.width, highlightthickness=0)
        canvas.pack()
        canvas.img = tkinter.PhotoImage(data=self.gif_data())
        canvas.create_image(0, 0, image=canvas.img, anchor=tkinter.NW)
        def on_resize(event):
            # handle resizing the image when the window is resized
            # the procedure is:
            #  * convert to a PIL image
            #  * resize that image
            #  * grab the base64-encoded GIF data from the resized image
            #  * put that in a tkinter label
            #  * show that image on the canvas
            new_img = PILImage.new(mode='L', size=(self.width, self.height))
            new_img.putdata(self.pixels)
            new_img = new_img.resize((event.width, event.height), PILImage.NEAREST)
            buff = BytesIO()
            new_img.save(buff, 'GIF')
            canvas.img = tkinter.PhotoImage(data=base64.b64encode(buff.getvalue()))
            canvas.configure(height=event.height, width=event.width)
            canvas.create_image(0, 0, image=canvas.img, anchor=tkinter.NW)
        # finally, bind that function so that it is called when the window is
        # resized.
        canvas.bind('<Configure>', on_resize)
        toplevel.bind('<Configure>', lambda e: canvas.configure(height=e.height, width=e.width))

        # when the window is closed, the program should stop
        toplevel.protocol('WM_DELETE_WINDOW', tk_root.destroy)

    #Creates a new image using kernel on current image
    def corr(self, kernel):
        result = Image.new(self.width, self.height)
        for x in range(self.width):
            for y in range(self.height):
                new_pixel = self.get_corr_pixel(x, y, kernel)
                if new_pixel > 255:
                    new_pixel = 255
                if new_pixel < 0:
                    new_pixel = 0
                new_pixel = round(new_pixel)
                result.set_pixel(x, y, new_pixel)
        return result



if __name__ == '__main__':
    # code in this block will only be run when you explicitly run your script,
    # and not when the tests are being run.  this is a good place for
    # generating images, etc.

    test = Image.load('test_images/pigbird.png')
    new = test.corr

    # the following code will cause windows from Image.show to be displayed
    # properly, whether we're running interactively or not:
    if WINDOWS_OPENED and not sys.flags.interactive:
        tk_root.mainloop()
