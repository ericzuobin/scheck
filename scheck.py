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
import urllib2
from logging.handlers import RotatingFileHandler
import daemonocle
import time

reload(sys)
sys.setdefaultencoding('utf8')
LOG_FILE = sys.path[0] + os.sep + 'scheck.log'
logger = logging.getLogger(__name__)
server_failed_count = {}
cached_notify = {}


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


def send_mail(msg):
    try:
        url = config['mail']['url']
        # 定义要提交的数据
        data = dict(to='admin@zuobin.net', subject='监控报警' + time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()), content=msg)
        print json.dumps(data)
        req = urllib2.Request(url, json.dumps(data))
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        urllib2.urlopen(req).read()
    except Exception, e:
        logger.error("发送邮件错误, %s" % e.message)


def notify():
    for key in server_failed_count:
        if key in config['alias']:
            alias = config['alias'][key]
        else:
            alias = key
        if key in config['retry']:
            if server_failed_count[key] >= config['retry'][key]:
                waring(alias, key)
        else:
            if server_failed_count[key] >= config['retry']['default']:
                waring(alias, key)


def waring(server_name, key):
    if key in cached_notify:
        if time.time() - cached_notify[key] > 600:
            cached_notify[key] = time.time()
            send_mail('Server %s 已停止服务! 已重试%d 次失败! ' % (server_name, server_failed_count[key]))
    else:
        cached_notify[key] = time.time()
        send_mail('Server %s 已停止服务! 已重试%d 次失败! ' % (server_name, server_failed_count[key]))


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


def shutdown_callback(message, code):
    logger.error('监控服务停止')
    logger.debug(message)


def main():
    logger.error('开始监控服务')
    while True:
        check_service()
        notify()
        time.sleep(10)


if __name__ == '__main__':
    daemon = daemonocle.Daemon(
        worker=main,
        pidfile=sys.path[0] + os.sep + 'scheck.pid',
        shutdown_callback=shutdown_callback,
    )
    daemon.do_action(sys.argv[1])


