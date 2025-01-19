import config as cfg
import dearpygui.dearpygui as dpg
import port_data_pb2 as port
import zmq

dpg.create_context()
# default main img size - W:2048, H:1080
WINDOW_WIDTH = 2000
WINDOW_HEIGTH = int(WINDOW_WIDTH / 2)


class Port:
    def __init__(self):

        self.subscriber_IPaddress = "localhost"
        self.subscriber_port = "2000"

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        self.socket.connect(f"tcp://{self.subscriber_IPaddress}:{self.subscriber_port}")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"port_state")

        self.portData = port.PortState()

        self.imagesFolder = "images/"

        self.isMoved = True
        self.images = {}
        self.imagesNames = ["port.png", "ship.png", "cart.png", "cartWithContainer.png"]

    def loadImages(self):
        for imgName in self.imagesNames:
            self.images[imgName] = dpg.load_image(self.imagesFolder + imgName)

            with dpg.texture_registry(show=True):
                dpg.add_dynamic_texture(
                    width=self.images[imgName][0],
                    height=self.images[imgName][1],
                    default_value=self.images[imgName][3],
                    tag=imgName,
                )

    def receiveData(self):
        raw_message = self.socket.recv_multipart()
        # Topic to pierwszy element wiadomości
        topic = raw_message[0].decode()  # Decode topic
        # Message data to drugi element wiadomości
        message_data = raw_message[1]
        # Ensure message data is not empty before attempting to parse
        self.portData.ParseFromString(message_data)

    def updatePortState(self):
        if self.portData.ship.isInPort:
            dpg.show_item(item=f"{cfg.containers[5]}_image")
            dpg.show_item(item=f"{cfg.containers[5]}_ind")
        else:
            dpg.hide_item(item=f"{cfg.containers[5]}_image")
            dpg.hide_item(item=f"{cfg.containers[5]}_ind")

        for i in range(len(cfg.containers)):
            if i < 4:
                dpg.configure_item(
                    item=f"{cfg.containers[i]}_ind",
                    overlay=f"{self.portData.transitPoints[i].containersNo}/{cfg.containers_capacities[i]}",
                )
                dpg.set_value(
                    item=f"{cfg.containers[i]}_ind",
                    value=float(self.portData.transitPoints[i].containersNo)
                    / float(cfg.containers_capacities[i]),
                )
            elif i == 4:
                dpg.configure_item(
                    item=f"{cfg.containers[i]}_ind",
                    overlay=f"{self.portData.storageYard.containersNo}/{cfg.containers_capacities[i]}",
                )
                dpg.set_value(
                    item=f"{cfg.containers[i]}_ind",
                    value=self.portData.storageYard.containersNo
                    / cfg.containers_capacities[i],
                )
            else:
                dpg.configure_item(
                    item=f"{cfg.containers[i]}_ind",
                    overlay=f"{self.portData.ship.remainingContainersNo}/{cfg.containers_capacities[i]}",
                )
                dpg.set_value(
                    item=f"{cfg.containers[i]}_ind",
                    value=self.portData.ship.remainingContainersNo
                    / cfg.containers_capacities[i],
                )

        for i in range(len(self.portData.carts)):
            dpg.set_item_pos(
                item=f"cart_{i}", pos=cart_pos[self.portData.carts[i].cartPos]
            )
            if self.portData.carts[i].withContainer:
                dpg.configure_item(item=f"cart_{i}", texture_tag=myPort.imagesNames[3])
            else:
                dpg.configure_item(item=f"cart_{i}", texture_tag=myPort.imagesNames[2])


myPort = Port()
myPort.loadImages()
mainWindowWidth = WINDOW_WIDTH
mainWindowHeight = WINDOW_HEIGTH + 50 #offset for a toolbar

