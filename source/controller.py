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

CRANE_1 = "SHIP_C1"  # UPPER
CRANE_2 = "SHIP_C2"  # LOWER
CRANE_3 = "SHIP_T1"  # AFRICA - EUROPA
CRANE_4 = "SHIP_T2"  # EUROPA - AMERICA
CRANE_5 = "SHIP_T3"  # AMERICA - ASIA
CRANE_6 = "SHIP_S1"

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
        # self.ship_inst = port.Ship()
        # self.cranes = [port.Crane() for _ in range(cfg.numberOfCranes)]
        # self.carts = [port.Cart() for __ in range(cfg.numberOfCarts)]
        # self.storage_yard = port.StorageYard()
        # self.transit_points = [port.TransitPoint for __ in range(4)]

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

    def recieved_crane_status(self, msg):

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
        tmp = [
            cart for cart in self.carts if cart["Position"] in position_set
        ]  # Check if cart in correct place
        tmp = [
            cart for cart in tmp if cart["Status"] != unload
        ]  # Check if it has an container
        if len(tmp) == 1 or len(tmp) == 2:
            cart_to_update = tmp[0]

            occupied_fields = [
                1 if any(cart["Position"] == position for cart in self.carts) else 0
                for position in PortPositions
            ]
            
            for cart in self.carts:
                
                if target_flag == "unload_ship":
                    if cart["Cart_name"] == cart_to_update["Cart_name"]:
                        cart["Status"] = unload  # Mark the cart as updated
                        cart["Target"] = self.containers[-1][
                            1
                        ]  # Set the Target from the last container's value
                        self.ship_remainingContainersNo -= 1
                        if occupied_fields[cart["Target"]]:
                            if not occupied_fields[(cart["Target"]+1)]:
                                cart["Position"] = cart["Target"]+1
                            elif not occupied_fields[PortPositions.ST_LP1]:    
                                cart["Position"] = PortPositions.ST_LP1.value
                            elif not occupied_fields[PortPositions.ST_LP2]:    
                                cart["Position"] = PortPositions.ST_LP2.value
                            elif not occupied_fields[PortPositions.ST_WAITING]:  
                                cart["Position"] = PortPositions.ST_WAITING.value
                        else:
                            cart["Position"] = cart["Target"]
                        break  # We found and updated the cart, no need to continue looping

                elif target_flag == "load_transit":
                    if cart["Cart_name"] == cart_to_update["Cart_name"]:
                        for existing_trans_point in self.transit_points:
                            if existing_trans_point["Port_ID"] == cart["Position"]:
                                cart["Status"] = unload  # Mark the cart as updated
                                existing_trans_point["containersNo"] += 1
                                if self.ship:
                                    cart["Target"] = PortPositions.SHIP_WAITIMG.value
                                else:
                                    cart["Target"] = PortPositions.ST_WAITING.value

                        break  # We found and updated the cart, no need to continue looping
                elif target_flag == "do_storage":
                    if cart["Cart_name"] == cart_to_update["Cart_name"]:
                        cart["Status"] = unload  # Mark the cart as updated
                        if unload == True:
                            self.storage_containers -= 1
                            cart["Target"] = self.storage_containers_info[-1][1]
                        else:
                            if self.ship:
                                cart["Target"] = PortPositions.SHIP_WAITIMG.value
                            else:
                                cart["Target"] = PortPositions.ST_WAITING.value
                            self.storage_containers += 1
                        break  # We found and updated the cart, no need to continue looping

            if self.containers and unload:
                self.containers.pop()
            if target_flag == "do_storage":
                if self.storage_containers and unload:
                    self.containers.pop()
                elif not unload:
                    self.storage_containers.append(
                        {"cont_numb": 0, "cont_target": cart_to_update["Target"]}
                    )

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

        unload_ship = "unload_ship"
        load_transit = "load_transit"
        do_storage = "do_storage"
        if crane_port_1:
            self.move_container({PortPositions.SHIP_LP1, PortPositions.SHIP_LP2}, True, unload_ship)
        if crane_port_2:
            self.move_container({PortPositions.SHIP_LP2, PortPositions.SHIP_LP3}, True, unload_ship)
        if crane_port_3:
            self.move_container(
                {PortPositions.AFRICA_LP, PortPositions.EUROPA_LP}, False, load_transit
            )
        if crane_port_4:
            self.move_container(
                {PortPositions.EUROPA_LP, PortPositions.AMERICA_LP}, False, load_transit
            )
        if crane_port_5:
            self.move_container(
                {PortPositions.AMERICA_LP, PortPositions.ASIA_LP}, False, load_transit
            )
        if (
            crane_port_6
            and self.ship
            and len(self.storage_containers) < cfg.containers_capacities[-2]
        ):
            self.move_container({PortPositions.ST_LP1, PortPositions.ST_LP2}, False, do_storage)
        elif crane_port_6 and not self.ship and len(self.containers) > 0:
            self.move_container({PortPositions.ST_LP1, PortPositions.ST_LP2}, True, do_storage)

    def move_cart(self):

        for cart in self.carts:

            occupied_fields = [
                1 if any(cart["Position"] == position for cart in self.carts) else 0
                for position in PortPositions
            ]

            if cart["Position"] != cart["Target"]:
                if occupied_fields[cart["Target"]]:
                    if not occupied_fields[(cart["Target"]+1)]:
                        cart["Position"] = cart["Target"]+1
                    elif not occupied_fields[PortPositions.ST_LP1]:    
                        cart["Position"] = PortPositions.ST_LP1.value
                    elif not occupied_fields[PortPositions.ST_LP2]:    
                        cart["Position"] = PortPositions.ST_LP2.value
                    elif not occupied_fields[PortPositions.ST_WAITING]:  
                        cart["Position"] = PortPositions.ST_WAITING.value
                else:
                    cart["Position"] = cart["Target"]


        for cart in self.carts:

            occupied_fields = [
                1 if any(cart["Position"] == position for cart in self.carts) else 0
                for position in PortPositions
            ]

            if (cart["Position"] == cart["Target"]) and cart["Position"] == (PortPositions.ST_WAITING.value or PortPositions.SHIP_WAITIMG.value):
                if cart["Position"] == PortPositions.ST_WAITING.value:
                    if not occupied_fields[PortPositions.ST_LP1.value]:
                        cart["Position"] = 


                    if not occupied_fields[(cart["Target"]+1)]:
                        cart["Position"] = cart["Target"]+1
                    elif not occupied_fields[PortPositions.ST_LP1]:    
                        cart["Position"] = PortPositions.ST_LP1.value
                    elif not occupied_fields[PortPositions.ST_LP2]:    
                        cart["Position"] = PortPositions.ST_LP2.value
                    elif not occupied_fields[PortPositions.ST_WAITING]:  
                        cart["Position"] = PortPositions.ST_WAITING.value
                else:
                    cart["Position"] = cart["Target"]
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
                return

        # If the cart does not exist, add a new one
        new_cart = port_state.carts.add()
        new_cart.name = cart_data["Cart_name"]
        new_cart.withContainer = cart_data["Status"]
        new_cart.cartPos = cart_data["Position"]
        new_cart.targetID = cart_data["Target"]
        logging.info(f"Added new cart {cart_data['Cart_name']} to PortState.")

    def generate_ship_message(self):
        """
        Generate and send a Ship message.
        """
        ship = port.Ship()
        ship.isInPort = self.ship
        ship.remainingContainersNo = self.ship_remainingContainersNo

        # Send the serialized message with the topic
        topic = "ship"
        # Send topic and message as a multipart message
        self.publisher.send_multipart(
            [topic.encode(), self.ship_inst.SerializeToString()]
        )
        logging.info(f"Sent Ship message: {ship}")

    def generate_crane_message(self):
        """
        Generate and send a Crane message.
        """
        for existing_crane in self.cranes:
            crane = port.Crane()
            crane.name = existing_crane["Crane_name"]
            crane.isReady = existing_crane["Status"]
            topic = "crane"
            self.publisher.send_multipart([topic.encode(), crane.SerializeToString()])
            logging.info(f"Sent Crane message: {crane}")

    def generate_cart_message(self):
        """
        Generate and send a Cart message.
        """
        for existing_cart in self.myPort.carts:
            cart = port.Cart()
            cart.name = existing_cart["Cart_name"]
            cart.withContainer = existing_cart["Status"]
            cart.cartPos = existing_cart.cartPos["Position"]
            cart.targetID = existing_cart.targetID["Target"]
            # self.publisher.send(cart.SerializeToString())
            topic = "cart"
            self.publisher.send_multipart([topic.encode(), cart.SerializeToString()])
            logging.info(f"Sent Cart message: {cart}")

    def generate_transit_point_message(self):
        """
        Generate and send a TransitPoint message.
        """
        for existing_trans_point in self.transit_points:
            transit_point = port.TransitPoint()
            transit_point.ID = existing_trans_point["Port_ID"]
            transit_point.containersNo = existing_trans_point["containersNo"]
            topic = "transit_point"
            self.publisher.send_multipart(
                [topic.encode(), transit_point.SerializeToString()]
            )
            logging.info(f"Sent TransitPoint message: {transit_point}")

    def generate_storage_yard_message(self):
        """
        Generate and send a StorageYard message.
        """
        storage_yard = port.StorageYard()
        storage_yard.containersNo = self.storage_containers
        # self.publisher.send(storage_yard.SerializeToString())
        topic = "storage_yard"
        self.publisher.send_multipart(
            [topic.encode(), storage_yard.SerializeToString()]
        )
        logging.info(f"Sent StorageYard message: {storage_yard}")

    def send_port_state(self):
        while self.running:
            # Serialize and send a Protobuf message
            self.myPort.ship.isInPort = self.ship
            self.myPort.ship.remainingContainersNo = self.ship_remainingContainersNo

            # Iterate through self.carts and add/update each cart
            for cart_data in self.carts:
                self.add_cart_to_port_state(self.myPort, cart_data)

            self.myPort.storageYard.containersNo = self.storage_containers

            for existing_trans_point in self.transit_points:
                new_point = self.myPort.transitPoints.add()
                new_point.ID = existing_trans_point["Port_ID"]
                new_point.containersNo = existing_trans_point["containersNo"]

            topic = "port_state"
            self.sender.send([topic.encode(), self.my_port.SerializeToString()])
            logging.info(f"PortState sent: {self.myPort}")
            time.sleep(1)

    def main_loop(self):
        """
        Main loop to process incoming messages of various types.
        Continuously listens for messages and processes them based on their expected type.
        """
        while self.running:
            try:

                raw_message = self.receiver.recv_multipart()
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
                    except Exception as e:
                        logging.error(
                            f"Error processing TransitPoint message: {e}, topic: {topic}"
                        )
                else:
                    logging.warning(f"Unrecognized topic: {topic}")
            except Exception as e:
                logging.error(f"Error processing message: {e}", exc_info=True)

    def run(self):
        gui_thread = threading.Thread(target=self.send_port_state, daemon=True)
        main_thread = threading.Thread(target=self.main_loop, daemon=True)

        gui_thread.start()
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
        elements.append({"cont_numb": cont_numb, "cont_target": cont_target})

    return elements


if __name__ == "__main__":
    controller = Controller()
    controller.run()
