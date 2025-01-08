import asyncio
import logging
import random
import random as rnd
import time
from typing import Dict, List, Set, Tuple

import config as cfg
import port_data_pb2 as port
import zmq
import zmq.asyncio

CRANE_1 = "SHIP_C1"  # UPPER
CRANE_2 = "SHIP_C2"  # LOWER
CRANE_3 = "SHIP_T1"  # AFRICA - EUROPA
CRANE_4 = "SHIP_T2"  # EUROPA - AMERICA
CRANE_5 = "SHIP_T3"  # AMERICA - ASIA
CRANE_6 = "SHIP_S1"

from enum import Enum


class PortPositions(Enum):
    AFRICA_LP = 0
    AFRICA_WAITING = 1
    EUROPA_LP = 2
    EUROPA_WAITING = 3
    ASIA_LP = 4
    ASIA_WAITING = 5
    AMERICA_LP = 6
    AMERICA_WAITING = 7
    ST_LP1 = 8
    ST_LP2 = 9
    ST_WAITING = 10
    SHIP_LP1 = 11
    SHIP_LP2 = 12
    SHIP_LP3 = 13
    SHIP_WAITIMG = 14


class Controller:
    def __init__(self):
        # State tracking
        self.myPort = port.PortState()

        # Setup ZeroMQ context
        self.zmq_context = zmq.Context()

        # Receiver
        self.receiver = self.zmq_context.socket(zmq.SUB)
        self.receiver.connect("tcp://127.0.0.1:5555")  # Example port
        self.receiver.setsockopt(zmq.SUBSCRIBE, b"")

        # Sender
        self.publisher_IPaddress = "localhost"
        self.publisher_port = "2000"

        self.sender = self.zmq_context.socket(zmq.PUB)
        self.sender.bind(f"tcp://{self.publisher_IPaddress}:{self.publisher_port}")

        # Port variables
        self.ship: bool = False
        self.ship_remainingContainersNo: int = 0
        self.containers: List[Dict[str, int]]

        self.cranes: List[Dict[str, bool]]

        self.carts: List[Dict[str, bool, int]]

        self.storage_containers = []  # TODO REST

    # async def process_event(self, message):
    #     # Parse incoming message based on type
    #     if isinstance(message, port.Ship):
    #         # if message.HasField("ship"):
    #         self.recieved_ship_status(message)
    #     if isinstance(message, port.Crane):
    #         self.recieved_cranes_status(message)
    #     if isinstance(message, port.Cart):
    #         self.recieved_cart_status(message)

    #         # elif message.HasField("storageYard"):
    #         #     self.handle_storage_yard_event(message.storageYard)
    #         # elif message.HasField("transitPoints"):
    #         #     self.handle_transit_point_event(message.transitPoints)
    #         # elif message.HasField("carts"):
    #         self.handle_cart_event(message.carts)

    def recieved_ship_status(self, msg):

        if not isinstance(msg, port.Ship):
            logging.error("Received message is not of type 'Ship'.")
            return

        self.ship = msg.isInPort
        self.ship_remainingContainersNo = msg.remainingContainersNo
        if self.ship_remainingContainersNo > 0:
            self.containers = generate_unique_elements(self.ship_remainingContainersNo)
        logging.info(
            f"Ship status is updated. Current status: {self.ship}, no: {self.ship_remainingContainersNo}"
        )

    def recieved_cranes_status(self, msg):

        found = False

        # Iterate through the list of cranes to check if the crane already exists
        for existing_crane in self.cranes:
            if existing_crane["Crane_name"] == msg.name:
                # Update the crane's status if it exists
                existing_crane["Status"] = msg.isReady
                found = True
                logging.info(
                    f"Crane {msg.name} status is updated. Current status: {msg.isReady}"
                )
                break

        # If the crane is not found, append it to the list
        if not found:
            self.cranes.append({"Crane_name": msg.name, "Status": msg.isReady})
            logging.info(f"Crane {msg.name} added. Initial status: {msg.isReady}")

    def recieved_cart_status(self, msg):

        found = False

        # Iterate through the list of carts to check if the crane already exists
        for existing_carts in self.carts:
            if existing_carts["Cart_name"] == msg.name:
                # Update the cart's status if it exists
                existing_carts["Status"] = msg.withContainer
                existing_carts["Position"] = msg.cartPos
                existing_carts["Target"] = msg.targetID

                found = True
                logging.info(
                    f"Carts {msg.name} status is updated. Current status: {msg.isReady}. Current position: {msg.cartPos}"
                )
                break

        # If the carts is not found, append it to the list
        if not found:
            self.carts.append(
                {
                    "Cart_name": msg.name,
                    "Status": msg.withContainer,
                    "Position": msg.cartPos,
                    "Target": msg.targetID,
                }
            )
            logging.info(
                f"Cart_name {msg.name} added. Initial status: {msg.withContainer}, position: {msg.cartPos}, target: {msg.targetID}"
            )

    def move_container(self, position_set, unload):
        tmp = [cart for cart in self.carts if cart["Position"] in position_set]
        tmp = [cart for cart in tmp if cart["Status"] != unload]
        if len(tmp) == 1 or len(tmp) == 2:
            if unload == True:
                self.ship_remainingContainersNo -= 1
            else:
                pass
                # TODO INCREMENT TRANSIT OR STORAGE

            cart_to_update = tmp[0]

            for cart in self.carts:
                if cart["Cart_name"] == cart_to_update["Cart_name"]:
                    cart["Status"] = unload  # Mark the cart as updated (Status: True)
                    if unload == True:
                        cart["Target"] = self.containers[-1][
                            1
                        ]  # Set the Target from the last container's value
                    else:
                        cart["Target"] = PortPositions.SHIP_WAITIMG
                    break  # We found and updated the cart, no need to continue looping

            if self.containers and unload:
                self.containers.pop()

    def update_containers_status(self):

        for existing_crane in self.cranes:
            crane_port_1 = (
                1
                if (
                    existing_crane["Crane_name"] == CRANE_1
                    and existing_crane["Status"] == True
                )
                else 0
            )
            crane_port_2 = (
                1
                if (
                    existing_crane["Crane_name"] == CRANE_2
                    and existing_crane["Status"] == True
                )
                else 0
            )
            crane_port_3 = (
                1
                if (
                    existing_crane["Crane_name"] == CRANE_3
                    and existing_crane["Status"] == True
                )
                else 0
            )
            crane_port_4 = (
                1
                if (
                    existing_crane["Crane_name"] == CRANE_4
                    and existing_crane["Status"] == True
                )
                else 0
            )
            crane_port_5 = (
                1
                if (
                    existing_crane["Crane_name"] == CRANE_5
                    and existing_crane["Status"] == True
                )
                else 0
            )
            crane_port_6 = (
                1
                if (
                    existing_crane["Crane_name"] == CRANE_6
                    and existing_crane["Status"] == True
                )
                else 0
            )

        if crane_port_1:
            self.move_container({PortPositions.SHIP_LP1, PortPositions.SHIP_LP2}, True)
        if crane_port_2:
            self.move_container({PortPositions.SHIP_LP2, PortPositions.SHIP_LP3}, True)
        if crane_port_3:
            self.move_container(
                {PortPositions.AFRICA_LP, PortPositions.EUROPA_LP}, False
            )
        if crane_port_4:
            self.move_container(
                {PortPositions.EUROPA_LP, PortPositions.AMERICA_LP}, False
            )
        if crane_port_5:
            self.move_container(
                {PortPositions.AMERICA_LP, PortPositions.ASIA_LP}, False
            )
        if (
            crane_port_6
            and self.ship
            and len(self.storage_containers) < cfg.containers_capacities[-2]
        ):
            self.move_container({PortPositions.SHIP_LP2, PortPositions.SHIP_LP3}, False)
        elif crane_port_6 and not self.ship and len(self.containers) > 0:
            self.move_container({PortPositions.SHIP_LP2, PortPositions.SHIP_LP3}, True)

    # def handle_ship_event(self, ship):
    #     self.myPort.ship = ship

    # def handle_storage_yard_event(self, storage_yard):
    #     self.storage_yard = storage_yard
    #     print("Updated storage yard state:", storage_yard.containersNo)

    # def handle_transit_point_event(self, transit_points):
    #     for transit_point in transit_points:
    #         self.transit_points[transit_point.ID] = transit_point.containersNo
    #         print(
    #             f"Transit point {transit_point.ID} updated: {transit_point.containersNo}"
    #         )

    # def handle_cart_event(self, carts):
    #     self.carts = carts
    #     for cart in carts:
    #         print(
    #             f"Cart position: {cart.cartPos}, With container: {cart.withContainer}"
    #         )

    def add_cart_to_port_state(self, port_state, cart_data):
        """
        Add or update a cart in the PortState protobuf message.

        Args:
            port_state (port.PortState): The PortState protobuf message.
            cart_data (dict): A dictionary with cart details (name, withContainer, cartPos, targetID).
        """
        # Check if the cart already exists
        for existing_cart in port_state.carts:
            if existing_cart.name == cart_data["Cart_name"]:
                # Update the existing cart
                existing_cart.withContainer = cart_data["Status"]
                existing_cart.cartPos = cart_data["Position"]
                existing_cart.targetID = cart_data["Target"]
                logging.info(f"Updated cart {cart_data['Cart_name']} in PortState.")
                return

        # If the cart does not exist, add a new one
        new_cart = port_state.carts.add()
        new_cart.name = cart_data["Cart_name"]
        new_cart.withContainer = cart_data["Status"]
        new_cart.cartPos = cart_data["Position"]
        new_cart.targetID = cart_data["Target"]
        logging.info(f"Added new cart {cart_data['Cart_name']} to PortState.")

    def main_loop(self):
        """
        Main loop to process incoming messages of various types.
        Continuously listens for messages and processes them based on their expected type.
        """
        while True:
            try:
                # Receive raw message
                # raw_message = await port.Ship.ParseFromString(self.receiver.recv())
                # Receive raw message
                # raw_message = await self.receiver.recv()  # Await to get the raw message
                # message = port.Ship()  # Create an empty Ship message
                # message.ParseFromString(raw_message)  # Parse the raw message
                # # self.Ship.ParseFromString(self.socket.recv())
                # # # raw_message is a list, the second part (index 1) is the Protobuf message
                # # message = port.Ship.FromString(raw_message)
                # logging.info("Received Ship message.")
                # await self.recieved_ship_status(raw_message)
                # Receive raw message
                self.Ship = port.Ship()
                self.Ship.ParseFromString(self.receiver.recv())
                # raw_message.ParseFromString(
                #     self.receiver.recv()
                # )  # No await needed, it's synchronous

                # logging.info(f"Received raw message: {self.Ship}")

                # Parse the raw message into the Ship object
                # message = port.Ship()
                # success = message.ParseFromString(raw_message)
                # print(success)
                # self.recieved_ship_status(
                #     message.ParseFromString(self.receiver.recv())
                # )

            # # # Identify and process message based on known message structure
            # # if self.is_port_state_message(raw_message):
            # #     message = port.PortState.FromString(raw_message)
            # #     logging.info("Received PortState message.")
            # #     await self.process_event(message)

            # if self.is_ship_message(raw_message):
            #     message = port.Ship.FromString(raw_message)
            #     logging.info("Received Ship message.")
            #     self.recieved_ship_status(message)

            # elif self.is_cart_message(raw_message):
            #     message = port.Cart.FromString(raw_message)
            #     logging.info("Received Cart message.")
            #     self.recieved_cart_status(message)

            # elif self.is_crane_message(raw_message):
            #     message = port.Crane.FromString(raw_message)
            #     logging.info("Received Crane message.")
            #     self.recieved_cranes_status(message)

            # # elif self.is_storage_yard_message(raw_message):
            # #     message = port.StorageYard.FromString(raw_message)
            # #     logging.info("Received StorageYard message.")
            # #     self.handle_storage_yard_event(message)

            # # elif self.is_transit_point_message(raw_message):
            # #     message = port.TransitPoint.FromString(raw_message)
            # #     logging.info("Received TransitPoint message.")
            # #     self.handle_transit_point_event(message)

            # else:
            #     logging.warning("Received unrecognized message.")

            # self.update_containers_status()
            # self.send_command()
            except Exception as e:
                logging.error(f"Error processing message: {e}", exc_info=True)

    def send_command(self, topic, data):
        # Serialize and send a Protobuf message
        self.myPort.ship.isInPort = self.ship
        self.myPort.ship.remainingContainersNo = self.ship_remainingContainersNo

        self.add_cart_to_port_state(self.myPort, self.carts)

        transitPointsIDs = [
            port.TransitPoint.Port_ID.AFRICA,
            port.TransitPoint.Port_ID.EUROPA,
            port.TransitPoint.Port_ID.ASIA,
            port.TransitPoint.Port_ID.AMERICA,
        ]

        self.myPort.storageYard.containersNo = int(
            rnd.random() * cfg.containers_capacities[4]
        )

        i = 0
        for id in transitPointsIDs:
            new_point = self.myPort.transitPoints.add()
            new_point.ID = id
            new_point.containersNo = int(rnd.random() * cfg.containers_capacities[i])
            i += 1
        self.sender.send_multipart([topic.encode(), data.SerializeToString()])


def generate_unique_elements(n: int, target_mod: int = 4) -> List[Dict[str, int]]:
    elements = []
    unique_numbers = set()

    for _ in range(n):
        # Generate a unique number
        while True:
            cont_numb = random.randint(1, n + 1)  # Example range for unique numbers
            if cont_numb not in unique_numbers:
                unique_numbers.add(cont_numb)
                break

        # Calculate the target as a module of the unique number
        cont_target = cont_numb % target_mod

        # Add the unique dictionary to the list
        elements.append({"cont_numb": cont_numb, "cont_target": cont_target})

    return elements


if __name__ == "__main__":
    controller = Controller()

    try:
        (controller.main_loop())
    except KeyboardInterrupt:
        logging.info("Simulation terminated.")
