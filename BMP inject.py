import numpy
from PIL import Image
import os
import sys

#See: https://github.com/k4zmu2a/SpaceCadetPinball/blob/master/Doc/.dat%20file%20format.txt
#And: https://github.com/k4zmu2a/SpaceCadetPinball/blob/master/Doc/.dat%20dump.txt
groups_list = []
palette = []
img_dict = {}

if (len(sys.argv) < 3):
    print("The first argument should be a path to PINBALL.DAT which will images from the second argument (a directory) injected into it.")
    exit()

if not os.path.isdir(sys.argv[2]):
    print("The second argument should be a directory!")
    exit()

onlyfiles = [f for f in os.listdir(sys.argv[2]) if os.path.isfile(os.path.join(sys.argv[2], f)) and f != "palette.png"]
onlyfiles.sort()
for s in onlyfiles:
    if not s.endswith(".png"):
        continue
    #Should only be used with the same file name schema that "BMP extract.py" outputs
    img_dict.update( {s.split(".")[0] : os.path.join(sys.argv[2], s)} ) #from 001-8.png would get 001-8
    groups_list.append(int(s.split("-")[0]))
    
groups_list = list(set(groups_list)) #Remove dupes
#print(groups_list)

pal_img = Image.open(os.path.join(sys.argv[2], "palette.png"))
pal_img = pal_img.convert("RGBA")
if pal_img.width * pal_img.height != 256:
    print("Palette file does not have 256 colours")
    exit()

for y in range(pal_img.height):
    for x in range(pal_img.width):
        pixel = pal_img.getpixel( (x, y) )
        #print(pixel)
        palette.append( (pixel, y * pal_img.width + x) ) #Build a colour:index dict
#print(palette)

with open(sys.argv[1], 'r+b') as f:
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
            
            if group_num not in groups_list: #If the group number isn't one of the ones we have a replacement image for, skip over all its contents (which involves a few loops)
                #print(group_num)
                f.read(chunk_size)
                continue
            
            if type == 1: #8bit bmp
                res_type = int.from_bytes(f.read(1), "little")
                width = int.from_bytes(f.read(2), "little")
                height = int.from_bytes(f.read(2), "little")
                x = int.from_bytes(f.read(2), "little")
                y = int.from_bytes(f.read(2), "little")
                data_size = int.from_bytes(f.read(4), "little")
                bmp_type = int.from_bytes(f.read(1), "little")
                
                img = Image.open(img_dict[f"{group_num:03}-8"])
                if img.width * img.height != data_size:
                    print(f"Image has a size of: {img.width * img.height} where it should be: {data_size}, skipping")
                    f.read(data_size)
                    continue
                    
                    
                img = img.convert("RGBA")
                img = img.transpose(Image.FLIP_TOP_BOTTOM) #We flipped while saving so we flip back here
                array = numpy.zeros(img.height * img.width, dtype = numpy.uint8)
                for y in range(img.height):
                    for x in range(img.width):
                        pixel = img.getpixel( (x, y) )
                        #print(pixel)
                        idx = -1
                        for c in palette:
                            if pixel == c[0]:
                                idx = c[1]
                                break
                                
                        if idx == -1:
                            print(f"Image has an invalid colour: {pixel}, replacing with black")
                            idx = 0
                        array[y * img.width + x] = idx
                f.write(array.tobytes())
                continue
                
            elif type == 5:
                if chunk_size != 0x400:
                    print("Palette at: " + hex(f.tell()) + " has a size of: " + hex(chunk_size) + " instead of 0x400! Exiting!")
                    exit()
                array = numpy.zeros(0x400, dtype = numpy.uint8)
                idx = 0
                for c in palette:
                    array[idx    ] = c[0][2]
                    array[idx + 1] = c[0][1]
                    array[idx + 2] = c[0][0]
                    array[idx + 3] = 0
                    idx += 4
                    
                #Check for Windows reserved
                reserved_in_place = True
                reserved_in_place = False if palette[0] == (0, 0, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[1] == (128, 0, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[2] == (0, 128, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[3] == (128, 128, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[4] == (0, 0, 128, 255) else reserved_in_place
                reserved_in_place = False if palette[5] == (128, 0, 128, 255) else reserved_in_place
                reserved_in_place = False if palette[6] == (0, 128, 128, 255) else reserved_in_place
                reserved_in_place = False if palette[7] == (192, 192, 192, 255) else reserved_in_place
                reserved_in_place = False if palette[8] == (192, 220, 192, 255) else reserved_in_place
                reserved_in_place = False if palette[9] == (166, 202, 240, 255) else reserved_in_place

                reserved_in_place = False if palette[246] == (255, 251, 240, 255) else reserved_in_place
                reserved_in_place = False if palette[247] == (160, 160, 164, 255) else reserved_in_place
                reserved_in_place = False if palette[248] == (128, 128, 128, 255) else reserved_in_place
                reserved_in_place = False if palette[249] == (255, 0, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[250] == (0, 255, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[251] == (255, 255, 0, 255) else reserved_in_place
                reserved_in_place = False if palette[252] == (0, 0, 255, 255) else reserved_in_place
                reserved_in_place = False if palette[253] == (255, 0, 255, 255) else reserved_in_place
                reserved_in_place = False if palette[254] == (0, 255, 255, 255) else reserved_in_place
                reserved_in_place = False if palette[255] == (255, 255, 255, 255) else reserved_in_place

                if not reserved_in_place:
                    print("Warning: At least one of the first or last 10 colours in the palette have been replaced, however in game the colours will display as they were before due to being Windows default reserved colours!")
                
                array[0 : 10 * 4] = [0] * 10 * 4
                array[246 * 4 : 246 * 4 + 9 * 4] = [0] * 9 * 4
                array[255 * 4 : 255 * 4 + 4] = [0xFC, 0xFC, 0xFC, 0x00] #The actual file has white at the end like this
                
                f.write(array.tobytes())
                #print(array.tobytes())
                
            elif type == 12:
                width = int.from_bytes(f.read(2), "little")
                height = int.from_bytes(f.read(2), "little")
                stride = int.from_bytes(f.read(2), "little")
                f.read(8) #Unknown junk
                data_size = chunk_size - 14
                if stride * 2 * height != data_size:
                    print("16 bit bmp at: " + hex(f.tell()) + " has a size vs. data length mismatch! Skipping.")
                    f.read(data_size)
                    continue
                    
                img = Image.open(img_dict[f"{group_num:03}-16"])
                img = img.transpose(Image.FLIP_TOP_BOTTOM) #We flipped while saving so we flip back here
                array = numpy.array(img, dtype = numpy.uint16, copy = False)
                bytes = array.tobytes()
                if len(bytes) != data_size:
                    print(f"Image has a size of: {len(bytes)} where it should be: {data_size}, skipping")
                    f.read(data_size)
                    continue
                f.write(bytes)
                continue
                
            else: #Undocumented stuff that may or may not exist
                f.read(chunk_size)