X_SCALING_FACTOR = float(WINDOW_WIDTH)/float(myPort.images[myPort.imagesNames[0]][0])
Y_SCALING_FACTOR = float(WINDOW_HEIGTH)/float(myPort.images[myPort.imagesNames[0]][1])
IND_WIDTH = 80
IND_HEIGTH = 25
SHIP_BEGINING_X = 1800
SHIP_BEGINING_Y = 100

# polozenia indykatorow
ind_xpos = [125, 125, 125, 125, 1000, 1900]
ind_ypos = [350, 520, 690, 860, 690, 520]

ind_xpos = [int((element + IND_WIDTH/2) * X_SCALING_FACTOR - IND_WIDTH/2) for element in ind_xpos]
ind_ypos = [int((element + IND_HEIGTH/2) * Y_SCALING_FACTOR - IND_HEIGTH/2) for element in ind_ypos]

cart_pos = {
    port.Cart.CartPosition.AFRICA_LP: [int(425*X_SCALING_FACTOR), int(310*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.AFRICA_WAITING: [int(540*X_SCALING_FACTOR), int(360*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.EUROPA_LP: [int(425*X_SCALING_FACTOR), int(455*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.EUROPA_WAITING: [int(540*X_SCALING_FACTOR), int(505*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.ASIA_LP: [int(425*X_SCALING_FACTOR), int(610*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.ASIA_WAITING: [int(540*X_SCALING_FACTOR), int(660*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.AMERICA_LP: [int(425*X_SCALING_FACTOR), int(770*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.AMERICA_WAITING: [int(540*X_SCALING_FACTOR), int(820*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.ST_LP1: [int(875*X_SCALING_FACTOR), int(310*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.ST_LP2: [int(1100*X_SCALING_FACTOR), int(310*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.ST_WAITING: [int(625*X_SCALING_FACTOR), int(190*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.SHIP_LP1: [int(1560*X_SCALING_FACTOR), int(345*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.SHIP_LP2: [int(1560*X_SCALING_FACTOR), int(545*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.SHIP_LP3: [int(1560*X_SCALING_FACTOR), int(740*Y_SCALING_FACTOR)],
    port.Cart.CartPosition.SHIP_WAITIMG: [int(1445*X_SCALING_FACTOR), int(295*Y_SCALING_FACTOR)],
}

def updateGUIState(sender, data):
    while True:
        myPort.receiveData()
        myPort.updatePortState()


with dpg.window(
    tag="mainWindow",
    label="Port w Rotterdamie ale lepiej",
    width=mainWindowWidth,
    height=mainWindowHeight,
):
    with dpg.drawlist(width=WINDOW_WIDTH, height=WINDOW_HEIGTH):
        dpg.draw_image(myPort.imagesNames[0], 
                        (0, 0), (WINDOW_WIDTH, WINDOW_HEIGTH), 
                        uv_min=(0, 0), uv_max=(1, 1))
        dpg.draw_image(myPort.imagesNames[1], 
                        (int(SHIP_BEGINING_X*X_SCALING_FACTOR), int(SHIP_BEGINING_Y*Y_SCALING_FACTOR)), 
                        (WINDOW_WIDTH, WINDOW_HEIGTH), 
                        uv_min=(0, 0), uv_max=(1, 1),
                        tag=f"{cfg.containers[5]}_image")

    for i in range(len(cfg.containers)):
        dpg.add_progress_bar(
            tag=f"{cfg.containers[i]}_ind",
            pos=[ind_xpos[i], ind_ypos[i]],
            width=IND_WIDTH,
            height=IND_HEIGTH,
        )

    cartPositions = list(cart_pos.values())
    for i in range(cfg.numberOfCarts):
        dpg.add_image(
            texture_tag=myPort.imagesNames[2], tag=f"cart_{i}", pos=cartPositions[i]
        )

with dpg.window(tag="controlWindow", pos = [0,0], min_size=[10, 10]):
    dpg.add_button(label="Update", callback=updateGUIState)

dpg.create_viewport(title="InPort App", width=mainWindowWidth, height=mainWindowHeight)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
