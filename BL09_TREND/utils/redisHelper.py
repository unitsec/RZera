from abc import ABC, abstractmethod
import redis
from redis.sentinel import Sentinel
import time
import struct
import numpy as np
import logging
from .logConfig import setup_logging
setup_logging(console=False)

class IOBase(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def read(self, name):
        raise IOError('IOSbase read is not implemented')


    @abstractmethod
    def write(self, name, val):
        raise IOError('IOSbase write is not implemented')


def numpy2bytes(matrix):
    #size
    dim = matrix.ndim
    dimArr = matrix.shape
    header=struct.pack('Q', dim)
    for i in range(dim):
        header += struct.pack('Q', dimArr[i])
    dtypestr=str(matrix.dtype)
    header += struct.pack('Q', len(dtypestr))
    header += bytes (dtypestr, encoding='utf-8')

    encoded = header + matrix.tobytes()
    return encoded

def bytes2numpy(encoded):
    dim= struct.unpack('Q',encoded[:8])[0]
    shapeEndPos = 8 + dim*8
    shape = struct.unpack('Q'*dim, encoded[8:shapeEndPos])
    dtypelen = struct.unpack('Q',encoded[shapeEndPos:(shapeEndPos+8)])[0]
    dtypestr = ''.join(chr(i) for i in encoded[(shapeEndPos+8):(shapeEndPos+8+dtypelen)])

    return np.frombuffer(encoded[(shapeEndPos+8+dtypelen):], dtype=dtypestr).reshape(shape)

class RedisHelper(IOBase):
    logger = logging.getLogger(__name__)
    def __init__(self, ip_port, passwd, timeout, db=0, master_name='mymaster'):
        super().__init__()
        self.sole = False
        self.redisWrite = None
        self.redisRead = None
        self.db = db
        begin = time.time()
        self.logger.info('start connect redis!')
        if type(ip_port) is tuple:
            self.redisRead = redis.Redis(host=ip_port[0], port=ip_port[1], db=self.db, password=passwd, socket_timeout=5, retry_on_timeout=True)
            self.redisWrite=self.redisRead
            self.sole=True
        else:
            while True:
                if not self.redisWrite:
                    sentinel = Sentinel(ip_port, socket_timeout=10)
                    try:
                        self.soleRW = False
                        self.redisRead = sentinel.slave_for(master_name, socket_timeout=30, password=passwd)
                        self.redisWrite = sentinel.master_for(master_name, socket_timeout=30, password=passwd)
                    except (redis.exceptions.ConnectionError):
                        print( 'ERROR: Redis falied')
                    if self.redisWrite is not None:
                        if self.redisRead is None: self.redisRead=self.redisWrite
                        self.soleRW = True
                        break
                    else:
                        print( 'ERROR: Redis falied')
                    if time.time()-begin>timeout:
                        print( 'WARNING: Reids timeout')
                        break

    def soleRW(self):
        return self.soleRW

    def read(self, path):
    	return self.redisRead.get(path)

    def write(self, path, data):
    	return self.redisWrite.set(path, data)

    def writeNumpyArray(self, path, matrix):
        encoded = numpy2bytes(matrix)
        self.write(path,encoded)

    def readNumpyArray(self, path):
        try:
            encoded = self.read(path)
            return bytes2numpy(encoded)
        except:
            self.logger.error(f"can't get data from {path}")
            return np.array([])

    def readStr(self,path):
        try:
            data = self.read(path)
            return str(data.decode())
        except:
            self.logger.error(f"can't get data from {path}")
            return None

    def writeStr(self,path,data):
        encoded = data.encode()
        self.write(path,encoded)

    def intersect_keywords_sets(self, keywords):
        """Calculate the intersection of keyword sets."""
        # 这个方法假设你已经为每个关键词创建了对应的 Redis 集合
        key_sets = [f'{keyword}_set' for keyword in keywords]
        # 使用 SINTER 命令直接计算交集
        intersection_keys = self.redisRead.sinter(*key_sets)
        return list(intersection_keys)

    #getting all the keys matching the pattern.
    def scan_keys(self, pattern='*', count=10):
        if not self.redisRead:
            raise Exception("Read connection is not established")
        cursor = 0
        keys = set()  # 使用集合去重
        while True:
            cursor, partial_keys = self.redisRead.scan(cursor, match=pattern, count=count)
            keys.update(partial_keys)  # 直接更新集合
            if cursor == 0:
                break
        return keys

def getRedisHelper(conf):
    mode = conf['redis_data']['mode'].lower()
    password = conf["redis_data"]['password']
    servers = []
    for item in conf["redis_data"]['servers']:
        servers.append((item['host'], item['port']))
    if mode == 'standalone':
        return RedisHelper(servers[0], password, 10)
    elif mode == 'sentinel':
        return RedisHelper(servers, password, 10, master_name=conf['master_name'])
    else:
        raise Exception(f'Redis mode not supported: {mode}')