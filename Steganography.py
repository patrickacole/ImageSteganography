#! /usr/bin/env python3.4
import numpy as np
import scipy
import PIL
import imageio
import zlib
import base64

class Payload:

    def __init__(self, rawData=None, compressionLevel=-1, json=None):
        if (rawData is None and json is None):
            raise ValueError('Either rawData or json must be given as input values')
        if (compressionLevel < -1 or compressionLevel > 9):
            raise ValueError('compressionLevel is out of the acceptable range: [-1,9]')
        if (self.verifyRawData(rawData)):
            raise TypeError('rawData must be a numpy array of type uint8')
        if (self.verifyJson(json)):
            raise TypeError('json must be of type str')
        if (json is None):
            self.rawData = np.array(rawData)
            data = self.convertedData()
            compressedData = self.compressData(compressionLevel, data)
            baseStr = self.getBaseStr(compressedData)
            self.json = self.formatJson(baseStr, compressionLevel)
        else:
            self.json = json
            jsonInfo = self.extractJson()
            decodeData = self.decodeData(jsonInfo[3])
            decompressed = self.decompressData(jsonInfo[2], decodeData)
            actualData = self.restoreData(decompressed, jsonInfo[0], jsonInfo[1])
            self.rawData = actualData

    def restoreData(self, data, dataType, dataSize):
        if (dataType == 'text'):
            return data
        height = int(dataSize.split(',')[0])
        width = int(dataSize.split(',')[1])
        if (dataType == 'gray'):
            return data.reshape((height,width))
        else:
            return data.reshape((height,width,3), order='A')

    def decompressData(self, compressed, decodeData):
        if (compressed == 'true'):
            data = zlib.decompress(decodeData)
        else:
            data = decodeData
        return np.fromstring(data, dtype='uint8')

    def decodeData(self, dataStr):
        dataBytes = bytes(dataStr, 'utf-8')
        newBytes = base64.b64decode(dataBytes)
        return newBytes

    def extractJson(self):
        splt = self.json.split("\"")
        dataType = splt[3]
        if (splt[6] == ':'):
            dataSize = splt[7]
        else:
            dataSize = 'null'
        if (dataSize == 'null'):
            dataCmpr = splt[8]
        else:
            dataCmpr = splt[10]
        if (dataCmpr.count('true')):
            dataCmpr = 'true'
        else:
            dataCmpr = 'false'
        if (dataSize == 'null'):
            dataCnt = splt[11]
        else:
            dataCnt = splt[13]
        return (dataType, dataSize, dataCmpr, dataCnt)

    def convertedData(self):
        if (self.rawData.ndim == 1):
            return self.rawData
        elif (self.rawData.ndim == 2):
            return self.rawData.flatten()
        else:
            return self.rawData.flatten('A')

    def formatJson(self, baseStr, compressionLevel):
        json = "{"
        if (self.rawData.ndim == 1):
            json += "\"type\":\"text\",\"size\":null,"
        elif (self.rawData.ndim == 2):
            height,width = self.rawData.shape
            json += "\"type\":\"gray\",\"size\":\"{0},{1}\",".format(height,width)
        elif (self.rawData.ndim == 3):
            height,width,depth = self.rawData.shape
            json += "\"type\":\"color\",\"size\":\"{0},{1}\",".format(height,width)
        if (compressionLevel == -1):
            json += "\"isCompressed\":false,"
        else:
            json += "\"isCompressed\":true,"

        json += "\"content\":\""
        json += baseStr
        json += "\"}"
        return json

    def getBaseStr(self, compressData):
        baseBytes = base64.b64encode(compressData)
        baseStr = baseBytes.decode('utf-8')
        return baseStr

    def compressData(self, compressionLevel, data):
        if (compressionLevel == -1):
            return self.rawData.tobytes()
        compressedData = zlib.compress(data, compressionLevel)
        return compressedData

    def verifyRawData(self, rawData):
        if (rawData is None):
            return False
        if (not isinstance(rawData, np.ndarray)):
            return True
        if (rawData.ndim == 1 and type(rawData[0]) != np.uint8):
            return True
        elif (rawData.ndim == 2 and type(rawData[0][0]) != np.uint8):
            return True
        elif (rawData.ndim == 3 and type(rawData[0][0][0]) != np.uint8):
            return True
        elif (rawData.ndim == 3 and rawData.shape[2] == 4):  # Added
            return True
        elif (rawData.ndim < 1 or rawData.ndim > 3):
            return True
        return False

    def verifyJson(self, json):
        if (json is None):
            return False
        if (type(json) != str or json.count("\n") != 0 or json.count(" ") != 0):
            return True
        return False

