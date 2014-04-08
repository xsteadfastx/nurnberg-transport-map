import os
import time
import threading
import geojson
import vagquery
from random import uniform
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask.ext.socketio import SocketIO, emit


app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = os.urandom(24)
Bootstrap(app)
socketio = SocketIO(app)


def get_station_list():
    '''getting station list by bruteforce'''
    with open('station.lst', 'w') as f:
        for i in range(100, 1000):
            try:
                if vagquery.DepartureQuery(i).query():
                    f.write(str(i) + '\n')
            except Exception:
                pass


def is_here(station):
    '''check if there is some departing in 0 minutes'''
    departures = vagquery.DepartureQuery(station).query()

    for i in departures:
        if i.departure_in_min == 0:
            return True, i.trip_id, i.latitude, i.longitude, i.direction
        else:
            return False, i.trip_id, i.latitude, i.longitude, i.direction


def create_geojson():
    '''getting everything together and returns a geojson'''
    if not os.path.exists('station.lst'):
        get_station_list()

    station_list = []
    with open('station.lst') as f:
        for i in f.readlines():
            station_list.append(i.strip())

    here_list = []
    for i in station_list:
        station = is_here(i)
        if station[0] == True:
            here_list.append(geojson.Feature(geometry=geojson.Point((station[3], station[2])), properties={'id': station[1], 'popupContent': '&rarr; ' + station[4]}))

    return geojson.FeatureCollection(here_list)


def emit_coords():
    '''check every 60 seconds'''
    global coords
    while True:
        time.sleep(60)
        coords = create_geojson()
        print coords
        socketio.emit('my response', coords, namespace='/map')


def heartbeat():
    '''send every 10 seconds a message'''
    while True:
        time.sleep(10)
        socketio.emit('heartbeat', 'heartbeat', namespace='/map')


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect', namespace='/map')
def map_connect():
    print 'Client connected'
    socketio.emit('my response', coords, namespace='/map')


@socketio.on('disconnect', namespace='/map')
def map_disconnect():
    print 'Client disconnected'


if __name__ == '__main__':
    threading.Thread(target=emit_coords).start()
    threading.Thread(target=heartbeat).start()
    socketio.run(app)
