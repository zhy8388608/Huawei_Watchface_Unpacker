# pthon3
"""Contains routines for printing protocol messages in xml format.
   Based off of google.protobuf.text_format"""

from xml.dom.minidom import Document, parseString

from google.protobuf import descriptor
from google.protobuf.text_encoding import CEscape

__all__ = [ 'MessageToXML', 'MessageToDOM', 
            'CreateXmlMessage', 'CreateXmlField', 'CreateXmlFieldValue']

# 根据 Theme Studio 11.0.18.300 官方安装目录下提取的 watchface-template\template_watch2.proto 修改后，编写脚本【bp转xml】



# 颜色属性RGBA，Color类型的属性，需要将整数数字转为十六进制，V11的顺序是ARGB，例如：#FF00FF80；V10的顺序是RGBA
ColorAttribute = ["area_color","color","color_value","height_range_color","low_range_color","pillar_color","polyline_color","text_color"]

# 重复属性值，同一个属性有多个值，可以将值进行合并，使用逗号分隔
# 需要修改成对应res文件夹下的图片文件名，例如 002 替换成 A100_002.bmp
ResAttribute = ["res_name","res_default","res_sign","res_primary","res_secondary"]

# 对于有些特殊的Message类型的数据，他的子节点直接就是value，不用创建他们的子节点
XmlAttributeMS = [
    "center_point","center_point_relative","center_position_relative","point","res_position","res_position_relative","rotate_center_point","rotate_center_point_relative","rotate_point_hand",    #Point
    "rect","rect_relative","res_rect","res_rect_relative","rotate_rect","rotate_rect_relative","text_rect","text_rect_relative",    #Rect
    "area_color","color","color_value","height_range_color","low_range_color","pillar_color","polyline_color","text_color",    #Color
]

# V11 转 V10
# element -> container -> layer || element -> layer
hwhd07_layer_label = {"single_res":"单图","selected_res":"选图","combined_res":"组合图","text":"文本","text2_res":"连接文本","line_res":"直线图","arc_res":"弧形图","hand_res":"指针"}
# layer的属性名称不一致，需要对应替换，无条件替换
hwhd07_layer_attr = {"value_type_one":"value1_type", "value_type_two":"value2_type", "connect_type":"text_con_type", "text_color":"text_active_color"}
# Theme Studio 11.0.18.300 中 data_type 对应关系
hwhd07_container_datatypelabel = { 
    "0":"月份", "1":"日期", "2":"星期", "3":"上午下午", "4":"小时", "5":"分钟", "6":"秒", "7":"未知", "8":"双时区", "9":"日出日落时间", "10":"步数", 
    "11":"心率", "12":"卡路里", "13":"中高强度时间", "14":"最大摄氧量", "15":"站立次数", "16":"压力", "17":"电量", "18":"未读信息数量", "19":"背景", "20":"空气质量", 
    "21":"天气", "22":"未知", "23":"未知", "24":"距离", "25":"睡眠", "26":"锻炼", "27":"支付宝", "28":"闹钟", "29":"秒表", "30":"计时器", 
    "31":"锻炼记录", "32":"训练状态", "33":"活动记录", "34":"呼吸训练", "35":"联系人", "36":"音乐", "37":"指南针", "38":"通话记录", "39":"未知", "40":"血氧饱和度", 
    "41":"农历", 
    "255":"无数据" }


# 存放 res 文件夹下的图片名称的list
imgs_filename_list = None

def MessageToXml(message, imgs_filename, *vargs, **kwargs):
    """ Builds an xml string from the message"""
    document11, document10 = MessageToDOM(message, imgs_filename)
    return (document11.toxml(*vargs,**kwargs), document10.toxml(*vargs,**kwargs))

def MessageToDOM(message, imgs_filename):
    """ Builds a DOM object from the message"""
    doc = Document()
    # document_root = doc.createElement(message.DESCRIPTOR.name)
    document_root = doc.createElement("watchface")
    doc.appendChild(document_root)
    global imgs_filename_list
    imgs_filename_list = imgs_filename.copy()
    # print(imgs_filename_list)

    CreateXmlMessage(message, doc, document_root)
    olddoc = parseString(doc.toxml())
    olddoc = Convert2oldver(olddoc)
    return (doc, olddoc)    # doc -> xml v11.x ----- olddoc -> xml v10.x

