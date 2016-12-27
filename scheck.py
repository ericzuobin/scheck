#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2016/12/23 下午5:55
# @Author  : Sahinn
# @File    : scheck.py
import os
import socket
import json
import logging
import sys
from logging.handlers import RotatingFileHandler

reload(sys)
sys.setdefaultencoding('utf8')
LOG_FILE = sys.path[0] + os.sep + 'scheck.log'
logger = logging.getLogger(__name__)
server_failed_count = {}


def configure_logging(level):
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5)
    handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(levelname)s'
                                  ' - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def load_config():
    """ 加载配置
    """
    config_path = sys.path[0] + os.sep + 'config.json'
    logger.info('加载配置 %s' % config_path)
    try:
        with open(config_path, 'rt') as config_file:
            return json.loads(config_file.read())
    except IOError:
        logger.error('加载配置 %s 路径不对' % config_path)
        sys.exit(0)
    except Exception, e:
        logger.error('加载配置 %s 出错' % e.message)
        sys.exit(0)


configure_logging(logging.ERROR)
config = load_config()


def check_server(address, port):
    s = socket.socket()
    logger.info('开始连接 %s, %d ' % (address, port))
    try:
        s.connect((address, port))
        logger.info('连接 %s , port %d 成功' % (address, port))
        return True
    except socket.error, e:
        logger.error("连接 %s , port %d 失败: %s" % (address, port, e.message))
    finally:
        s.close()


def notify():
    for key in server_failed_count:
        if key in config['alias']:
            alias = config['alias'][key]
        else:
            alias = key
        if key in config['retry']:
            if server_failed_count[key] >= config['retry'][key]:
                print 'Server', key, ' 已停止服务! 重试次数 ', alias
        else:
            if server_failed_count[key] >= config['retry']['default']:
                print 'Server', key, ' 已停止服务! 重试次数 ', alias


def check_service():
    server = config['server']
    for host in server:
        ports = server[host]
        for port in ports:
            count_key = host + '_' + str(port)
            if check_server(host, port):
                server_failed_count[count_key] = 0
            else:
                if count_key in server_failed_count:
                    server_failed_count[count_key] += 1
                else:
                    server_failed_count[count_key] = 1

if __name__ == '__main__':
    for i in range(4):
        check_service()
    notify()



