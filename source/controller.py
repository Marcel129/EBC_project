import asyncio
import logging
import random
import random as rnd
import threading
import time
from typing import Dict, List, Set, Tuple

import config as cfg
import port_data_pb2 as port
import zmq
import zmq.asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
# logging.propagate = False
# CRANE_1 = "SHIP_C1"  # UPPER
# CRANE_2 = "SHIP_C2"  # LOWER
# CRANE_3 = "SHIP_T1"  # AFRICA - EUROPA
# CRANE_4 = "SHIP_T2"  # EUROPA - AMERICA
# CRANE_5 = "SHIP_T3"  # AMERICA - ASIA
# CRANE_6 = "SHIP_S1"

CRANE_1 = "CRANE_1"  # UPPER
CRANE_2 = "CRANE_2"  # LOWER
CRANE_3 = "CRANE_3"  # AFRICA - EUROPA
CRANE_4 = "CRANE_4"  # EUROPA - AMERICA
CRANE_5 = "CRANE_5"  # AMERICA - ASIA
CRANE_6 = "CRANE_6"

from enum import Enum

# TODO
# TODO 2. Flagi kiedy wyslamy msg do world


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


transitPointsIDs = [
    port.TransitPoint.Port_ID.AFRICA,
    port.TransitPoint.Port_ID.EUROPA,
    port.TransitPoint.Port_ID.ASIA,
    port.TransitPoint.Port_ID.AMERICA,
]


