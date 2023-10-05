# pthon3
import sys
import os
import shutil
import zipfile
import struct
from PIL import Image
import xml.dom.minidom as DOM

import template_watchface_pb2
import wf_hwhd07_pb2
import xml_format

version = "1.3-20230826"

# com.huawei.watchface for band
class watchface_band:
    def __init__(self):
        self.header = None    #2bytes, 0x0002 or 0x0001
        self.xmllen = None    #2bytes
        self.maplen = None    #4bytes
        self.binlen = None    #4bytes
        self.blanks = None    #4bytes, 0x00 0x00 0x00 0x00

        self.xmloffset = 0x10    #16
        self.mapoffset = None    #mapoffset = xmloffset + xmllen
        self.binoffset = None    #binoffset = xmloffset + xmllen + maplen

        self.xmldata = None    #Nanopb to bin
        self.mapdata = None    #(imgoffer + imglen) * n, imgoffer: 4bytes, imglen: 4bytes
        self.bindata = None    #bindata_header + imgzipdata * n

# BMP image file data
class bmp_f:
    def __init__(self):
        self.file_header = None    #bmp file header
        self.info_header = None    #bmp info header
        self.pixels = None    #bmp pixels data


class watchface_unpack:
    def __init__(self):
        self.bin_sign = b"UUUU\x01\x00\x00\x01"    #8bytes
        
        # HWHD01:390*390, HWHD02:454*454, HWHD06:280*456, HWHD07(band):194*368, HWHD09:466*466, HWHD10:320*360, HWHD11:336*480, HWHD12:240*240
        self.screenlist = ["HWHD01", "HWHD02", "HWHD06", "HWHD07", "HWHD09", "HWHD10", "HWHD11", "HWHD12", ]
        
        self.file_size = 0
        self.imgs_filename = []
        self.screentype = ""
        self.descriptionxmlpath = ""
        self.descriptionxml = "description.xml"
        self.huaweiwatchface = "com.huawei.watchface"
        self.watchfacebin = "watchface.bin"
        self.watchfacedir = "watchface"

    # 读取输入的文件，可能是压缩包，也可能是 watchface bin 类型的文件
    # 如果 com.huawei.watchface 文件也是压缩包，将会进一步解压
    def read(self, bin_file, output_dir):
        data_in = None
        zis = None
        
        file_type = self.check_file_type(bin_file)
        if file_type == 99 :    #zip file
            zis = zipfile.ZipFile(bin_file, 'r')
            found_huaweiwatchface = False
            found_watchfacebin = False
            if os.path.exists(output_dir) :
                print(f"Info: {output_dir} directory already exists")
            if self.descriptionxml in zis.namelist():
                zis.extract(self.descriptionxml, output_dir)
                self.read_des_xml(output_dir + "/" + self.descriptionxml)
            for zip_entry in zis.namelist():
                if zip_entry == self.huaweiwatchface:
                    data_in = zis.open(zip_entry)
                    bin_file2 = os.path.abspath(bin_file + "/" + self.huaweiwatchface)
                    file_type = self.check_data_type(data_in, bin_file2)
                    found_huaweiwatchface = True
                    if file_type == 99 :    #zip file
                        zis.extract(zip_entry, output_dir)
                        bin_file2 = os.path.abspath(output_dir + "/" + self.huaweiwatchface)
                        output_dir2 = os.path.abspath(output_dir + "/" + self.huaweiwatchface + "_out")
                        self.read(bin_file2, output_dir2)
                        return
                    elif file_type == 1 or file_type == 2 :    #watchface file
                        self.file_size = zis.getinfo(zip_entry).file_size
                        bin_file2 = os.path.abspath(bin_file + "/" + self.huaweiwatchface)
                        output_dir2 = os.path.abspath(output_dir + "/" + self.huaweiwatchface + "_out")
                        self.read_bin(data_in, bin_file2, output_dir2)
                    else :
                        return
                # if zip_entry == self.watchfacebin:
                    # data_in = zis.open(zip_entry)
                    # self.file_size = zis.getinfo(zip_entry).file_size
                    # file_type = self.check_data_type(data_in, bin_file + "/" + self.watchfacebin)
                    # self.read_bin(data_in, bin_file + "/" + self.watchfacebin, output_dir + "/" + self.watchfacebin + "_out")
                    # found_watchfacebin = True
                if zip_entry.startswith(self.watchfacedir + "/"):
                    zis.extract(zip_entry, output_dir)
                    found_watchfacedir = True
            # if not found_huaweiwatchface and not found_watchfacebin:
                # print(f"Info: {bin_file} doesn't contain {self.huaweiwatchface} or {self.watchfacebin} file")
            if not found_huaweiwatchface:
                if not bin_file.endswith(self.huaweiwatchface):
                    print(f"Info: {bin_file} doesn't contain {self.huaweiwatchface}")
                return
        elif file_type == 1 or file_type == 2 :    #watchface file
            data_in = open(bin_file, 'rb')
            self.file_size = os.path.getsize(bin_file)
            self.read_bin(data_in, bin_file, output_dir)

        if zis is not None:
            zis.close()
        if data_in is not None:
            data_in.close()

    # 读取 description.xml 文件，解析文件，获取一些信息
    def read_des_xml(self, des_xml_file):
        self.descriptionxmlpath = os.path.abspath(des_xml_file)
        if os.path.exists(self.descriptionxmlpath):
            dom = DOM.parse(self.descriptionxmlpath)
            root = dom.documentElement    #HwTheme
            
            for child in root.childNodes :
                if child.nodeName == 'title':
                    print(f">>>> The title is {child.firstChild.data}")
                elif child.nodeName == 'screen':
                    self.screentype = child.firstChild.data
                    print(f">>>> The screen type is {self.screentype}")
                elif child.nodeName == 'version':
                    print(f">>>> The version is {child.firstChild.data}")
            
            if self.screentype not in self.screenlist:
                self.screentype = "UNSUPPORTED"

    # 读取 watchface bin 类型的文件，解析并处理
    def read_bin(self, data_in, file_name, output_dir):
        output_dir = os.path.abspath(output_dir)
        if os.path.exists(output_dir) :
            print(f"Info: {output_dir} directory already exists")
        os.makedirs(output_dir, exist_ok=True)
        output_dir_res = os.path.abspath(output_dir + "/res")
        if os.path.exists(output_dir_res) :
            print(f"Info: {output_dir_res} directory already exists")
        os.makedirs(output_dir_res, exist_ok=True)

        print("")
        print(f"Processing file {file_name}")
        
        wfbin = watchface_band()
        data_in.seek(0)
        tmpdata = data_in.read(16)
        wfbin.header, wfbin.xmllen, wfbin.maplen, wfbin.binlen, wfbin.blanks = struct.unpack("2H3L", tmpdata)
        if wfbin.header > 2 or wfbin.blanks != 0x0 :
            print(f"Info: {file_name} header is incorrect")
        if wfbin.maplen % 8 != 0 :
            print(f"Info: {file_name} index map size is incorrect")
        wfbin.xmloffset = 16
        wfbin.mapoffset = wfbin.xmloffset + wfbin.xmllen
        wfbin.binoffset = wfbin.xmloffset + wfbin.xmllen + wfbin.maplen
        
        wfbin.xmldata = data_in.read(wfbin.xmllen)
        wfbin.mapdata = data_in.read(wfbin.maplen)
        wfbin.bindata = data_in.read(wfbin.binlen)
        
        if wfbin.binlen - len(wfbin.bindata) > 2:
            print(f"Info: {file_name} image bin size is incorrect")
        
        # with open(output_dir + "/watchfacebin_xml.bin", "wb") as f:
            # f.write(wfbin.xmldata)
        # with open(output_dir + "/watchfacebin_map.bin", "wb") as f:
            # f.write(wfbin.mapdata)
        # with open(output_dir + "/watchfacebin_img.bin", "wb") as f:
            # f.write(wfbin.bindata)
        
        self.parse_img(wfbin, file_name, output_dir_res)
        self.parse_xml(wfbin, file_name, output_dir)
        
        return()

    # 检查输入文件的类型，先打开它，压缩包或者watchface bin
    def check_file_type(self, bin_file):
        bin_file = os.path.abspath(bin_file)
        if not os.path.isfile(bin_file):
            print(f"Err: {bin_file} does not exist or is not a file")
            return 0    #unsupported file type
        data_in = open(bin_file, 'rb')
        file_type = self.check_data_type(data_in, bin_file)
        data_in.close()
        return file_type

    # 检查已打开文件的类型，压缩包或者watchface bin
    def check_data_type(self, data_in, file_name):
        data_in.seek(0)
        tmpdata = data_in.read(4)
        binheader1, binheader2 = struct.unpack("HH", tmpdata)
        data_type = 0    #unsupported file type
        # print(f"{file_name} file header is {tmpdata.hex()}")
        if binheader1 == 0x4B50 and binheader2 == 0x0403:
            data_type = 99    #zip file
            print(f"Info: {file_name} is ZIP file")
        elif binheader1 > 0 and binheader1 <= 9 and binheader2 >= 4:
            data_in.seek(0)
            buf = data_in.read()
            bin_sign_offset = buf.find(self.bin_sign)
            data_type = binheader1    #watchface file
            print(f"Info: {file_name} is huawei watchface bin v{data_type} file")
            if bin_sign_offset <= 0 :
                print(f"Info: {file_name} may be unsupported file type")
        if data_type == 0 :
            print(f"Info: {file_name} is unsupported file type")
        return data_type

    # 解析并生成xml文件
    def parse_xml(self, wfbin, file_name, output_dir):
        print("")
        print("**** Start parse xml file ****")

        if self.screentype == "HWHD07":
            protobuf_object = wf_hwhd07_pb2.hwhd07()
        # elif self.screentype == "HWHD07":
            # protobuf_object = template_watchface_pb2.hwhd07()
        else:
            print(f"Info: unsupported screen type or no {self.descriptionxml} file")
            protobuf_object = template_watchface_pb2.watchface()
            
        protobuf_object.ParseFromString(wfbin.xmldata)
        pbfilename = output_dir + "/fake_v11_watch_face_config.pb"
        with open(pbfilename, "w") as f:
            f.write(str(protobuf_object))
        print(f"The ThemeStudio v11.x protobuf file path is {os.path.abspath(pbfilename)}")
        
        dom11, dom10 = xml_format.MessageToDOM(protobuf_object, self.imgs_filename)
        xmlfilename = output_dir + "/fake_v11_watch_face_config.xml"
        with open(xmlfilename, "w", encoding="utf-8") as f:
            dom11.writexml(f, indent="", addindent="    ", newl="\n", encoding="utf-8")
        print(f"The ThemeStudio v11.x config xml file path is {os.path.abspath(xmlfilename)}")
        # xmlfilename = output_dir + "/fake_v10_watch_face_config.xml"
        # with open(xmlfilename, "w", encoding="utf-8") as f:
            # dom10.writexml(f, indent="", addindent="    ", newl="\n", encoding="utf-8")
        # print(f"The v10.x config xml file path is {os.path.abspath(xmlfilename)}")
        
        if os.path.exists(self.descriptionxmlpath):
            xmlfilename = os.path.abspath(output_dir + "/watch_face_info.xml")
            shutil.copyfile(self.descriptionxmlpath, xmlfilename)
            print(f"The info xml file path is {xmlfilename}")
        
        print("**** End parse xml file ****")
        
    # 解析并生成图片文件
    def parse_img(self, wfbin, file_name, output_dir):
        print("**** Start parse image files ****")
        index_size = int(wfbin.maplen / 8)
        print(f"Find {index_size} image files")
        ims_list = []
        ims_type = []
        self.imgs_filename = []
        
        for i in range(index_size) :
            offset, imgsize = struct.unpack(f"LL", wfbin.mapdata[8*i : (8*i+8)])
            data_in = wfbin.bindata[offset : (offset + imgsize)]
            print(f">>>> Position->{wfbin.binoffset + offset}")

            imgtype = self.read_img_header(data_in)
            if imgtype == "PNG":
                img = self.read_png_img(data_in)
            elif imgtype[:3] == "BMP":
                img = bmp_f()
                self.read_bmp_img(data_in, img, imgtype)
            else:
                img = None
                print("Info: find unkown type image, skipped")

            ims_list.append(img)
            ims_type.append(imgtype)
        print("**** End parse image files ****")

        print("")
        print("**** Start output image files ****")
        for i, img in enumerate(ims_list):
            pi = str(i+1).rjust(3,'0')
            filename = f"A100_{pi}.{ims_type[i][:3].lower()}"
            self.imgs_filename.append(filename)
            print(f"Processing {filename}")
            img_path = os.path.join(output_dir, filename)
            if ims_type[i] == "PNG":  # write PNG file
                img.save(img_path, ims_type[i])
            elif ims_type[i][:3] == "BMP":  # write BMP file
                with open(img_path, "wb") as f:
                    f.write(img.file_header)
                    f.write(img.info_header)
                    f.write(img.pixels)

        print("**** End output image files ****")

    def read_img_header(self, data_in):
        headertype="UnkownType"
        if len(data_in) < 4:
            print("Info: image bin size is too short")
            return headertype

        h1, h2 = struct.unpack("HH", data_in[:4])
        if h1 == 0x2345 :
            if h2 == 0x8888 :
                headertype = "PNG"
            elif h2 == 0xF565 :
                headertype = "BMP565"
            elif h2 == 0xF555 :
                headertype = "BMP555"
            elif h2 == 0xF888 :
                headertype = "BMP888"
        print(f"header: {data_in[:4].hex()} -> {headertype[:3]}")
        return headertype

    def read_png_img(self, data_in):
        #4bytes header + 2bytes width + 2bytes height
        width, height = struct.unpack("HH", data_in[4:8])
        print(f"Width->{width}, Height->{height}")

        pngdata = bytearray()
        pos = 8
        while pos < len(data_in):
            b, g, r, a = struct.unpack("4B", data_in[pos : (pos + 4)])
            pos += 4
            if b == 0x89 and g == 0x67 and r == 0x45 and a == 0x23:
                b, g, r, a = struct.unpack("4B", data_in[pos : (pos + 4)])
                pos += 4
                count = struct.unpack("L", data_in[pos : (pos + 4)])
                pos += 4
                for i in range(count[0]):
                    pngdata.append(r)
                    pngdata.append(g)
                    pngdata.append(b)
                    pngdata.append(a)
            else:
                pngdata.append(r)
                pngdata.append(g)
                pngdata.append(b)
                pngdata.append(a)

        if len(pngdata) < width * height * 4 :
            print("Info: image data size is incorrect")
        return Image.frombytes("RGBA", (width, height), bytes(pngdata))

    def read_bmp_img(self, data_in, bmp_file, mode):
        #4bytes header + 2bytes width + 2bytes height
        width, height = struct.unpack("HH", data_in[4:8])
        print(f"Width->{width}, Height->{height}")

        if mode == "BMP565" :
            # BMP文件头和信息头RGB565
            bmp_file.file_header = struct.pack("<2sIHHI", b'BM', 14 + 56 + width * height * 2, 0, 0, 14 + 56)
            bmp_file.info_header = struct.pack("<IIIHHIIIIIIIIII", 56, width, height, 1, 16, 3, width * height * 2, 2834, 2834, 0, 0,   0xF800, 0x07E0, 0x001F, 0)
        elif mode == "BMP555" :
            # BMP文件头和信息头RGB555
            bmp_file.file_header = struct.pack("<2sIHHI", b'BM', 14 + 40 + width * height * 2, 0, 0, 14 + 40)
            bmp_file.info_header = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 16, 0, width * height * 2, 2834, 2834, 0, 0)
        elif mode == "BMP888" :
            # BMP文件头和信息头RGB888
            bmp_file.file_header = struct.pack("<2sIHHI", b'BM', 14 + 40 + width * height * 3, 0, 0, 14 + 40)
            bmp_file.info_header = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, width * height * 3, 2834, 2834, 0, 0)

        if mode == "BMP565" or mode == "BMP555":
            bmpdata=bytearray()
            pos = 8
            while pos < len(data_in):
                # print(f"{pos}/{len(data_in)}")
                if len(data_in) - pos >= 12:
                    b1, b2, b3, b4 = struct.unpack("4B", data_in[pos : (pos + 4)])
                    pos += 4
                    if b1 == 0x89 and b2 == 0x67 and b3 == 0x45 and b4 == 0x23 :
                        b1, b2, b3, b4 = struct.unpack("4B", data_in[pos : (pos + 4)])
                        pos += 4
                        count = struct.unpack("L", data_in[pos : (pos + 4)])
                        pos += 4
                        for i in range(count[0]):
                            bmpdata.append(b1)
                            bmpdata.append(b2)
                            bmpdata.append(b3)
                            bmpdata.append(b4)
                    else:
                        bmpdata.append(b1)
                        bmpdata.append(b2)
                        bmpdata.append(b3)
                        bmpdata.append(b4)
                else:
                    b1, b2 = struct.unpack("2B", data_in[pos : (pos + 2)])
                    pos += 2
                    bmpdata.append(b1)
                    bmpdata.append(b2)
            if len(bmpdata) < width * height * 2 :
                print("Info: image data size is incorrect")

            bmp_file.pixels = bytearray()
            for i in range(height):
                for j in range(width):
                    pi = (height - i - 1) * width * 2 + j * 2
                    bmp_file.pixels.append(bmpdata[pi])
                    bmp_file.pixels.append(bmpdata[pi+1])

            return bmp_file
        elif mode == "BMP888":
            pass


def main():
    if len(sys.argv) < 2 or "-?" in sys.argv or "/?" in sys.argv:
        show_help()
        sys.exit(0)

    print("Huawei Watchface Unpack")
    print(f"version: {version}")
    print("")
    
    input_file = sys.argv[1]
    input_file = os.path.abspath(input_file) 
    if not os.path.isfile(input_file) :
        print(f"Err: input_file is error -> {input_file}")
        sys.exit(0)

    output_dir = input_file + "_out" if len(sys.argv) < 3 else sys.argv[2]
    output_dir = os.path.abspath(output_dir)

    extractor = watchface_unpack()
    extractor.read(input_file, output_dir)
    sys.exit(0)

def show_help():
    print("Huawei Watchface Unpack")
    print(f"version: {version}")
    print("Unpack images from *.hwt or com.huawei.watchface file")
    print("")
    print("Usage: hw_watchface_unpack.exe <input_file> [output_dir]")
    print(f"\tinput_file  *.hwt or com.huawei.watchface file")
    print(f"\toutput_dir  defaults to <input_file>_out")

if __name__ == "__main__":
    main()
