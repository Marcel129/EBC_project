import config as cfg
import dearpygui.dearpygui as dpg
import port_data_pb2 as port
import zmq

dpg.create_context()

cart_xpos = [125, 125, 125, 125, 1000]
cart_ypos = [300, 470, 640, 810, 690]

# polozenia indykatorow
ind_xpos = [125, 125, 125, 125, 1000, 1800]
ind_ypos = [300, 470, 640, 810, 690, 520]

cart_pos = {
    port.Cart.CartPosition.AFRICA_LP: [425, 285],
    port.Cart.CartPosition.AFRICA_WAITING: [540, 335],
    port.Cart.CartPosition.EUROPA_LP: [425, 430],
    port.Cart.CartPosition.EUROPA_WAITING: [540, 480],
    port.Cart.CartPosition.ASIA_LP: [425, 585],
    port.Cart.CartPosition.ASIA_WAITING: [540, 635],
    port.Cart.CartPosition.AMERICA_LP: [425, 745],
    port.Cart.CartPosition.AMERICA_WAITING: [540, 795],
    port.Cart.CartPosition.ST_LP1: [880, 285],
    port.Cart.CartPosition.ST_LP2: [1105, 285],
    port.Cart.CartPosition.ST_WAITING: [625, 165],
    port.Cart.CartPosition.SHIP_LP1: [1560, 320],
    port.Cart.CartPosition.SHIP_LP2: [1560, 520],
    port.Cart.CartPosition.SHIP_LP3: [1560, 715],
    port.Cart.CartPosition.SHIP_WAITIMG: [1445, 270],
}
tst = cart_pos[port.Cart.CartPosition.ST_LP2]


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
mainWindowWidth = myPort.images[myPort.imagesNames[0]][0]
mainWindowHeight = myPort.images[myPort.imagesNames[0]][1]


def updateGUIState(sender, data):
    while True:
        myPort.receiveData()
        myPort.updatePortState()


with dpg.window(
    tag="mainWindow",
    label="Port w Rotterdamie ale lepiej",
    width=mainWindowWidth,
    height=mainWindowHeight - 10,
):

    dpg.add_image(texture_tag=myPort.imagesNames[0], pos=[0, 0])
    dpg.add_image(
        texture_tag=myPort.imagesNames[1],
        tag=f"{cfg.containers[5]}_image",
        pos=[1800, 100],
    )

    for i in range(len(cfg.containers)):
        dpg.add_progress_bar(
            tag=f"{cfg.containers[i]}_ind",
            pos=[ind_xpos[i], ind_ypos[i]],
            width=80,
            height=25,
        )

    cartPositions = list(cart_pos.values())
    for i in range(cfg.numberOfCarts):
        dpg.add_image(
            texture_tag=myPort.imagesNames[2], tag=f"cart_{i}", pos=cartPositions[i]
        )

with dpg.window(tag="controlWindow"):
    dpg.add_button(label="Update", callback=updateGUIState)

dpg.create_viewport(title="InPort App", width=mainWindowWidth, height=mainWindowHeight)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
