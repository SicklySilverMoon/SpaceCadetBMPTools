import numpy
from PIL import Image
import os
import shutil
import sys

#See: https://github.com/k4zmu2a/SpaceCadetPinball/blob/master/Doc/.dat%20file%20format.txt
#And: https://github.com/k4zmu2a/SpaceCadetPinball/blob/master/Doc/.dat%20dump.txt
class bmp8:
    def __init__(self, group_num, res_type, width, height, bmp_type, data):
        self.group_num = group_num 
        self.res_type = res_type
        self.width = width
        self.height = height
        self.bmp_type = bmp_type
        self.data = data
        
class bmp16:
    def __init__(self, group_num, width, height, stride, data):
        self.group_num = group_num 
        self.width = width
        self.height = height
        if stride >= 0:
            self.stride = stride
        elif width % 4 != 0:
            self.stride = width - (width % 4) + 4
        else:
            self.stride = width
        self.data = data

if __name__ == "__main__":
    bmp8_list = []
    bmp16_list = []
    palette = None

    with open(sys.argv[1], 'rb') as f:
        sig = f.read(21)
        if sig != b'\x50\x41\x52\x54\x4F\x55\x54\x28\x34\x2E\x30\x29\x52\x45\x53\x4F\x55\x52\x43\x45\x00':
            print("Not a valid 3D Pinball DAT file!")
            exit()
            
        f.read(150) #name, and description, useless to use
        filesize = int.from_bytes(f.read(4), "little")
        num_groups = int.from_bytes(f.read(2), "little")
        groupsize = int.from_bytes(f.read(4), "little")
        f.read(2) #Unknown quantity
        headersize = f.tell()
        #print(filesize)
        #print(num_groups)
        #print(groupsize) #This should be equal to filesize - header size which is 0xB7
        #print(f.tell())
        if filesize - headersize != groupsize:
            print("Warning: filesize - header size is not equal to group size, excess data somewhere!")
            
        group_num = -1
        while f.tell() - headersize != groupsize:
            group_num += 1
            num_entries = int.from_bytes(f.read(1), "little")
            for i in range(num_entries):
                type = int.from_bytes(f.read(1), "little")
                
                if type == 0: #known: type 0 is always followed by a single 2 byte value, unknown: anything beyond that
                    f.read(2)
                    continue
                    
                chunk_size = int.from_bytes(f.read(4), "little")
                
                if type == 1: #8bit bmp
                    res_type = int.from_bytes(f.read(1), "little")
                    width = int.from_bytes(f.read(2), "little")
                    height = int.from_bytes(f.read(2), "little")
                    f.read(4) #x and y pos
                    data_size = int.from_bytes(f.read(4), "little")
                    bmp_type = int.from_bytes(f.read(1), "little")
                    if bmp_type != 1:
                        print(f"Group {group_num} has a bmp_type of: {bmp_type} instead of expected 1")
                    if chunk_size - 14 != data_size:
                        print("Chunk entry is larger than remaining bitmap data at: " + hex(f.tell()) + "!")
                    data = f.read(data_size)
                    bmp8_list.append(bmp8(group_num, res_type, width, height, bmp_type, data))
                    continue
                elif type == 3: #Group name field, this could be quite useful later
                    f.read(chunk_size)
                    continue
                elif type == 5:
                    if palette != None:
                        print("Palette entry found more than once!")
                    if chunk_size != 0x400:
                        print("Palette at: " + hex(f.tell()) + " has a size of: " + hex(chunk_size) + " instead of 0x400!")
                    palette = []
                    raw_palette = f.read(chunk_size)
                    for i in range(0, len(raw_palette), 4):
                        color = tuple(numpy.frombuffer(raw_palette[i:i + 4], dtype=numpy.uint8, count=4))
                        palette.append( (color[2], color[1], color[0], 255) ) #Due to little endian oddities and numpy arrays using the machine type or something its better to do this
                        #255 b/c idk but despite specifying alpha the program sets it to 255 anyways
                    #Add Windows reserved colours
                    palette[0] = (0, 0, 0, 255)
                    palette[1] = (128, 0, 0, 255)
                    palette[2] = (0, 128, 0, 255)
                    palette[3] = (128, 128, 0, 255)
                    palette[4] = (0, 0, 128, 255)
                    palette[5] = (128, 0, 128, 255)
                    palette[6] = (0, 128, 128, 255)
                    palette[7] = (192, 192, 192, 255)
                    palette[8] = (192, 220, 192, 255)
                    palette[9] = (166, 202, 240, 255)
                    
                    palette[246] = (255, 251, 240, 255)
                    palette[247] = (160, 160, 164, 255)
                    palette[248] = (128, 128, 128, 255)
                    palette[249] = (255, 0, 0, 255)
                    palette[250] = (0, 255, 0, 255)
                    palette[251] = (255, 255, 0, 255)
                    palette[252] = (0, 0, 255, 255)
                    palette[253] = (255, 0, 255, 255)
                    palette[254] = (0, 255, 255, 255)
                    palette[255] = (255, 255, 255, 255)
                    #print(palette)
                elif type == 9: #String field, this could be somewhat useful(?) later
                    f.read(chunk_size)
                    continue
                elif type == 10: #Array of 16 bit integer pairs, could be useful
                    f.read(chunk_size)
                    continue
                elif type == 11: #Array of 32 bit integer pairs, could be useful
                    f.read(chunk_size)
                    continue
                elif type == 12: #16 bit bmp
                    width = int.from_bytes(f.read(2), "little")
                    height = int.from_bytes(f.read(2), "little")
                    stride = int.from_bytes(f.read(2), "little")
                    f.read(8) #Unknown junk
                    data_size = chunk_size - 14
                    if stride * 2 * height != data_size:
                        print("16 bit bmp at: " + hex(f.tell()) + " has a size vs. data length mismatch! Skipping.")
                        f.read(data_size)
                        continue
                    data = f.read(data_size)
                    bmp16_list.append(bmp16(group_num, width, height, stride, data))
                    continue
                else: #Undocumented stuff that may or may not exist
                    print("Unknown group type: " + str(type) + " encountered at: " + hex(f.tell()))
                    f.read(chunk_size)
            
        #print(bmp8_list)
        try:
            os.mkdir("bmps")
        except FileExistsError: #remove and recreate the dir if it exists
            shutil.rmtree("bmps")
            os.mkdir("bmps")
            
        array = numpy.zeros( (16, 16, 4), dtype = numpy.uint8)
        for x in range(16):
            for y in range(16):
                c = palette[x * 16 + y] #Yeah idk why but it works properly this way but not with y * 16 + x, i'm too tired to mess with it now
                array[x][y] = numpy.asarray(c, dtype = numpy.uint8)
        img = Image.fromarray(array)
        img.save("bmps/palette.png")
            
        bmp_num = 0
        for b in bmp8_list:
        
            indexed_stride = b.width
            if b.width % 4 != 0:
                indexed_stride = b.width - (b.width % 4) + 4
                
            array = numpy.zeros( (b.height, indexed_stride, 4), dtype=numpy.uint8)
            
            for y in range(b.height):
                for x in range(indexed_stride):
                    idx = y * indexed_stride + x
                    colour = palette[b.data[idx]]
                    array[y][x] = numpy.asarray(colour, dtype=numpy.uint8)
                    
            img = Image.fromarray(array)
            img = img.transpose(Image.FLIP_TOP_BOTTOM) #Extracting images the way we do seems to have them vertically flipped, easy solution, flip them here
            img.save("bmps/" + f"{b.group_num:03}" + "-8.png")
            bmp_num += 1
            
        bmp_num = 0
        for b in bmp16_list:
            array = numpy.zeros((b.height, b.stride), dtype=numpy.uint16)
            stride = b.stride * 2 #stride is given in pixels, with 2 bytes per pixel, so multiply by 2
            
            for y in range(b.height):
                for x in range(0, stride, 2):
                    idxF = y * stride + x
                    idxS = y * stride + x + 1
                    colour = int.from_bytes(b.data[idxF:idxS + 1], "little")
                    array[y][x // 2] = colour
            
            img = Image.fromarray(array)
            img = img.transpose(Image.FLIP_TOP_BOTTOM) #Same as above
            img.save("bmps/" + f"{b.group_num:03}" + "-16.png")
            bmp_num += 1