def CreateXmlMessage(message, doc, element):
    global imgs_filename_list
    for field, value in message.ListFields():
        if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:    #处理重复的名称的节点或者属性
            # res图片资源名称，需要配合bin解析以后获取到的文件名进行对应替换
            if field.name[:8] == "res_name" or field.name in ResAttribute :
                # print(f"{field.name} # {value}")
                newvalue = []
                for vi in value:
                    for i in range(len(imgs_filename_list)):
                        if vi == str(i+1).rjust(3,'0'):
                            newvalue.append(imgs_filename_list[i])
                            
                if len(newvalue) > 0 :
                    element.setAttribute(field.name, ','.join(newvalue))
                else:
                    element.setAttribute(field.name, ','.join(value))
            else:
                for sub_element in value:
                    CreateXmlField(field, sub_element, doc, element)
        else:
            CreateXmlFieldValue(field, value, doc, element)
    return

def CreateXmlField(field, value, doc, element):
    """Print a single field name/value pair.  For repeated fields, the value
    should be a single element."""
    if field.is_extension:
        if (field.containing_type.GetOptions().message_set_wire_format and
            field.type == descriptor.FieldDescriptor.TYPE_MESSAGE and
            field.message_type == field.extension_scope and
            field.label == descriptor.FieldDescriptor.LABEL_OPTIONAL):
            
            # print(field.name)
            field_element = doc.createElement(field.message_type.full_name)
            CreateXmlFieldValue(field, value, doc, field_element)
            element.appendChild(field_element)   
        else:
            # print(field.name)
            field_element = doc.createElement(field.full_name)
            CreateXmlFieldValue(field, value, doc, field_element)
            element.appendChild(field_element)   
    elif field.type == descriptor.FieldDescriptor.TYPE_GROUP:
        # For groups, use the capitalized name.
        field_element = doc.createElement(field.message_type.full_name)
        CreateXmlFieldValue(field, value, doc, field_element)
        # print(field.name)
        element.appendChild(field_element)   
    else:
        field_element = doc.createElement(field.name)
        CreateXmlFieldValue(field, value, doc, field_element)
        # print(field.name)
        element.appendChild(field_element)
        
    return

def CreateXmlFieldValue(field, value, doc, element):
    if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
        if field.name in XmlAttributeMS:  #有些Message类型的，并不会把他的内容转成节点，而是把他内容整体转换成一个value值，例如：Point、Rect、Color
            field_element = doc.createElement(field.name)
            CreateXmlAttributeMS(field, value, doc, element)
        else:
            CreateXmlMessage(value, doc, element)
    else:
        CreateXmlAttribute(field, value, doc, element)
    return

# 非Message类型的数据，代表着没有子节点了，所以直接赋值为当前节点的属性
def CreateXmlAttribute(field, value, doc, element):
    global imgs_filename_list
    if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
        CreateXmlFieldValue(field, value, doc, element)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM:
        field_value = str(field.enum_type.values_by_number[value].name)
        if field.name == "draw_type":
            field_value = field_value.lower()[10:]
        if field.name == "label":
            field_value = field_value.lower()[14:]
        if field.name == "align_type" or field.name == "text_align" or field.name == "res_align":
            field_value = field_value.lower()
        element.setAttribute(field.name, field_value)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_STRING:
        if field.name[:8] == "res_name" or field.name in ResAttribute :
            newvalue = ""
            for i in range(len(imgs_filename_list)):
                if value == str(i+1).rjust(3,'0'):
                    newvalue = imgs_filename_list[i]
                    
            if newvalue != "" :
                element.setAttribute(field.name, newvalue)
            else:
                element.setAttribute(field.name, value)
        else:
            element.setAttribute(field.name, value)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_BOOL:
        # lower cased boolean names, to match string output
        if value:
            element.setAttribute(field.name, "true")
        else:
            element.setAttribute(field.name, "false")
    else:
        element.setAttribute(field.name, str(value))
    return

