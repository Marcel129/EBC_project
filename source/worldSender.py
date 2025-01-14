import asyncio
import logging
import random as rnd
import time

import config as cfg
import port_data_pb2 as port  # Your generated Protobuf definitions
import zmq
import zmq.asyncio
from controller import PortPositions

# Configure logging
logging.basicConfig(level=logging.WARNING)

CRANE_DELAY = 1  # seconds
SHIP_DELAY = 5  # seconds

transitPointsIDs = [
    port.TransitPoint.Port_ID.AFRICA,
    port.TransitPoint.Port_ID.EUROPA,
    port.TransitPoint.Port_ID.ASIA,
    port.TransitPoint.Port_ID.AMERICA,
]


class WorldSimulator:
    def __init__(self, publisher_ip="localhost", publisher_port="5555"):
        # publisher to controller
        self.zmq_context = zmq.Context()
        self.publisher = self.zmq_context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://{publisher_ip}:{publisher_port}")  # Use bind()
        # receiver from controller
        self.receiver_IPaddress = "localhost"
        self.receiver_port = "2000"
        self.receiver = self.zmq_context.socket(zmq.SUB)
        self.receiver.connect(f"tcp://{self.receiver_IPaddress}:{self.receiver_port}")
        self.receiver.setsockopt(zmq.SUBSCRIBE, b"")

        # Receiver Socket for ACKs (REQ)
        self.ack_receiver = self.zmq_context.socket(zmq.REQ)
        self.ack_receiver.connect(
            "tcp://127.0.0.1:5556"
        )  # Connect to subscriber's ACK endpoi

        # ACK Socket (REP)
        self.ack_socket = self.zmq_context.socket(zmq.REP)
        self.ack_socket.bind("tcp://127.0.0.1:5560")  # Listen for ACK requests

        self.ship = port.Ship()
        self.cranes = []
        self.carts = []
        self.storage_yard = port.StorageYard()
        self.transit_points = []
        self.init_world()

        # flags for generating messages
        self.ship_message_flag = True
        self.carts_message_flag = [True for __ in range(cfg.numberOfCarts)]
        self.cranes_message_flag = [True for __ in range(cfg.numberOfCranes)]
        self.transit_point_flag = [True for __ in range(4)]
        self.storage_yard_flag = True

        self.ship_delay = SHIP_DELAY
        self.cranes_delays = [CRANE_DELAY for __ in range(cfg.numberOfCranes)]

    def init_world(self):

        self.ship.isInPort = True
        # self.ship.remainingContainersNo = rnd.randint(0, cfg.containers_capacities[-1])
        self.ship.remainingContainersNo = 20

        for i in range(cfg.numberOfCarts):
            cart = port.Cart()
            cart.name = f"CART_{i+1}"
            cart.withContainer = False
            cart.cartPos = PortPositions.SHIP_WAITIMG.value
            cart.targetID = PortPositions.SHIP_WAITIMG.value
            self.carts.append(cart)

        for id in transitPointsIDs:
            transit_point = port.TransitPoint()
            transit_point.ID = id
            # print(f"id: {transit_point.ID}")
            transit_point.containersNo = 0
            self.transit_points.append(transit_point)

        for i in range(cfg.numberOfCranes):
            crane = port.Crane()
            crane.name = f"CRANE_{i+1}"
            crane.isReady = True
            print(crane)
            self.cranes.append(crane)

        self.storage_yard.containersNo = 0

    def send_ack(self, poller, timeout_ms=100):
        """
        Sends an acknowledgment request and waits for the acknowledgment.
        """
        try:
            # Send ACK request if the socket is ready
            if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
                self.ack_receiver.send_string("ACK_REQUEST")

            # Poll for acknowledgment with a timeout
            if poller.poll(timeout_ms):  # Timeout in milliseconds
                ack = self.ack_receiver.recv_string()
                if ack == "ACK":
                    return True
                else:
                    logging.warning(f"Unexpected ACK response: {ack}")
                    return False
            else:
                logging.warning("ACK timeout.")
                return False
        except zmq.ZMQError as e:
            logging.error(f"ZMQ error during acknowledgment: {e}")
            return False
        except Exception as e:
            logging.error(f"Error sending/receiving acknowledgment: {e}")
            return False

    def generate_ship_message(self):
        """
        Generate and send a Ship message.
        """
        topic = "ship"
        try:
            self.publisher.send_multipart(
                [topic.encode(), self.ship.SerializeToString()]
            )
            logging.info(f"Sent Ship message: {self.ship}")

            poller = zmq.Poller()
            poller.register(self.ack_receiver, zmq.POLLIN)

            # Wait for ACK response
            if self.send_ack(poller):
                self.ship_message_flag = False
                logging.info("ACK received for Ship")
            else:
                logging.warning("ACK timeout for Ship")

        except Exception as e:
            logging.error(f"Error generating Ship message: {e}")

    def generate_crane_message(self):
        """
        Generate and send a Crane message.
        """
        for i, crane in enumerate(self.cranes):
            if self.cranes_message_flag[i]:
                topic = "crane"
                try:
                    self.publisher.send_multipart(
                        [topic.encode(), crane.SerializeToString()]
                    )
                    logging.info(f"Sent Crane message: {crane}")

                    poller = zmq.Poller()
                    poller.register(self.ack_receiver, zmq.POLLIN)

                    # Wait for ACK response
                    if self.send_ack(poller):
                        self.cranes_message_flag[i] = False
                        logging.info(f"ACK received for Crane {crane}")
                    else:
                        logging.warning(f"ACK timeout for Crane {crane}")

                except Exception as e:
                    logging.error(f"Error generating Crane message: {e}")

    def generate_cart_message(self):
        """
        Generate and send a Cart message.
        """
        for i, cart in enumerate(self.carts):
            if self.carts_message_flag[i]:
                topic = "cart"
                try:
                    self.publisher.send_multipart(
                        [topic.encode(), cart.SerializeToString()]
                    )
                    logging.info(f"Sent Cart message: {cart}")

                    poller = zmq.Poller()
                    poller.register(self.ack_receiver, zmq.POLLIN)

                    # Wait for ACK response
                    if self.send_ack(poller):
                        self.carts_message_flag[i] = False
                        logging.info(f"ACK received for Cart {cart}")
                    else:
                        logging.warning(f"ACK timeout for Cart {cart}")

                except Exception as e:
                    logging.error(f"Error generating Cart message: {e}")

    def generate_transit_point_message(self):
        """
        Generate and send a TransitPoint message.
        """
        for i, transit_point in enumerate(self.transit_points):
            if self.transit_point_flag[i]:
                topic = "transit_point"
                try:
                    self.publisher.send_multipart(
                        [topic.encode(), transit_point.SerializeToString()]
                    )
                    logging.info(f"Sent TransitPoint message: {transit_point}")

                    poller = zmq.Poller()
                    poller.register(self.ack_receiver, zmq.POLLIN)

                    # Wait for ACK response
                    if self.send_ack(poller):
                        self.transit_point_flag[i] = False
                        logging.info(f"ACK received for TransitPoint {transit_point}")
                    else:
                        logging.warning(f"ACK timeout for TransitPoint {transit_point}")

                except Exception as e:
                    logging.error(f"Error generating TransitPoint message: {e}")

    def generate_storage_yard_message(self):
        """
        Generate and send a StorageYard message.
        """
        topic = "storage_yard"
        try:
            self.publisher.send_multipart(
                [topic.encode(), self.storage_yard.SerializeToString()]
            )
            logging.info(f"Sent StorageYard message: {self.storage_yard}")

            poller = zmq.Poller()
            poller.register(self.ack_receiver, zmq.POLLIN)

            # Wait for ACK response
            if self.send_ack(poller):
                self.storage_yard_flag = False
                logging.info("ACK received for StorageYard")
            else:
                logging.warning("ACK timeout for StorageYard")

        except Exception as e:
            logging.error(f"Error generating StorageYard message: {e}")

    def process_message(self):
        try:
            raw_message = self.receiver.recv_multipart()
            topic = raw_message[0].decode()
            message_data = raw_message[1]

            # Ensure message data is not empty before attempting to parse
            if not message_data:
                logging.warning(f"Empty message data for topic: {topic}")
                return

            if topic == "ship" 
            #and self.ship_message_flag == False:
                msg = port.Ship()
                try:
                    msg.ParseFromString(message_data)
                    self.ship.isInPort = msg.isInPort
                    self.ship.remainingContainersNo = msg.remainingContainersNo
                    logging.info("Received Ship message.")
                    self.send_ack(zmq.Poller())
                except Exception as e:
                    logging.error(f"Error processing Ship message: {e}")

            elif topic == "cart":
                msg = port.Cart()
                try:
                    msg.ParseFromString(message_data)
                    for cart in self.carts:
                        if cart.name == msg.name:
                            cart.withContainer = msg.withContainer
                            cart.cartPos = msg.cartPos
                            cart.targetID = msg.targetID
                            logging.info(f"Updated Cart: {cart.name}")
                            self.send_ack(zmq.Poller())
                            break
                    else:
                        logging.warning(f"Cart with name {msg.name} not found.")
                except Exception as e:
                    logging.error(f"Error processing Cart message: {e}")

            elif topic == "crane":
                msg = port.Crane()
                try:
                    msg.ParseFromString(message_data)
                    for i, crane in enumerate(self.cranes):
                        if (
                            crane.name
                            == msg.name
                            # and self.cranes_message_flag[i] == False
                        ):
                            crane.isReady = msg.isReady
                            logging.info(f"Updated Crane: {crane.name}")
                            self.send_ack(zmq.Poller())
                            break
                    else:
                        logging.warning(f"Crane with name {msg.name} not found.")
                except Exception as e:
                    logging.error(f"Error processing Crane message: {e}")

            elif topic == "storage_yard":
                msg = port.StorageYard()
                try:
                    msg.ParseFromString(message_data)
                    self.storage_yard.containersNo = msg.containersNo
                    logging.info("Received StorageYard message.")
                    self.send_ack(zmq.Poller())
                except Exception as e:
                    logging.error(f"Error processing StorageYard message: {e}")

            elif topic == "transit_point":
                msg = port.TransitPoint()
                try:
                    msg.ParseFromString(message_data)
                    for transit_point in self.transit_points:
                        if transit_point.ID == msg.ID:
                            transit_point.containersNo = msg.containersNo
                            logging.info(f"Updated TransitPoint: {transit_point.ID}")
                            self.send_ack(zmq.Poller())
                            break
                    else:
                        logging.warning(f"TransitPoint with ID {msg.ID} not found.")
                except Exception as e:
                    logging.error(f"Error processing TransitPoint message: {e}")

            else:
                logging.warning(f"Unknown topic: {topic}")

        except Exception as e:
            logging.error(f"Error processing message: {e}", exc_info=True)

    # def generate_ship_message(self):
    #     """
    #     Generate and send a Ship message.
    #     """
    #     # Send the serialized message with the topic
    #     topic = "ship"
    #     # Send topic and message as a multipart message
    #     self.publisher.send_multipart([topic.encode(), self.ship.SerializeToString()])
    #     logging.info(f"Sent Ship message: {self.ship}")

    #     # Poller for acknowledgment
    #     poller = zmq.Poller()
    #     poller.register(self.ack_receiver, zmq.POLLIN)

    #     # Send ACK_REQUEST if the socket is ready for sending
    #     if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
    #         self.ack_receiver.send_string("ACK_REQUEST")

    #     # Poll for acknowledgment
    #     if poller.poll(1000):  # Timeout in milliseconds
    #         ack = self.ack_receiver.recv_string()
    #         if ack == "ACK":
    #             self.ship_message_flag = False
    #             logging.info("ACK received for Ship")
    #     else:
    #         logging.warning("ACK timeout for Ship")

    #     # # Wait for acknowledgment
    #     # self.ack_receiver.send_string("ACK_REQUEST")
    #     # ack = self.ack_receiver.recv_string()
    #     # if ack == "ACK":
    #     #     self.ship_message_flag = False
    #     #     print(f"ACK received for")

    # def generate_crane_message(self):
    #     """
    #     Generate and send a Crane message.
    #     """
    #     # for i in range(cfg.numberOfCranes):
    #     #     crane = port.Crane()
    #     #     crane.name = f"CRANE_{i}"  # TODO
    #     #     crane.isReady = True
    #     #     topic = "crane"
    #     #     self.publisher.send_multipart([topic.encode(), crane.SerializeToString()])
    #     #     # self.publisher.send(crane.SerializeToString())
    #     #     logging.info(f"Sent Crane message: {crane}")
    #     for i, crane in enumerate(self.cranes):
    #         if self.cranes_message_flag[i] == True:
    #             topic = "crane"
    #             self.publisher.send_multipart(
    #                 [topic.encode(), crane.SerializeToString()]
    #             )
    #             # self.publisher.send(crane.SerializeToString())
    #             logging.info(f"Sent Crane message: {crane}")

    #             # # Wait for acknowledgment
    #             # self.ack_receiver.send_string("ACK_REQUEST")
    #             # ack = self.ack_receiver.recv_string()
    #             # if ack == "ACK":
    #             #     self.cranes_message_flag[i] = False
    #             #     print(f"ACK received for")
    #             # Use a separate socket to send ACK requests
    #             # Use poller to wait for acknowledgment
    #             poller = zmq.Poller()
    #             poller.register(self.ack_receiver, zmq.POLLIN)

    #             # Send ACK_REQUEST if the socket is ready for sending
    #             if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
    #                 self.ack_receiver.send_string("ACK_REQUEST")

    #             # Poll for acknowledgment
    #             if poller.poll(1000):  # Timeout in milliseconds
    #                 ack = self.ack_receiver.recv_string()
    #                 if ack == "ACK":
    #                     self.cranes_message_flag[i] = False
    #                     logging.info(f"ACK received for crane {crane}")
    #             else:
    #                 logging.warning(f"ACK timeout for crane {crane}")

    # def generate_cart_message(self):
    #     """
    #     Generate and send a Cart message.
    #     """
    #     # for i in range(cfg.numberOfCarts):
    #     #     cart = port.Cart()
    #     #     cart.name = f"CART_{i}"
    #     #     cart.withContainer = False
    #     #     cart.cartPos = int(rnd.random() * 15)
    #     #     cart.targetID = PortPositions.SHIP_WAITIMG.value
    #     #     # self.publisher.send(cart.SerializeToString())
    #     #     topic = "cart"
    #     #     self.publisher.send_multipart([topic.encode(), cart.SerializeToString()])
    #     #     logging.info(f"Sent Cart message: {cart}")

    #     for i, cart in enumerate(self.carts):
    #         if self.carts_message_flag[i] == True:
    #             topic = "cart"
    #             self.publisher.send_multipart(
    #                 [topic.encode(), cart.SerializeToString()]
    #             )
    #             # self.publisher.send(crane.SerializeToString())
    #             logging.info(f"Sent Cart message: {cart}")
    #             # # Wait for acknowledgment
    #             # self.ack_receiver.send_string("ACK_REQUEST")
    #             # ack = self.ack_receiver.recv_string()
    #             # if ack == "ACK":
    #             #     self.carts_message_flag[i] = False
    #             #     print(f"ACK received for")

    #             # Poller for acknowledgment
    #             poller = zmq.Poller()
    #             poller.register(self.ack_receiver, zmq.POLLIN)

    #             # Send ACK_REQUEST if the socket is ready for sending
    #             if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
    #                 self.ack_receiver.send_string("ACK_REQUEST")

    #             # Poll for acknowledgment
    #             if poller.poll(1000):  # Timeout in milliseconds
    #                 ack = self.ack_receiver.recv_string()
    #                 if ack == "ACK":
    #                     self.carts_message_flag[i] = False
    #                     logging.info(f"ACK received for Cart {cart}")
    #             else:
    #                 logging.warning(f"ACK timeout for Cart {cart}")

    # def generate_transit_point_message(self):
    #     """
    #     Generate and send a TransitPoint message.
    #     """
    #     # for id in transitPointsIDs:
    #     #     transit_point = port.TransitPoint()
    #     #     transit_point.ID = id
    #     #     transit_point.containersNo = 0
    #     #     # self.publisher.send(transit_point.SerializeToString())
    #     #     topic = "transit_point"
    #     #     self.publisher.send_multipart([topic.encode(), transit_point.SerializeToString()])
    #     #     logging.info(f"Sent TransitPoint message: {transit_point}")

    #     for i, transit_point in enumerate(self.transit_points):
    #         if self.transit_point_flag[i] == True:
    #             topic = "transit_point"
    #             self.publisher.send_multipart(
    #                 [topic.encode(), transit_point.SerializeToString()]
    #             )
    #             # self.publisher.send(crane.SerializeToString())
    #             logging.info(f"Sent TransitPoint message: {transit_point}")

    #             # # Wait for acknowledgment
    #             # self.ack_receiver.send_string("ACK_REQUEST")
    #             # ack = self.ack_receiver.recv_string()
    #             # if ack == "ACK":
    #             #     self.transit_point_flag[i] = False
    #             #     print(f"ACK received for")

    #             # Poller for acknowledgment
    #             poller = zmq.Poller()
    #             poller.register(self.ack_receiver, zmq.POLLIN)

    #             # Send ACK_REQUEST if the socket is ready for sending
    #             if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
    #                 self.ack_receiver.send_string("ACK_REQUEST")

    #             # Poll for acknowledgment
    #             if poller.poll(1000):  # Timeout in milliseconds
    #                 ack = self.ack_receiver.recv_string()
    #                 if ack == "ACK":
    #                     self.transit_point_flag[i] = False
    #                     logging.info(f"ACK received for TransitPoint {transit_point}")
    #             else:
    #                 logging.warning(f"ACK timeout for TransitPoint {transit_point}")

    # def generate_storage_yard_message(self):
    #     """
    #     Generate and send a StorageYard message.
    #     """
    #     # storage_yard = port.StorageYard()
    #     # storage_yard.containersNo = rnd.randint(0, 500)
    #     # # self.publisher.send(storage_yard.SerializeToString())
    #     topic = "storage_yard"
    #     self.publisher.send_multipart(
    #         [topic.encode(), self.storage_yard.SerializeToString()]
    #     )
    #     logging.info(f"Sent StorageYard message: {self.storage_yard}")

    #     # # Wait for acknowledgment
    #     # self.ack_receiver.send_string("ACK_REQUEST")
    #     # ack = self.ack_receiver.recv_string()
    #     # if ack == "ACK":
    #     #     self.storage_yard_flag = False
    #     #     print(f"ACK received for")

    #     # Poller for acknowledgment
    #     poller = zmq.Poller()
    #     poller.register(self.ack_receiver, zmq.POLLIN)

    #     # Send ACK_REQUEST if the socket is ready for sending
    #     if self.ack_receiver.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
    #         self.ack_receiver.send_string("ACK_REQUEST")

    #     # Poll for acknowledgment
    #     if poller.poll(1000):  # Timeout in milliseconds
    #         ack = self.ack_receiver.recv_string()
    #         if ack == "ACK":
    #             self.storage_yard_flag = False
    #             logging.info("ACK received for StorageYard")
    #     else:
    #         logging.warning("ACK timeout for StorageYard")

    # def process_message(self):
    #     try:
    #         raw_message = self.receiver.recv_multipart()
    #         # Topic to pierwszy element wiadomości
    #         topic = raw_message[0].decode()  # Decode topic
    #         # Message data to drugi element wiadomości
    #         message_data = raw_message[1]
    #         # Ensure message data is not empty before attempting to parse
    #         if not message_data:
    #             logging.warning(f"Empty message data for topic: {topic}")
    #         else:
    #             # Process based on topic
    #             if topic == "ship":
    #                 msg = port.Ship()
    #                 try:
    #                     msg.ParseFromString(message_data)
    #                     self.ship.isInPort = msg.isInPort
    #                     self.ship.remainingContainersNo = msg.remainingContainersNo
    #                     logging.info("Received Ship message.")
    #                     ack_request = self.ack_socket.recv_string()
    #                     if ack_request == "ACK_REQUEST":
    #                         self.ack_socket.send_string("ACK")
    #                         print("ACK sent.")
    #                 except Exception as e:
    #                     logging.error(
    #                         f"Error processing Ship message: {e}, topic: {topic}"
    #                     )
    #             elif topic == "cart":
    #                 msg = port.Cart()
    #                 try:
    #                     msg.ParseFromString(message_data)
    #                     for cart in self.carts:
    #                         if cart.name == msg.name:
    #                             cart.withContainer = msg.withContainer
    #                             cart.cartPos = msg.cartPos
    #                             cart.targetID = msg.targetID
    #                             logging.info(f"Updated Cart: {cart.name}")
    #                             ack_request = self.ack_socket.recv_string()
    #                             if ack_request == "ACK_REQUEST":
    #                                 self.ack_socket.send_string("ACK")
    #                                 print("ACK sent.")
    #                             break
    #                     else:
    #                         logging.warning(f"Cart with name {msg.name} not found.")
    #                 except Exception as e:
    #                     logging.error(
    #                         f"Error processing Cart message: {e}, topic: {topic}"
    #                     )
    #             elif topic == "crane":
    #                 msg = port.Crane()
    #                 try:
    #                     msg.ParseFromString(message_data)
    #                     for crane in self.cranes:
    #                         if crane.name == msg.name:
    #                             crane.isReady = msg.isReady
    #                             logging.info(f"Updated Crane: {crane.name}")
    #                             ack_request = self.ack_socket.recv_string()
    #                             if ack_request == "ACK_REQUEST":
    #                                 self.ack_socket.send_string("ACK")
    #                                 print("ACK sent.")
    #                             break
    #                     else:
    #                         logging.warning(f"Crane with name {msg.name} not found.")
    #                 except Exception as e:
    #                     logging.error(
    #                         f"Error processing Crane message: {e}, topic: {topic}"
    #                     )
    #             elif topic == "storage_yard":
    #                 msg = port.StorageYard()
    #                 try:
    #                     msg.ParseFromString(message_data)
    #                     self.storage_yard.containersNo = msg.containersNo
    #                     logging.info("Received StorageYard message.")
    #                     ack_request = self.ack_socket.recv_string()
    #                     if ack_request == "ACK_REQUEST":
    #                         self.ack_socket.send_string("ACK")
    #                         print("ACK sent.")
    #                 except Exception as e:
    #                     logging.error(
    #                         f"Error processing StorageYard message: {e}, topic: {topic}"
    #                     )
    #             elif topic == "transit_point":
    #                 msg = port.TransitPoint()
    #                 try:
    #                     msg.ParseFromString(message_data)
    #                     for transit_point in self.transit_points:
    #                         if transit_point.ID == msg.ID:
    #                             transit_point.containersNo = msg.containersNo
    #                             logging.info(f"Updated Cart: {transit_point.ID}")
    #                             ack_request = self.ack_socket.recv_string()
    #                             if ack_request == "ACK_REQUEST":
    #                                 self.ack_socket.send_string("ACK")
    #                                 print("ACK sent.")
    #                             break
    #                     else:
    #                         logging.warning(f"Cart with name {msg.ID} not found.")
    #                 except Exception as e:
    #                     logging.error(
    #                         f"Error processing TransitPoint message: {e}, topic: {topic}"
    #                     )
    #             else:
    #                 pass
    #     except Exception as e:
    #         logging.error(f"Error processing message: {e}", exc_info=True)

    # def generate_messages(self):
    #     if self.ship_message_flag:
    #         self.generate_ship_message()
    #         self.ship_message_flag = False
    #     if self.storage_yard_flag:
    #         self.generate_storage_yard_message()
    #         self.storage_yard_flag = False
    #     if self.transit_point_flag:
    #         self.generate_transit_point_message()
    #         self.transit_point_flag = False
    #     if self.carts_message_flag:
    #         self.generate_cart_message()
    #         self.carts_message_flag = False
    #     if self.cranes_message_flag:
    #         self.generate_crane_message()
    #         self.cranes_message_flag = False

    def generate_messages(self):
        """
        Generate and send messages for various topics, ensuring acknowledgment before resetting flags.
        """

        # In the generate_messages method
        if self.ship_message_flag:
            self.generate_ship_message()
        if self.storage_yard_flag:
            self.generate_storage_yard_message()
        if self.transit_point_flag:
            self.generate_transit_point_message()
        if any(self.cranes_message_flag):  # Check if any crane requires a message
            self.generate_crane_message()
        if any(self.carts_message_flag):  # Check if any cart requires a message
            self.generate_cart_message()

    def process_events(self):
        # while not self.ship.isInPort:
        if not self.ship.isInPort:
            self.ship_delay -= 1
            print(f"Ship delay: {self.ship_delay}")
            if self.ship_delay <= 0:
                self.ship.isInPort = True
                self.ship.remainingContainersNo = rnd.randint(
                    20, cfg.containers_capacities[-1]
                )
                self.ship_message_flag = True
                self.ship_delay = SHIP_DELAY

        for crane in self.cranes:
            number = int(crane.name.split("_")[1]) - 1
            if not crane.isReady:
                print(f"Crane {number+1}")
                print(self.cranes_delays[number])
                print("")
                self.cranes_delays[number] -= 1
                if self.cranes_delays[number] <= 0:
                    crane.isReady = True  # Mark the crane as ready
                    self.cranes_message_flag[number] = (
                        True  # Set the corresponding message flag
                    )
                    self.cranes_delays[number] = CRANE_DELAY
            # while not crane.isReady:
            #     self.cranes_delays[number] -= 1
            #     if self.cranes_delays[number] <= 0:
            #         crane.isReady = True
            #         self.cranes_message_flag = True

    def simulate(self):
        """
        Main simulation loop.
        Periodically sends rnd.randomized messages to simulate world behavior.
        """

        while True:
            try:
                self.process_message()
                self.process_events()
                # for _ in range(5):
                #     # if self.ship_message_flag:
                #     self.generate_ship_message()
                #     self.ship_message_flag = False
                #     # if self.storage_yard_flag:
                #     self.generate_storage_yard_message()
                #     self.storage_yard_flag = False
                #     # if self.transit_point_flag:
                #     self.generate_transit_point_message()
                #     self.transit_point_flag = False
                #     # if self.carts_message_flag:
                #     self.generate_cart_message()
                #     self.carts_message_flag = False
                #     # if self.cranes_message_flag:
                #     self.generate_crane_message()
                #     self.cranes_message_flag = False
                self.generate_messages()
            except Exception as e:
                logging.error(f"Error during simulation: {e}", exc_info=True)


if __name__ == "__main__":
    simulator = WorldSimulator()

    try:
        (simulator.simulate())
    except KeyboardInterrupt:
        logging.info("Simulation terminated.")
