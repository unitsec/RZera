import redis
from redis.sentinel import Sentinel
import time
import numpy as np

class RedisHelper():
    def __init__(self, ip_port, passwd, timeout):
        self.status = False
        self.redisWrite = None
        self.redisRead = None
        begin = time.time()
        while True:
            if not self.redisWrite:
                sentinel = Sentinel(ip_port, socket_timeout=10)
                try:
                    self.redisRead = sentinel.slave_for('neonmaster', socket_timeout=30, password=passwd)
                    self.redisWrite = sentinel.master_for('neonmaster', socket_timeout=30, password=passwd)
                except redis.exceptions.ConnectionError:
                    print('ERROR: Redis failed')
                if self.redisWrite is not None:
                    if self.redisRead is None:
                        self.redisRead = self.redisWrite
                    self.status = True
                    print('INFO: Redis connected')
                    break
                else:
                    print('ERROR: Redis failed')
                if time.time() - begin > timeout:
                    print('WARNING: Redis timeout')
                    break

    def getStatus(self):
        return self.status

    def getRedisWrite(self):
        return self.redisWrite

    def getRedisRead(self):
        return self.redisRead

    def readNumpyArray(self,path):
        tmp = self.redisRead.get(path)
        return np.array(jsonDecoder(tmp))

    def readStr(self,path):
        tmp = self.redisRead.get(path)
        return tmp

import json
import base64

class numpyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            if obj.flags['C_CONTIGUOUS']:
                obj_data = obj.data
            else:
                cont_obj = np.ascontiguousarray(obj)
                assert(cont_obj.flags['C_CONTIGUOUS'])
                obj_data = cont_obj.data
            data_b64 = base64.b64encode(obj_data)
            return dict(__ndarray__=data_b64,
                        dtype=str(obj.dtype),
                        shape=obj.shape)
        return json.JSONEncoder(self, obj)

def numpyDecoder(obj):
    if isinstance(obj, dict) and '__ndarray__' in obj:
        data = base64.b64decode(obj['__ndarray__'])
        return np.frombuffer(data, obj['dtype']).reshape(obj['shape'])
    return obj

def jsonEncoder(array_data):
    return json.dumps(array_data, cls=numpyEncoder)

def jsonDecoder(json_data):
    _array=None
    try:
        _array=json.loads(json_data, object_hook=numpyDecoder)
        #_array=int(json.loads(json_data, object_hook=numpyDecoder))
    except:
        _array=None

    return _array

# convert list/np.array to json
def array2json(array_data):
    if type(list_data)==list:
        return json.dumps(np.array(list_data))
    elif type(list_data)==np.ndarray:
        return json.dumps(list_data)
    else:
        print ("Error: not proper data type.")
        return None

# convert json to list
def json2array(json_data):
    try:
        return np.array(json.loads(json_data))
    except:
        print ("Error: json string is not in list type.")
        return None

def getRedisHelper_oldThree(conf):
    ip_port = []
    ips = conf["redis_data"]["servers"]
    for i in range(len(ips)):
        ip = ips[i]["host"]
        port = ips[i]["port"]
        ip_port.append((ip,port))
    passwd = conf["redis_data"]["password"]
    rds = RedisHelper(ip_port,passwd,10)
    return rds
    #return rds.getRedisRead
