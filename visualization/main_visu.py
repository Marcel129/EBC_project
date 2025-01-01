import port_data_pb2 as port
import zmq

subscriber_IPaddress = "localhost"
subscriber_port = "2000"

context = zmq.Context()
socket = context.socket(zmq.SUB)

socket.connect(f"tcp://{subscriber_IPaddress}:{subscriber_port}")
socket.setsockopt(zmq.SUBSCRIBE,b"")

myPort = port.PortState()

while True:
    myPort.ParseFromString(socket.recv())
    name = ""
    for transPoint in myPort.transitPoints:
        if transPoint.ID == port.TransitPoint.Port_ID.AMERICA:
            name = "AMERICA"
        elif transPoint.ID == port.TransitPoint.Port_ID.EUROPA:
            name = "EUROPA"
        elif transPoint.ID == port.TransitPoint.Port_ID.ASIA:
            name = "ASIA"
        elif transPoint.ID == port.TransitPoint.Port_ID.AFRICA:
            name = "AFRICA"

        print(f"Container to {name} with {transPoint.containersNo} containers")