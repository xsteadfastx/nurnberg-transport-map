import os
import time
import threading
import geojson
import vagquery
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
            return True, i.trip_id, i.latitude, i.longitude, i.direction, i.product, i.prognosis
        else:
            return False, i.trip_id, i.latitude, i.longitude, i.direction, i.product, i.prognosis


def build_feature():
    '''checks list of stations and emits geojson'''
    if not os.path.exists('station.lst'):
        get_station_list()

    station_list = []
    with open('station.lst') as f:
        for i in f.readlines():
            station_list.append(i.strip())

    for i in station_list:
        try:
            station = is_here(i)
            if station[0]:
                feature = geojson.Feature(geometry=geojson.Point((station[3], station[2])), properties={'id': station[1], 'product': station[5], 'prognosis': station[6], 'popupContent': '&rarr; ' + station[4]})
                #print feature
                socketio.emit('my response', feature, namespace='/map')

        except Exception:
            pass


def emit_thread():
    '''function to put in a thread'''
    while True:
        build_feature()


def remove_markers():
    '''delete markers on interval'''
    while True:
        time.sleep(60)
        socketio.emit('remove markers', 'remove', namespace='/map')


@app.route('/')
def index():
    '''rendering the map'''
    return render_template('index.html')


@socketio.on('connect', namespace='/map')
def map_connect():
    ''' try to send coords on connect'''
    print 'Client connected'


@socketio.on('disconnect', namespace='/map')
def map_disconnect():
    '''what to do on disconnect'''
    print 'Client disconnected'


if __name__ == '__main__':
    threading.Thread(target=emit_thread).start()
    threading.Thread(target=remove_markers).start()
    socketio.run(app)