# 对于有些特殊的Message类型的数据，他的子节点直接就是value，不用创建他们的子节点
def CreateXmlAttributeMS(prefield, message, doc, element):
    if prefield.name in ColorAttribute :    # V11的顺序是ARGB，例如：#FF00FF80
        # print(f"{prefield.full_name} #")
        newvalue = ""
        for field, value in message.ListFields():
            newvalue += hex(value)[2:].upper()
        if len(newvalue) >= 8:
            newvalue = "#" + newvalue[6:8] + newvalue[0:6]
        element.setAttribute(prefield.name, newvalue)
        return

    prevalue = list()
    for field, value in message.ListFields():
        if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM:
            field_value = str(field.enum_type.values_by_number[value].name)
            prevalue.append(field_value)
        elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_STRING:
            prevalue.append(value)
        elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_BOOL:
            if value:
                prevalue.append("true")
            else:
                prevalue.append("false")
        else:
            prevalue.append(str(value))
    element.setAttribute(prefield.name, ",".join(prevalue))
    return

# 转换成 HwWatchFaceDesigner V10 的版本的xml文件
def Convert2oldver(doc):
    root = doc.documentElement    #HwTheme
    
    for child1 in root.childNodes :
        if child1.nodeName == 'element':
            for child2 in child1.childNodes :
                if child2.nodeName == 'container':
                    Convert2oldver_container(child2)
                    for child3 in child2.childNodes :
                        if child3.nodeName == 'layer':
                            Convert2oldver_layer(child3)
                            
                elif child2.nodeName == 'layer':
                    Convert2oldver_layer(child2)
    
    return doc

# 转换V10过程中，对 layer 节点进行一定的处理
def Convert2oldver_layer(layernd):
    for color in ColorAttribute :    # #ARGB -> #RGBA
        if layernd.hasAttribute(color) and len(layernd.getAttribute(color)) >= 9:
            value = layernd.getAttribute(color)
            newvalue = "#" + value[3:9] + value[1:3]
            # print(f"{value}->{newvalue}")
            layernd.setAttribute(color, newvalue)

    if layernd.hasAttribute("draw_type"):
        if layernd.getAttribute("draw_type") in hwhd07_layer_label:
            layernd.setAttribute("label", hwhd07_layer_label[layernd.getAttribute("draw_type")])

    if layernd.hasAttribute("align_type"):
        layernd.setAttribute("align_type", layernd.getAttribute("align_type").upper())
    if layernd.hasAttribute("text_align"):
        layernd.setAttribute("text_align", layernd.getAttribute("text_align").upper())
    # if layernd.hasAttribute("res_align"):
        # layernd.setAttribute("res_align", layernd.getAttribute("res_align").upper())

    for attr in hwhd07_layer_attr:
        if layernd.hasAttribute(attr):
            layernd.setAttribute(hwhd07_layer_attr[attr], layernd.getAttribute(attr))
            layernd.removeAttribute(attr)

    # 属性值的有条件替换
    if layernd.getAttribute("draw_type") == "single_res" and layernd.hasAttribute("res_name"):
        layernd.setAttribute("res_active", layernd.getAttribute("res_name"))
        layernd.removeAttribute("res_name")
    
    if layernd.getAttribute("draw_type") == "combined_res":
        if not layernd.hasAttribute("x_offset"):
            layernd.setAttribute("x_offset", "0")
        if not layernd.hasAttribute("y_offset"):
            layernd.setAttribute("y_offset", "0")
    

# 转换V10过程中，对 container 节点进行一定的处理
def Convert2oldver_container(containernd):
    if containernd.hasAttribute("rect"):
        containernd.removeAttribute("rect")
    
    if containernd.hasAttribute("data_type") and containernd.getAttribute("data_type") in hwhd07_container_datatypelabel:
        containernd.setAttribute("label", hwhd07_container_datatypelabel[containernd.getAttribute("data_type")])
    
    