class Controller:
    def __init__(self):
        self.running = True

        # Setup ZeroMQ context
        self.zmq_context = zmq.Context()

        # Receiver
        self.receiver_IPaddress = "localhost"
        self.receiver_port = "5555"

        self.receiver = self.zmq_context.socket(zmq.SUB)
        self.receiver.connect(f"tcp://{self.receiver_IPaddress}:{self.receiver_port}")
        self.receiver.setsockopt(zmq.SUBSCRIBE, b"")

        # Sender
        self.sender_IPaddress = "localhost"
        self.sender_port = "2000"

        self.sender = self.zmq_context.socket(zmq.PUB)
        self.sender.bind(f"tcp://{self.sender_IPaddress}:{self.sender_port}")

        # ACK Socket (REP)
        self.ack_socket = self.zmq_context.socket(zmq.REP)
        self.ack_socket.bind("tcp://127.0.0.1:5556")  # Listen for ACK requests

        # Receiver Socket for ACKs (REQ)
        self.ack_receiver = self.zmq_context.socket(zmq.REQ)
        self.ack_receiver.connect("tcp://127.0.0.1:5560")

        # Port variables
        self.ship: bool = False
        self.ship_remainingContainersNo: int = 0
        self.containers: List[Dict[str, int]] = []  # Initialize containers
        self.cranes: List[Dict[str, bool]] = []  # Initialize cranes
        self.carts: List[Dict[str, bool, int]] = []  # Initialize carts
        self.transit_points: List[Dict[str, int]] = []  # Initialize transit points
        self.storage_containers: int = 0
        self.storage_containers_info: List[Dict[str, int]] = []  # Initialize containers
        # State tracking
        self.myPort = port.PortState()

        # flags for generating messages
        self.ship_message_flag = False
        self.carts_message_flag = [False for __ in range(cfg.numberOfCarts)]
        self.cranes_message_flag = [False for __ in range(cfg.numberOfCranes)]
        self.transit_point_flag = [False for __ in range(4)]
        self.storage_yard_flag = False

        self.poller = zmq.Poller()  # Create a poller

    def recieved_ship_status(self, msg):

        if not isinstance(msg, port.Ship):
            logging.error("Received message is not of type 'Ship'.")
            return
        print("get ship message from world")
        self.ship = msg.isInPort
        self.ship_remainingContainersNo = msg.remainingContainersNo
        if self.ship_remainingContainersNo > 0:
            self.containers = generate_unique_elements(self.ship_remainingContainersNo)
        logging.info(
            f"Ship status is updated. Current status: {self.ship}, no: {self.ship_remainingContainersNo}"
        )
        # if not isinstance(msg, port.Ship):
        #     logging.error("Received message is not of type 'Ship'.")
        #     return
        # print("get ship message from world")
        # self.ship = msg.isInPort
        # self.ship_remainingContainersNo = 1
        # if self.ship_remainingContainersNo > 0:
        #     self.containers.append({"cont_numb": 0, "cont_target": 6})
        # logging.info(
        #     f"Ship status is updated. Current status: {self.ship}, no: {self.ship_remainingContainersNo}"
        # )

    def recieved_crane_status(self, msg):

        found = False

        # Iterate through the list of cranes to check if the crane already exists
        for existing_crane in self.cranes:
            if existing_crane["Crane_name"] == msg.name:
                # Update the crane's status if it exists
                existing_crane["Status"] = msg.isReady
                found = True
                print(
                    f"Crane {msg.name} status is updated. Current status: {msg.isReady}"
                )
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
                    f"Carts {msg.name} status is updated. Current status: {msg.withContainer}. Current position: {msg.cartPos}. Current target: {msg.targetID}"
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

    def recieved_transit_point_status(self, msg):
        found = False
        # Iterate through the list of transit points to check if the crane already exists
        for existing_trans_point in self.transit_points:
            if existing_trans_point["Port_ID"] == msg.ID:
                # Update the crane's status if it exists
                existing_trans_point["containersNo"] = msg.containersNo
                found = True
                logging.info(
                    f"TransitPoint {msg.ID} status is updated. Current status: {msg.containersNo}"
                )
                break
        # If the crane is not found, append it to the list
        if not found:
            self.transit_points.append(
                {"Port_ID": msg.ID, "containersNo": msg.containersNo}
            )
            logging.info(
                f"TransitPoint {msg.ID} added. Initial status: {msg.containersNo}"
            )

    def recieved_storage_yard_status(self, msg):
        self.storage_containers = msg.containersNo
        logging.info(
            f"Storage yard is updated. Current status: {self.storage_containers}"
        )

    def move_container(self, position_set, unload, target_flag):
        # tmp = [
        #     cart for cart in self.carts if cart["Position"] in position_set
        # ]  # Check if cart in correct place
        # tmp = [
        #     cart for cart in tmp if cart["Status"] != unload
        # ]  # Check if it has an container
        tmp = [
            cart
            for cart in self.carts
            if cart["Position"] in position_set and cart["Status"] != unload
        ]  # Check if cart in correct place and if it doesn't have a container (unload)
        if len(tmp) == 1 or len(tmp) == 2:
            # cart_to_update = tmp[0]
            cart_to_update = random.choice(tmp) if len(tmp) == 2 else tmp[0]
            # cart_to_update = tmp[1] if len(tmp) == 2 else tmp[0]
            occupied_fields = [
                (
                    1
                    if any(cart["Position"] == position.value for cart in self.carts)
                    else 0
                )
                for position in PortPositions
            ]

            # print(f"Car to update: f{cart_to_update}")
            # print(f"Car to update: f{cart_to_update}")
            for cart in self.carts:
                if target_flag == "unload_ship":
                    if (
                        cart["Cart_name"] == cart_to_update["Cart_name"]
                        and (self.ship_remainingContainersNo > 0)
                        and self.containers
                        and cart["Status"] == False
                        and unload
                    ):
                        cart["Status"] = unload  # Mark the cart as updated
                        cart["Target"] = self.containers[-1][
                            "cont_target"
                        ]  # Set the Target from the last container's value
                        self.ship_remainingContainersNo -= 1
                        self.containers.pop()
                        time.sleep(0.5)
                        if occupied_fields[cart["Target"]]:
                            if not occupied_fields[(cart["Target"] + 1)]:
                                cart["Position"] = cart["Target"] + 1
                            elif not occupied_fields[PortPositions.ST_LP1.value]:
                                cart["Position"] = PortPositions.ST_LP1.value
                            elif not occupied_fields[PortPositions.ST_LP2.value]:
                                cart["Position"] = PortPositions.ST_LP2.value
                            elif not occupied_fields[PortPositions.ST_WAITING.value]:
                                cart["Position"] = PortPositions.ST_WAITING.value
                        else:
                            cart["Position"] = cart["Target"]
                        break  # We found and updated the cart, no need to continue looping

                elif target_flag == "load_transit":
                    if cart["Cart_name"] == cart_to_update["Cart_name"]:
                        for i, existing_trans_point in enumerate(self.transit_points):
                            if (
                                existing_trans_point["Port_ID"] == cart["Position"]
                                and cart["Status"] == True
                                and existing_trans_point["containersNo"]
                                < cfg.containers_capacities[i]
                            ):
                                time.sleep(0.5)
                                cart["Status"] = unload  # Mark the cart as updated
                                existing_trans_point["containersNo"] += 1
                                if self.ship:
                                    cart["Target"] = PortPositions.SHIP_WAITIMG.value
                                else:
                                    cart["Target"] = PortPositions.ST_WAITING.value
                            elif (
                                existing_trans_point["containersNo"]
                                == cfg.containers_capacities[i]
                            ):
                                time.sleep(0.5)
                                cart["Position"] = PortPositions.ST_WAITING.value
                        break  # We found and updated the cart, no need to continue looping
                elif target_flag == "do_storage":
                    if cart["Cart_name"] == cart_to_update["Cart_name"]:
                        if (
                            unload == True
                            and (self.storage_containers > 0)
                            and cart["Status"] == False
                        ):
                            self.storage_containers -= 1
                            cart["Target"] = self.storage_containers_info[-1][
                                "cont_target"
                            ]
                            self.storage_containers_info.pop()
                            time.sleep(0.5)
                            cart["Status"] = unload  # Mark the cart as updated
                        elif (
                            not unload
                            and (
                                self.storage_containers < cfg.containers_capacities[-2]
                            )
                            and cart["Status"] == True
                        ):
                            self.storage_containers_info.append(
                                {
                                    "cont_numb": 0,
                                    "cont_target": cart_to_update["Target"],
                                }
                            )
                            self.storage_containers += 1
                            time.sleep(0.5)
                            cart["Status"] = unload  # Mark the cart as updated
                            if self.ship:
                                cart["Target"] = PortPositions.SHIP_WAITIMG.value
                            else:
                                cart["Target"] = PortPositions.ST_WAITING.value
                        break  # We found and updated the cart, no need to continue looping

    def update_containers_status(self):

        if len(self.cranes) == cfg.numberOfCranes:
            crane_ports = {
                "CRANE_1": 0,
                "CRANE_2": 0,
                "CRANE_3": 0,
                "CRANE_4": 0,
                "CRANE_5": 0,
                "CRANE_6": 0,
            }

            for existing_crane in self.cranes:
                if existing_crane["Status"] == True:
                    crane_name = existing_crane["Crane_name"]
                    if crane_name in crane_ports:
                        crane_ports[crane_name] = 1
            unload_ship = "unload_ship"
            load_transit = "load_transit"
            do_storage = "do_storage"
            if crane_ports["CRANE_1"]:
                self.move_container(
                    {PortPositions.SHIP_LP1.value, PortPositions.SHIP_LP2.value},
                    True,
                    unload_ship,
                )
            if crane_ports["CRANE_2"]:
                self.move_container(
                    {PortPositions.SHIP_LP2.value, PortPositions.SHIP_LP3.value},
                    True,
                    unload_ship,
                )
            if crane_ports["CRANE_3"]:
                self.move_container(
                    {PortPositions.AFRICA_LP.value, PortPositions.EUROPA_LP.value},
                    False,
                    load_transit,
                )
            if crane_ports["CRANE_4"]:
                self.move_container(
                    {PortPositions.EUROPA_LP.value, PortPositions.ASIA_LP.value},
                    False,
                    load_transit,
                )
            if crane_ports["CRANE_5"]:
                self.move_container(
                    {PortPositions.ASIA_LP.value, PortPositions.AMERICA_LP.value},
                    False,
                    load_transit,
                )
            if crane_ports["CRANE_6"]:
                self.move_container(
                    {PortPositions.ST_LP1.value, PortPositions.ST_LP2.value},
                    False,
                    do_storage,
                )
            # elif crane_ports["CRANE_6"] and (not self.ship):
            #     self.move_container(
            #         {PortPositions.ST_LP1.value, PortPositions.ST_LP2.value},
            #         True,
            #         do_storage,
            # )

    def move_cart(self):

        for cart in self.carts:

            occupied_fields = [
                (
                    1
                    if any(cart["Position"] == position.value for cart in self.carts)
                    else 0
                )
                for position in PortPositions
            ]

            if cart["Position"] != cart["Target"]:
                if occupied_fields[cart["Target"]]:
                    if cart["Target"] < PortPositions.SHIP_WAITIMG.value:
                        if (
                            not occupied_fields[(cart["Target"] + 1)]
                            and cart["Target"] <= PortPositions.AMERICA_LP.value
                        ):
                            time.sleep(0.5)
                            cart["Position"] = cart["Target"] + 1
                        elif (
                            not occupied_fields[PortPositions.ST_LP1.value]
                            # and self.cranes_message_flag[-1] == False
                        ):
                            time.sleep(0.5)
                            cart["Position"] = PortPositions.ST_LP1.value
                        elif (
                            not occupied_fields[PortPositions.ST_LP2.value]
                            # and self.cranes_message_flag[-1] == False
                        ):
                            time.sleep(0.5)
                            cart["Position"] = PortPositions.ST_LP2.value
                        elif not occupied_fields[PortPositions.ST_WAITING.value]:
                            time.sleep(0.5)
                            cart["Position"] = PortPositions.ST_WAITING.value
                    elif cart["Target"] == PortPositions.SHIP_WAITIMG.value:
                        time.sleep(0.5)
                        cart["Position"] = cart["Target"]
                else:
                    time.sleep(0.5)
                    cart["Position"] = cart["Target"]

        time.sleep(0.5)

        for cart in self.carts:

            occupied_fields = [
                (
                    1
                    if any(cart["Position"] == position.value for cart in self.carts)
                    else 0
                )
                for position in PortPositions
            ]
            if (
                (
                    cart["Target"] == PortPositions.AFRICA_LP.value
                    and self.transit_points[0]["containersNo"]
                    == cfg.containers_capacities[0]
                    and cart["Status"] == True
                )
                or (
                    cart["Target"] == PortPositions.EUROPA_LP.value
                    and self.transit_points[1]["containersNo"]
                    == cfg.containers_capacities[1]
                    and cart["Status"] == True
                )
                or (
                    cart["Target"] == PortPositions.ASIA_LP.value
                    and self.transit_points[2]["containersNo"]
                    == cfg.containers_capacities[2]
                    and cart["Status"] == True
                )
                or (
                    cart["Target"] == PortPositions.AMERICA_LP.value
                    and self.transit_points[3]["containersNo"]
                    == cfg.containers_capacities[3]
                    and cart["Status"] == True
                )
            ):
                if (
                    not occupied_fields[PortPositions.ST_LP1.value]
                    # and self.cranes_message_flag[-1] == False
                ):
                    time.sleep(0.5)
                    cart["Position"] = PortPositions.ST_LP1.value
                elif (
                    not occupied_fields[PortPositions.ST_LP2.value]
                    # and self.cranes_message_flag[-1] == False
                ):
                    time.sleep(0.5)
                    cart["Position"] = PortPositions.ST_LP2.value
                else:
                    time.sleep(0.5)
                    cart["Position"] = PortPositions.ST_WAITING.value

        time.sleep(0.5)

        for cart in self.carts:

            occupied_fields = [
                (
                    1
                    if any(cart["Position"] == position.value for cart in self.carts)
                    else 0
                )
                for position in PortPositions
            ]
            if (cart["Position"] == cart["Target"]) and (
                cart["Position"] == PortPositions.ST_WAITING.value
                or cart["Position"] == PortPositions.SHIP_WAITIMG.value
            ):
                if cart["Position"] == PortPositions.ST_WAITING.value:
                    if (
                        not occupied_fields[PortPositions.ST_LP1.value]
                        # and self.cranes_message_flag[-1] == False
                    ):
                        time.sleep(0.5)
                        cart["Position"] = PortPositions.ST_LP1.value
                    elif (
                        not occupied_fields[PortPositions.ST_LP2.value]
                        # and self.cranes_message_flag[-1] == False
                    ):
                        time.sleep(0.5)
                        cart["Position"] = PortPositions.ST_LP2.value
                if (
                    cart["Position"]
                    == PortPositions.SHIP_WAITIMG.value
                    # and cart["Status"] == False
                ):
                    if (
                        not occupied_fields[PortPositions.SHIP_LP1.value]
                        # and self.cranes_message_flag[0] == False
                    ):
                        time.sleep(0.5)
                        cart["Position"] = PortPositions.SHIP_LP1.value
                    elif (
                        not occupied_fields[PortPositions.SHIP_LP2.value]
                        # and (
                        #     self.cranes_message_flag[0] == False
                        #     or self.cranes_message_flag[1] == False
                        # )
                    ):
                        time.sleep(0.5)
                        cart["Position"] = PortPositions.SHIP_LP2.value
                    elif (
                        not occupied_fields[PortPositions.SHIP_LP3.value]
                        # and self.cranes_message_flag[1] == False
                    ):
                        time.sleep(0.5)
                        cart["Position"] = PortPositions.SHIP_LP3.value

    def check_port_status(self):

        if self.ship_remainingContainersNo == 0 and self.ship:
            self.ship = False
            self.ship_message_flag = True

        tmp = self.carts[:]  # Create a shallow copy of the carts list
        if (
            len(tmp) != cfg.numberOfCarts
            or len(self.cranes) != cfg.numberOfCranes
            or len(self.transit_points) != 4
        ):
            return False

        for existing_crane in self.cranes:
            if (
                existing_crane["Crane_name"] == CRANE_1
                and existing_crane["Status"] == True
            ):
                # Filter carts that are at SHIP_LP1 and update the crane status
                for cart in tmp[
                    :
                ]:  # Iterate over a copy of the list to safely modify `tmp`
                    if cart["Position"] == PortPositions.SHIP_LP1.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[0] = True
                    elif cart["Position"] == PortPositions.SHIP_LP2.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[0] = True
            elif (
                existing_crane["Crane_name"] == CRANE_2
                and existing_crane["Status"] == True
            ):
                # Filter carts that are at SHIP_LP1 and update the crane status
                for cart in tmp[
                    :
                ]:  # Iterate over a copy of the list to safely modify `tmp`
                    if cart["Position"] == PortPositions.SHIP_LP2.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[1] = True
                    elif cart["Position"] == PortPositions.SHIP_LP3.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[1] = True
            elif (
                existing_crane["Crane_name"] == CRANE_3
                and existing_crane["Status"] == True
            ):
                # Filter carts that are at SHIP_LP1 and update the crane status
                for cart in tmp[
                    :
                ]:  # Iterate over a copy of the list to safely modify `tmp`
                    if cart["Position"] == PortPositions.AFRICA_LP.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[2] = True
                    elif cart["Position"] == PortPositions.EUROPA_LP.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[2] = True
            elif (
                existing_crane["Crane_name"] == CRANE_4
                and existing_crane["Status"] == True
            ):
                # Filter carts that are at SHIP_LP1 and update the crane status
                for cart in tmp[
                    :
                ]:  # Iterate over a copy of the list to safely modify `tmp`
                    if cart["Position"] == PortPositions.EUROPA_LP.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[3] = True
                    elif cart["Position"] == PortPositions.AMERICA_LP.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[3] = True
            elif (
                existing_crane["Crane_name"] == CRANE_5
                and existing_crane["Status"] == True
            ):
                # Filter carts that are at SHIP_LP1 and update the crane status
                for cart in tmp[
                    :
                ]:  # Iterate over a copy of the list to safely modify `tmp`
                    if cart["Position"] == PortPositions.AMERICA_LP.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[-2] = True
                    elif cart["Position"] == PortPositions.ASIA_LP.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[-2] = True
            elif (
                existing_crane["Crane_name"] == CRANE_6
                and existing_crane["Status"] == True
            ):
                # Filter carts that are at SHIP_LP1 and update the crane status
                for cart in tmp[
                    :
                ]:  # Iterate over a copy of the list to safely modify `tmp`
                    if cart["Position"] == PortPositions.ST_LP1.value:
                        time.sleep(0.5)
                        # existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[-1] = True
                    elif cart["Position"] == PortPositions.ST_LP2.value:
                        time.sleep(0.5)
                        existing_crane["Status"] = False
                        tmp.remove(cart)  # Remove the cart from tmp
                        # self.cranes_message_flag[-1] = True

        self.generate_messages()

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
                return

        # If the cart does not exist, add a new one
        new_cart = port_state.carts.add()
        new_cart.name = cart_data["Cart_name"]
        new_cart.withContainer = cart_data["Status"]
        new_cart.cartPos = cart_data["Position"]
        new_cart.targetID = cart_data["Target"]
        logging.info(f"Added new cart {cart_data['Cart_name']} to PortState.")

    def add_transit_points_to_port_state(self, port_state, transit_data):
        """
        Add or update a cart in the PortState protobuf message.

        Args:
            port_state (port.PortState): The PortState protobuf message.
            cart_data (dict): A dictionary with cart details (name, withContainer, cartPos, targetID).
        """

        # Check if the cart already exists
        for existing_trans_point in port_state.transitPoints:
            if existing_trans_point.ID == transit_data["Port_ID"]:
                existing_trans_point.containersNo = transit_data["containersNo"]
                # print(f"Sent transit point to gui: {existing_trans_point} id: {existing_trans_point.ID}")
                return

        # If the cart does not exist, add a new one
        new_transit = port_state.transitPoints.add()
        new_transit.ID = transit_data["Port_ID"]
        new_transit.containersNo = transit_data["containersNo"]
        logging.info(f"Added new transit {transit_data['Port_ID']} to PortState.")

    def send_with_ack(self, message, topic, flag_variable, timeout=1000):
        """
        Helper function to send a message with acknowledgment.
        """
        # Send message
        self.sender.send_multipart([topic.encode(), message])
        logging.info(f"Sent {topic} message.")

        # Poll for acknowledgment
        poller = zmq.Poller()
        poller.register(self.ack_receiver, zmq.POLLIN)

        # Send ACK_REQUEST if the socket is ready for sending
        if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
            self.ack_receiver.send_string("ACK_REQUEST")

        # Poll for acknowledgment
        if poller.poll(timeout):  # Timeout in milliseconds
            ack = self.ack_receiver.recv_string()
            if ack == "ACK":
                flag_variable = False
                logging.info(f"ACK received for {topic}")
            else:
                logging.warning(f"ACK received but not 'ACK' for {topic}")
        else:
            logging.warning(f"ACK timeout for {topic}")

    def generate_ship_message(self):
        """
        Generate and send a Ship message.
        """
        if self.ship_remainingContainersNo == 0:
            ship = port.Ship()
            ship.isInPort = self.ship
            ship.remainingContainersNo = self.ship_remainingContainersNo

            self.send_with_ack(ship.SerializeToString(), "ship", self.ship_message_flag)

    def generate_crane_message(self):
        """
        Generate and send a Crane message.
        """
        for i, existing_crane in enumerate(self.cranes):
            if self.cranes_message_flag[i]:
                crane = port.Crane()
                crane.name = existing_crane["Crane_name"]
                crane.isReady = existing_crane["Status"]

                self.send_with_ack(
                    crane.SerializeToString(), "crane", self.cranes_message_flag[i]
                )

    def generate_cart_message(self):
        """
        Generate and send a Cart message.
        """
        for i, existing_cart in enumerate(self.myPort.carts):
            if self.carts_message_flag[i]:
                cart = port.Cart()
                cart.name = existing_cart["Cart_name"]
                cart.withContainer = existing_cart["Status"]
                cart.cartPos = existing_cart.cartPos["Position"]
                cart.targetID = existing_cart.targetID["Target"]

                self.send_with_ack(
                    cart.SerializeToString(), "cart", self.carts_message_flag[i]
                )

    def generate_transit_point_message(self):
        """
        Generate and send a TransitPoint message.
        """
        for i, existing_trans_point in enumerate(self.transit_points):
            if self.transit_point_flag[i]:
                transit_point = port.TransitPoint()
                transit_point.ID = existing_trans_point["Port_ID"]
                transit_point.containersNo = existing_trans_point["containersNo"]

                self.send_with_ack(
                    transit_point.SerializeToString(),
                    "transit_point",
                    self.transit_point_flag[i],
                )

    def generate_storage_yard_message(self):
        """
        Generate and send a StorageYard message.
        """
        storage_yard = port.StorageYard()
        storage_yard.containersNo = self.storage_containers

        self.send_with_ack(
            storage_yard.SerializeToString(), "storage_yard", self.storage_yard_flag
        )

    def generate_messages(self):
        if self.ship_message_flag:
            self.generate_ship_message()
        if self.storage_yard_flag:
            self.generate_storage_yard_message()
        if self.transit_point_flag:
            self.generate_transit_point_message()
        if any(self.cranes_message_flag):
            self.generate_crane_message()
        if any(self.carts_message_flag):
            self.generate_cart_message()

    def send_port_state(self):
        while self.running:

            for cart_data in self.carts:
                self.add_cart_to_port_state(self.myPort, cart_data)
            for existing_trans_point in self.transit_points:
                self.add_transit_points_to_port_state(self.myPort, existing_trans_point)

            # Serialize and send a Protobuf message
            self.myPort.ship.isInPort = self.ship
            self.myPort.ship.remainingContainersNo = self.ship_remainingContainersNo
            self.myPort.storageYard.containersNo = self.storage_containers
            # Iterate through self.carts and add/update each car

            topic = "port_state"
            self.sender.send_multipart(
                [topic.encode(), self.myPort.SerializeToString()]
            )
            # logging.info(f"PortState sent: {self.myPort}")
            time.sleep(1)

    def main_loop(self):
        """
        Main loop to process incoming messages of various types.
        Continuously listens for messages and processes them based on their expected type.
        """

        # Register the receiver socket with the poller for POLLIN event
        self.poller.register(self.receiver, zmq.POLLIN)

        while self.running:
            try:

                # Poll the socket for events with a timeout (in milliseconds)
                socks = dict(
                    self.poller.poll(timeout=100)
                )  # This will return {socket: event}

                if self.receiver in socks and socks[self.receiver] == zmq.POLLIN:
                    raw_message = self.receiver.recv_multipart()
                    if not raw_message:
                        # If no message received within the timeout, continue the loop
                        break
                    # Topic to pierwszy element wiadomości
                    topic = raw_message[0].decode()  # Decode topic
                    # Message data to drugi element wiadomości
                    message_data = raw_message[1]
                    # Ensure message data is not empty before attempting to parse
                    if not message_data:
                        logging.warning(f"Empty message data for topic: {topic}")
                        continue  # Skip processing this message
                    # Process based on topic
                    if topic == "ship":
                        msg = port.Ship()
                        try:
                            msg.ParseFromString(message_data)
                            logging.info("Received Ship message.")
                            print(msg)
                            self.recieved_ship_status(msg)
                            ack_request = self.ack_socket.recv_string()
                            if ack_request == "ACK_REQUEST":
                                self.ack_socket.send_string("ACK")
                                print("ACK sent.")
                        except Exception as e:
                            logging.error(
                                f"Error processing Ship message: {e}, topic: {topic}"
                            )
                    elif topic == "cart":
                        msg = port.Cart()
                        try:
                            msg.ParseFromString(message_data)
                            logging.info("Received Cart message.")
                            print(msg)
                            self.recieved_cart_status(msg)
                            ack_request = self.ack_socket.recv_string()
                            if ack_request == "ACK_REQUEST":
                                self.ack_socket.send_string("ACK")
                                print("ACK sent.")
                        except Exception as e:
                            logging.error(
                                f"Error processing Cart message: {e}, topic: {topic}"
                            )
                    elif topic == "crane":
                        msg = port.Crane()
                        try:
                            msg.ParseFromString(message_data)
                            logging.info("Received Crane message.")
                            print(msg)
                            self.recieved_crane_status(msg)
                            ack_request = self.ack_socket.recv_string()
                            if ack_request == "ACK_REQUEST":
                                self.ack_socket.send_string("ACK")
                                print("ACK sent.")
                        except Exception as e:
                            logging.error(
                                f"Error processing Crane message: {e}, topic: {topic}"
                            )
                    elif topic == "storage_yard":
                        msg = port.StorageYard()
                        try:
                            msg.ParseFromString(message_data)
                            logging.info("Received StorageYard message.")
                            print(msg)
                            self.recieved_storage_yard_status(msg)
                            ack_request = self.ack_socket.recv_string()
                            if ack_request == "ACK_REQUEST":
                                self.ack_socket.send_string("ACK")
                                print("ACK sent.")
                        except Exception as e:
                            logging.error(
                                f"Error processing StorageYard message: {e}, topic: {topic}"
                            )
                    elif topic == "transit_point":
                        msg = port.TransitPoint()
                        try:
                            msg.ParseFromString(message_data)
                            logging.info("Received TransitPoint message.")
                            print(msg)
                            self.recieved_transit_point_status(msg)
                            ack_request = self.ack_socket.recv_string()
                            if ack_request == "ACK_REQUEST":
                                self.ack_socket.send_string("ACK")
                                print("ACK sent.")

                        except Exception as e:
                            logging.error(
                                f"Error processing TransitPoint message: {e}, topic: {topic}"
                            )
                    else:
                        logging.warning(f"Unrecognized topic: {topic}")

            except Exception as e:
                logging.error(f"Error processing message: {e}", exc_info=True)

    def check_conditions_and_update(self):
        """This method will run in a separate thread to check conditions and perform updates."""
        while self.running:
            if (
                len(self.carts) == cfg.numberOfCarts
                and len(self.cranes) == cfg.numberOfCranes
                and len(self.transit_points) == 4
            ):
                self.update_containers_status()
                self.move_cart()
                self.check_port_status()
            else:
                # Log the current state when conditions aren't met
                logging.warning(
                    f"Current carts: {len(self.carts)} / {cfg.numberOfCarts}"
                )
                logging.warning(
                    f"Current cranes: {len(self.cranes)} / {cfg.numberOfCranes}"
                )
                logging.warning(
                    f"Current transit points: {len(self.transit_points)} / 4"
                )

            # Sleep for a while before checking again
            time.sleep(1)

    def run(self):
        gui_thread = threading.Thread(target=self.send_port_state, daemon=True)
        main_thread = threading.Thread(target=self.main_loop, daemon=True)
        # Start a new thread for checking conditions and performing updates
        update_thread = threading.Thread(
            target=self.check_conditions_and_update, daemon=True
        )
        gui_thread.start()
        update_thread.start()
        main_thread.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            logging.info("Simulation terminated.")


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
        elements.append({"cont_numb": cont_numb, "cont_target": cont_target * 2})

    # elements = []

    # for i in range(n):
    #     # Równomierne przypisanie identyfikatorów od 0 do n-1
    #     cont_numb = i + 1  # Indeksy zaczynają się od 1
    #     cont_target = cont_numb % target_mod  # Oblicz cel jako resztę z dzielenia

    #     elements.append({"cont_numb": cont_numb, "cont_target": cont_target})

    return elements


if __name__ == "__main__":
    controller = Controller()
    controller.run()
