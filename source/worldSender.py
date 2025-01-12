import asyncio
import logging
import random as rnd

import config as cfg
import port_data_pb2 as port  # Your generated Protobuf definitions
import zmq
import zmq.asyncio
from controller import PortPositions

# Configure logging
logging.basicConfig(level=logging.INFO)

transitPointsIDs = [
    port.TransitPoint.Port_ID.AFRICA,
    port.TransitPoint.Port_ID.EUROPA,
    port.TransitPoint.Port_ID.ASIA,
    port.TransitPoint.Port_ID.AMERICA,
]

class WorldSimulator:
    def __init__(self, publisher_ip="localhost", publisher_port="5555"):
        #publisher to controller
        self.zmq_context = zmq.Context()
        self.publisher = self.zmq_context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://{publisher_ip}:{publisher_port}")  # Use bind()
        #receiver from controller
        self.receiver_IPaddress = "localhost"
        self.receiver_port = "2000"
        self.receiver = self.zmq_context.socket(zmq.SUB)
        self.receiver.connect(f"tcp://{self.receiver_IPaddress}:{self.receiver_port}")
        self.receiver.setsockopt(zmq.SUBSCRIBE, b"")

        self.ship = port.Ship()
        self.cranes = []
        self.carts = []
        self.storage_yard = port.StorageYard()
        self.transit_points = []
        self.init_world()

        #flags for generating messages
        self.ship_message_flag = True
        self.carts_message_flag = True
        self.cranes_message_flag = True
        self.transit_points_flag = True
        self.storage_yard_flag = True

        self.ship_delay = 1000
        self.cranes_delays = [1000 for __ in range(6)]

    def init_world(self):

        self.ship.isInPort = True
        self.ship.remainingContainersNo = rnd.randint(0, cfg.containers_capacities[-1])

        for i in range(cfg.numberOfCarts):
            cart = port.Cart()
            cart.name = f"CART_{i}"
            cart.withContainer = False
            cart.cartPos = PortPositions.SHIP_WAITIMG.value
            cart.targetID = PortPositions.SHIP_WAITIMG.value
            self.carts.append(cart)
        
        for id in transitPointsIDs:
            transit_point = port.TransitPoint()
            transit_point.ID = id
            transit_point.containersNo = 0
            self.transit_points.append(transit_point)
        
        for i in range(cfg.numberOfCranes):
            crane = port.Crane()
            crane.name = f"CRANE_{i}"
            crane.isReady = True
            self.cranes.append(crane)
        
        self.storage_yard.containersNo = 0

    def generate_ship_message(self):
        """
        Generate and send a Ship message.
        """
        # Send the serialized message with the topic
        topic = "ship"
        # Send topic and message as a multipart message
        self.publisher.send_multipart([topic.encode(), self.ship.SerializeToString()])
        logging.info(f"Sent Ship message: {self.ship}")


    def generate_crane_message(self):
        """
        Generate and send a Crane message.
        """
        # for i in range(cfg.numberOfCranes):
        #     crane = port.Crane()
        #     crane.name = f"CRANE_{i}"  # TODO
        #     crane.isReady = True
        #     topic = "crane"
        #     self.publisher.send_multipart([topic.encode(), crane.SerializeToString()])
        #     # self.publisher.send(crane.SerializeToString())
        #     logging.info(f"Sent Crane message: {crane}")
        
        for crane in self.cranes:
            topic = "crane"
            self.publisher.send_multipart([topic.encode(), crane.SerializeToString()])
            # self.publisher.send(crane.SerializeToString())
            logging.info(f"Sent Crane message: {crane}")


    def generate_cart_message(self):
        """
        Generate and send a Cart message.
        """
        # for i in range(cfg.numberOfCarts):
        #     cart = port.Cart()
        #     cart.name = f"CART_{i}"
        #     cart.withContainer = False
        #     cart.cartPos = int(rnd.random() * 15)
        #     cart.targetID = PortPositions.SHIP_WAITIMG.value
        #     # self.publisher.send(cart.SerializeToString())
        #     topic = "cart"
        #     self.publisher.send_multipart([topic.encode(), cart.SerializeToString()])
        #     logging.info(f"Sent Cart message: {cart}")
        
        for cart in self.carts:
            topic = "cart"
            self.publisher.send_multipart([topic.encode(), cart.SerializeToString()])
            # self.publisher.send(crane.SerializeToString())
            logging.info(f"Sent Cart message: {cart}")

    def generate_transit_point_message(self):
        """
        Generate and send a TransitPoint message.
        """
        # for id in transitPointsIDs:
        #     transit_point = port.TransitPoint()
        #     transit_point.ID = id
        #     transit_point.containersNo = 0 
        #     # self.publisher.send(transit_point.SerializeToString())
        #     topic = "transit_point"
        #     self.publisher.send_multipart([topic.encode(), transit_point.SerializeToString()])
        #     logging.info(f"Sent TransitPoint message: {transit_point}")
        
        for transit_point in self.transit_points:
            topic = "transit_point"
            self.publisher.send_multipart([topic.encode(), transit_point.SerializeToString()])
            # self.publisher.send(crane.SerializeToString())
            logging.info(f"Sent TransitPoint message: {transit_point}")

    def generate_storage_yard_message(self):
        """
        Generate and send a StorageYard message.
        """
        # storage_yard = port.StorageYard()
        # storage_yard.containersNo = rnd.randint(0, 500)
        # # self.publisher.send(storage_yard.SerializeToString())
        topic = "storage_yard"
        self.publisher.send_multipart([topic.encode(), self.storage_yard.SerializeToString()])
        logging.info(f"Sent StorageYard message: {self.storage_yard}")
 
    def process_message(self):
            try:
                raw_message = self.receiver.recv_multipart()
                # Topic to pierwszy element wiadomości
                topic = raw_message[0].decode()  # Decode topic
                # Message data to drugi element wiadomości
                message_data = raw_message[1]
                # Ensure message data is not empty before attempting to parse
                if not message_data:
                    logging.warning(f"Empty message data for topic: {topic}")
                else:
                    # Process based on topic
                    if topic == "ship":
                        msg = port.Ship()
                        try:
                            msg.ParseFromString(message_data)
                            self.ship.isInPort = msg.isInPort
                            self.ship.remainingContainersNo = msg.remainingContainersNo
                            logging.info("Received Ship message.")
                        except Exception as e:
                            logging.error(f"Error processing Ship message: {e}, topic: {topic}")
                    elif topic == "cart":
                        msg = port.Cart()
                        try:
                            msg.ParseFromString(message_data)
                            for transit_point in self.carts:
                                if transit_point.name == msg.name:
                                    transit_point.withContainer = msg.withContainer
                                    transit_point.cartPos = msg.cartPos
                                    transit_point.targetID = msg.targetID
                                    logging.info(f"Updated Cart: {transit_point.name}")
                                    break
                            else:
                                logging.warning(f"Cart with name {msg.name} not found.")
                        except Exception as e:
                            logging.error(f"Error processing Cart message: {e}, topic: {topic}")
                    elif topic == "crane":
                        msg = port.Crane()
                        try:
                            msg.ParseFromString(message_data)
                            for transit_point in self.cranes:
                                if transit_point.name == msg.name:
                                    transit_point.isReady = msg.isReady
                                    logging.info(f"Updated Crane: {transit_point.name}")
                                    break
                            else:
                                logging.warning(f"Crane with name {msg.name} not found.")
                        except Exception as e:
                            logging.error(f"Error processing Crane message: {e}, topic: {topic}")
                    elif topic == "storage_yard":
                        msg = port.StorageYard()
                        try:
                            msg.ParseFromString(message_data)
                            self.storage_yard.containersNo = msg.containersNo
                            logging.info("Received StorageYard message.")
                        except Exception as e:
                            logging.error(f"Error processing StorageYard message: {e}, topic: {topic}")
                    elif topic == "transit_point":
                        msg = port.TransitPoint()
                        try:
                            msg.ParseFromString(message_data)
                            for transit_point in self.transit_points:
                                if transit_point.ID == msg.ID:
                                    transit_point.containersNo = msg.containersNo
                                    logging.info(f"Updated Cart: {transit_point.ID}")
                                    break
                            else:
                                logging.warning(f"Cart with name {msg.ID} not found.")
                        except Exception as e:
                            logging.error(f"Error processing TransitPoint message: {e}, topic: {topic}")
                    else:
                        logging.warning(f"Unrecognized topic: {topic}")
            except Exception as e:
                logging.error(f"Error processing message: {e}", exc_info=True)


    def generate_messages(self):
        if self.ship_message_flag: 
            self.generate_ship_message() 
            self.ship_message_flag = False 
        if self.storage_yard_flag: 
            self.generate_storage_yard_message()
            self.storage_yard_flag = False   
        if self.transit_point_flag: 
            self.generate_transit_point_message()
            self.transit_point_flag = False   
        if self.carts_message_flag: 
            self.generate_cart_message() 
            self.carts_message_flag = False  
        if self.cranes_message_flag: 
            self.generate_crane_message()
            self.cranes_message_flag = False   
    
    def process_events(self):
        
        while not self.ship.isInPort:
            self.ship_delay-=1
            if self.ship_delay<=0:
                self.ship.isInPort = True
                self.ship_message_flag = True

        for crane in self.cranes:
            number = int(crane.name.split('_')[1])
            while not crane.isReady:
                self.cranes_delays[number]-=1
                if self.cranes_delays[number]<=0:
                    crane.isReady = True
                    self.cranes_message_flag = True

                
    def simulate(self):
        """
        Main simulation loop.
        Periodically sends rnd.randomized messages to simulate world behavior.
        """

        while True:
            try:
                self.process_message()
                self.process_events()
                self.generate_messages()
            except Exception as e:
                logging.error(f"Error during simulation: {e}", exc_info=True)


if __name__ == "__main__":
    simulator = WorldSimulator()

    try:
        (simulator.simulate())
    except KeyboardInterrupt:
        logging.info("Simulation terminated.")
