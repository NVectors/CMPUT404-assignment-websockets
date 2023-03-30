#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

'''Abram Hindle, Accessed March 28, https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py '''
clients = list()

def send_all(msg):
    for client in clients:
        client.put( msg )

def send_all_json(obj):
    send_all( json.dumps(obj) )

class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()
''''''

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

myWorld = World()

def set_listener( entity, data ):
    ''' do something with the update ! '''

myWorld.add_set_listener( set_listener )

@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    '''Redirect: https://pythonbasics.org/flask-redirect-and-errors/'''
    return flask.redirect("/static/index.html")

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    '''Abram Hindle, Accessed March 28, https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py'''
    try:
        while True:
            msg = ws.receive()
            print("WS RECV: %s" % msg)
            if (msg is not None):
                packet = json.loads(msg)
                send_all_json( packet )
            else:
                break
    except:
        '''Done'''

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    '''Abram Hindle, Accessed March 28, https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py'''
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )
    try:
        while True:
            # block here
            msg = client.get()
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print("WS Error %s" % e)
    finally:
        clients.remove(client)
        gevent.kill(g)


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

'''Below is Assignment 4 code reused, https://github.com/NVectors/CMPUT404-assignment-ajax/blob/master/server.py'''

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    "Try to update or set the entity otherwise it is a 500 error"
    try:
        # Get the raw body/data of a post
        raw_data = flask_post_json()

        if (request.method == 'POST'):
            myWorld.set(entity, raw_data)
        elif (request.method == 'PUT'):
            for key,value in raw_data.items():
                myWorld.update(entity, key, value)

        # Serializes data to JSON and wraps it in a Response object
        # https://www.geeksforgeeks.org/use-jsonify-instead-of-json-dumps-in-flask/
        return flask.jsonify(myWorld.get(entity))
    except Exception as e:
        return flask.Response(status=500, response=json.dumps({'Error': str(e)}))


@app.route("/world", methods=['POST','GET'])
def world():
    '''you should probably return the world here'''
    return flask.jsonify(myWorld.world())

@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
     # Try to return the representation of the entity otherwise it is a 500 error
    try:
        rep_entity = myWorld.get(entity)
        return flask.jsonify(rep_entity)
    except Exception as e:
        return flask.Response(status=500, response=json.dumps({'Error': str(e)}))



@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    # Try to clear the world otherwise it is a 500 error
    try:
        if (request.method == 'POST'):
            myWorld.clear()
            return flask.jsonify(myWorld.world())
        elif (request.method == 'GET'):
            return flask.jsonify(myWorld.world())
    except Exception as e:
        return flask.Response(status=500, response=json.dumps({'Error': str(e)}))



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
