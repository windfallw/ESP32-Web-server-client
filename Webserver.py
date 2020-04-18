import socket
import os
import gc

Icon200 = '''
HTTP/1.0 200 OK
accept-ranges: bytes
content-type: image/x-icon
Access-Control-Allow-Origin: *
Server: ESP32-Webserver

'''

OK200 = '''
HTTP/1.0 200 OK
Content-Type: {0};charset=utf-8
Access-Control-Allow-Origin: *
Server: ESP32-Webserver

'''

NotFound404 = '''
HTTP/1.0 404 NOT FOUND
Content-Type: text/html;charset=utf-8
Access-Control-Allow-Origin: *
Server: ESP32-Webserver

<title>404 Not Found</title>
<h1>404 NOT FOUND   ):</h1><hr>
<a href="https://github.com/windfallw" style="text-decoration:none;">
Welcome to->MY GITHUB</a>
'''

MethodNotAllowed405 = '''
HTTP/1.0 405 Method Not Allowed
Content-Type: text/html;charset=utf-8
Access-Control-Allow-Origin: *
Server: ESP32-Webserver

'''

dType = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'json': 'application/json',
    'icon': 'image/x-icon'
}


def header200(type='html'):
    "传入响应头的文件类型"
    for i in dType.keys():
        if type == i:
            return OK200.format(dType[type])
    return OK200.format(dType['html'])


class WebServant:
    route_table_get = []
    route_table_post = []

    def __init__(self):
        "init初始化时会自动添加src目录下的js和css文件在get路由表中"
        os.chdir('src')
        file = os.listdir()
        for i in file:
            type = i.rsplit('.')[-1]
            path = '/src/' + i

            def static_file(*function):
                client, address = function
                client.send(header200(type))
                with open(path, 'rb') as f:
                    line = f.read(8192)
                    while line:
                        client.send(line)
                        line = f.read(8192)
                    f.close()

            self.route_table_get.append([path, static_file])
        os.chdir('/')

    def route(self, path, method='GET'):
        "装饰器,方法可选择get或者post,默认为get"

        def decorator(func):
            if method.upper() == 'GET':
                self.route_table_get.append([path, func])
            elif method.upper() == 'POST':
                self.route_table_post.append([path, func])
            else:
                raise Exception("unsupported method!", method)
            return func

        return decorator

    def run(self, host='0.0.0.0', port=80):
        "host和port默认为本机ip的80端口"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(1)
        print("listen on 80.")
        while True:
            try:
                client, address = sock.accept()
                request_head, request_data = client.recv(1024).decode().split('\r\n', 1)  # 处理http请求头分割成请求部分和数据部分
                request_method, request_url, request_version = request_head.split(' ', 2)  # 将请求方法 请求路径 http版本分割出来
                client_data = request_data.rsplit('\r\n', 1)[-1]  # 用户发送的数据
                print(request_url, request_method, address, client)
                flag = False

                if request_method.upper() == 'GET':
                    for i in self.route_table_get:
                        path, func = i
                        if path == request_url:
                            func(client, address)
                            flag = True
                            break
                    if not flag:
                        client.send(NotFound404)
                elif request_method.upper() == 'POST':
                    for i in self.route_table_post:
                        path, func = i
                        if path == request_url:
                            func(client, address, client_data)
                            flag = True
                            break
                    if not flag:
                        client.send(NotFound404)
                else:
                    client.send(MethodNotAllowed405)

            except Exception as e:
                print('WebServant:', e)

            finally:
                client.close()
                gc.collect()
                print('use:', gc.mem_alloc(), 'remain:', gc.mem_free())