class Carrier:

    def __init__(self, img):
        if (not isinstance(img, np.ndarray) or ((img.ndim == 3) and type(img[0][0][0]) is not np.uint8)):
            raise TypeError('Must be of typ np.ndarray and consist of uint8 elements')
        if (img.ndim < 3 or img.shape[2] < 4):
            raise ValueError('Image dimension must be 3 with 4 channels')
        self.img = np.array(img)

    def payloadExists(self):
        byteList = []
        for w in range(7):
            currByte = 0x00
            for d in reversed(range(4)):
                currByte = currByte << 2
                value = self.img[0][w][d]
                if (value&2):
                    currByte = currByte|2
                if (value&1):
                    currByte = currByte|1
            byteList.append(currByte)
        arr = np.array(byteList, dtype=np.uint8)
        try:
            check = arr.tobytes().decode('utf-8')
        except:
            check = False
        if (check == '{"type"'):
            return True
        return False

    def clean(self):
        #if (not self.payloadExists()):
        #    return self.img
        height,width,depth = self.img.shape
        randArr = np.random.randint(0, 4, size=(height,width,depth),dtype=np.uint8)
        cleanImg = np.bitwise_xor(self.img, randArr)
        return cleanImg

    def embedPayload(self, payload, override=False):
        if (type(payload) is not Payload or type(override) is not bool):
            raise TypeError('Input parameter payload must be of type Payload and override must be of type bool')
        jsonArr = np.fromstring(payload.json, dtype=np.uint8)
        height,width,depth = self.img.shape
        if (jsonArr.shape[0] > (width * height)):
            raise ValueError('Payload is too large to embed')
        if (self.payloadExists() and not override):
            raise Exception('Current carrier already has a payload, and override flag was not given')
        mask1 = 0b11111100
        mask2 = 0b00000011
        valid = np.ones(jsonArr.shape[0]*4, dtype=np.bool)
        valid.resize(height,width,4)
        rptArr = np.repeat(jsonArr, 4)
        sftArr = np.right_shift(rptArr, np.tile(np.array([0,2,4,6], dtype=np.uint8), jsonArr.shape[0]))
        arr = np.bitwise_and(sftArr, mask2)
        arr.resize(height,width,4)
        tmpCarrier = np.bitwise_or(self.img, 0b00000000, dtype=np.uint8)
        tmpCarrier = np.bitwise_and(self.img, mask1, out=tmpCarrier, where=valid, dtype=np.uint8)
        embed = np.bitwise_or(tmpCarrier, arr, out=tmpCarrier, dtype=np.uint8)
        return embed

    def extractPayload(self):
        mask = 0b00000011
        value = np.bitwise_and(self.img, mask, dtype=np.uint8)
        part1 = np.delete(value, [1,2,3], axis=2)
        part2 = np.delete(value, [0,2,3], axis=2)
        part3 = np.delete(value, [0,1,3], axis=2)
        part4 = np.delete(value, [0,1,2], axis=2)
        part2 = np.left_shift(part2, 2)
        part3 = np.left_shift(part3, 4)
        part4 = np.left_shift(part4, 6)
        payload = np.bitwise_or(part1, part2, dtype=np.uint8)
        payload = np.bitwise_or(payload, part3, dtype=np.uint8)
        payload = np.bitwise_or(payload, part4, dtype=np.uint8)
        payload = payload.flatten('A')
        index = np.where(payload == 125)
        for i in np.nditer(index):
            if (payload[i-1] == 34):
                payload = payload[0:(i+1)]
                break
        json = payload.tobytes().decode('utf-8')
        pay = Payload(json=json)
        return pay

if __name__ == "__main__":
    '''
    # test json for payload 3
    with open('data/payload3.txt', 'r') as rfile:
        line = rfile.read()
    arr = np.fromstring(line, dtype=np.uint8)
    pay = Payload(arr, 5)
    with open('test3.json', 'w') as wfile:
        wfile.write(pay.json)
    '''
    '''
    # test json for payload 2
    img = imageio.imread('data/payload2.png')
    #img = np.array(img)
    pay = Payload(img, 7)
    with open('test2.json', 'w') as wfile:
        wfile.write(pay.json)
    '''
    '''
    # test json for payload 1
    img = imageio.imread('data/payload1.png')
    img = np.array(img)
    pay = Payload(img)
    with open('test1.json', 'w') as wfile:
        wfile.write(pay.json)
    '''
    '''
    # test payload for json 3
    with open('data/payload3.json', 'r') as rfile:
        line = rfile.read()
    pay1 = Payload(json=line)
    if (np.array_equal(pay1.rawData, pay.rawData)):
        print('correct')
    '''
    '''
    # test payload for json 2
    with open('data/payload2.json', 'r') as rfile:
        line = rfile.read()
    pay1 = Payload(json=line)
    if (np.array_equal(pay1.rawData, pay.rawData)):
        print('correct')
    #'''
    '''
    # test payload for json 1
    with open('data/payload1.json', 'r') as rfile:
        line = rfile.read()
    pay1 = Payload(json=line)
    if (np.array_equal(pay1.rawData, pay.rawData)):
        print('correct')
    '''
    '''
    # test
    img = imageio.imread('data/carrier.png')
    c = Carrier(img)
    newImg = c.embedPayload(pay)
    #img = PIL.Image.fromarray(newImg, 'RGBA')
    #img.show()
    img = imageio.imread('data/embedded2_7.png')
    if (np.array_equal(newImg,img)):
        print('correct')
    else:
        print('incorrect')
    height,width,depth = img.shape
    '''
    #print(c.payloadExists())
    #newImg = c.clean()
    #n = Carrier(newImg)
    #print(c.payloadExists())
    #print(n.payloadExists())
    '''
    img = imageio.imread('data/embedded2_7.png')
    c = Carrier(img)
    n = c.extractPayload()
    if (n.json == pay.json):
        print('True')
    '''
