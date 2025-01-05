import port_data_pb2 as port
import zmq
import time
import random as rnd
import config as cfg

publisher_IPaddress = "localhost"
publisher_port = "2000"

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind(f"tcp://{publisher_IPaddress}:{publisher_port}")

myPort = port.PortState()

transitPointsIDs = [
    port.TransitPoint.Port_ID.AFRICA,
    port.TransitPoint.Port_ID.EUROPA,
    port.TransitPoint.Port_ID.ASIA,
    port.TransitPoint.Port_ID.AMERICA
]

def createRandomFrame():
    mp = port.PortState()

    mp.ship.isInPort = rnd.random() > 0.5
    mp.ship.remainingContainersNo = int(rnd.random()*cfg.containers_capacities[5])

    mp.storageYard.containersNo = int(rnd.random()*cfg.containers_capacities[4])

    i = 0
    for id in transitPointsIDs:
        new_point = mp.transitPoints.add()
        new_point.ID = id
        new_point.containersNo = int(rnd.random()*cfg.containers_capacities[i])
        i += 1

    for i in range(cfg.numberOfCarts):
        new_cart = mp.carts.add()
        new_cart.withContainer = rnd.random() > 0.5
        new_cart.cartPos = int(rnd.random()*15)

    return mp


while True:
    mp = createRandomFrame()
    socket.send(mp.SerializeToString())
    time.sleep(2)