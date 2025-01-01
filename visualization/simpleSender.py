import port_data_pb2 as port
import zmq
import time

publisher_IPaddress = "localhost"
publisher_port = "2000"

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind(f"tcp://{publisher_IPaddress}:{publisher_port}")

myPort = port.PortState()

tp_Africa = port.TransitPoint.Port_ID.AFRICA
tp_Europa = port.TransitPoint.Port_ID.EUROPA
tp_Asia = port.TransitPoint.Port_ID.ASIA
tp_America = port.TransitPoint.Port_ID.AMERICA

lp_ship1 = port.LoadingPoint.LoadingPoint_ID.SHIP_1,
lp_ship2 = port.LoadingPoint.LoadingPoint_ID.SHIP_2,
lp_ship3 = port.LoadingPoint.LoadingPoint_ID.SHIP_3,
lp_stgYard1 = port.LoadingPoint.LoadingPoint_ID.STORAGE_YARD_1,
lp_stgYard2 = port.LoadingPoint.LoadingPoint_ID.STORAGE_YARD_2,
lp_tpAfrica = port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_AFRICA,
lp_tpEuropa = port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_EUROPA,
lp_tpAsia = port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_ASIA,
lp_tpAmerica = port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_AMERICA

def port_Init():
    myPort.ship.isInPort = False
    myPort.ship.isEmpty = True
    myPort.ship.remainingContainersNo = 0

    myPort.storageYard.containersNo = 0
    myPort.storageYard.isEmpty = True

    transitPointsIDs = [
        port.TransitPoint.Port_ID.AFRICA,
        port.TransitPoint.Port_ID.EUROPA,
        port.TransitPoint.Port_ID.ASIA,
        port.TransitPoint.Port_ID.AMERICA
    ]

    loadingPointsIDs = [
        port.LoadingPoint.LoadingPoint_ID.SHIP_1,
        port.LoadingPoint.LoadingPoint_ID.SHIP_2,
        port.LoadingPoint.LoadingPoint_ID.SHIP_3,
        port.LoadingPoint.LoadingPoint_ID.STORAGE_YARD_1,
        port.LoadingPoint.LoadingPoint_ID.STORAGE_YARD_2,
        port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_AFRICA,
        port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_EUROPA,
        port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_ASIA,
        port.LoadingPoint.LoadingPoint_ID.TRANSIT_POINT_AMERICA
    ]

    for id in transitPointsIDs:
        new_point = myPort.transitPoints.add()
        new_point.ID = id
        new_point.containersNo = 0
        new_point.isEmpty = True

    myPort.transitPoints[port.TransitPoint.Port_ID.AFRICA].containersNo = 20

    for id in loadingPointsIDs:
        new_point = myPort.loadingPoints.add()
        new_point.ID = id
        new_point.busy = False


port_Init()

while True:
    socket.send(myPort.SerializeToString())
    time.sleep(1)