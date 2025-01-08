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


class WorldSimulator:
    def __init__(self, publisher_ip="localhost", publisher_port="5555"):
        self.zmq_context = zmq.Context()
        self.publisher = self.zmq_context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://{publisher_ip}:{publisher_port}")  # Use bind()

    # async def send_message(self, message):
    #     """
    #     Sends a serialized Protobuf message with a topic.
    #     """
    #     topic = type(message).__name__  # Use the message type as the topic
    #     await self.publisher.send_multipart(
    #         [topic.encode(), message.SerializeToString()]
    #     )

    def generate_ship_message(self):
        """
        Generate and send a Ship message.
        """
        ship = port.Ship()
        ship.isInPort = rnd.choice([True, False])
        ship.remainingContainersNo = (
            int(rnd.random() * cfg.containers_capacities[5]) if ship.isInPort else 0
        )
        # await self.send_message(ship)
        self.publisher.send(ship.SerializeToString())
        logging.info(f"Sent Ship message: {ship}")

    # async def generate_crane_message(self):
    #     """
    #     Generate and send a Crane message.
    #     """
    #     # for i in range(cfg.numberOfCranes):
    #     #     crane = port.Crane()
    #     #     crane.name = f"CRANE_{i}"  # TODO
    #     #     crane.isReady = True
    #     #     await self.send_message(crane)
    #     #     logging.info(f"Sent Crane message: {crane}")
    #     crane = port.Crane()
    #     crane.isReady = True
    #     crane.name = "CRANE_0"
    #     await self.send_message(crane)
    #     logging.info(f"Sent Crane message: {crane}")

    # async def generate_cart_message(self):
    #     """
    #     Generate and send a Cart message.
    #     """
    #     for i in range(cfg.numberOfCarts):
    #         cart = port.Cart()
    #         cart.name = f"CART_{i}"
    #         cart.withContainer = False
    #         cart.cartPos = int(rnd.random() * 15)
    #         cart.targetID = PortPositions.SHIP_WAITIMG.value
    #         await self.publisher.send(cart.SerializeToString())
    #         logging.info(f"Sent Cart message: {cart}")

    # async def generate_transit_point_message(self):
    #     """
    #     Generate and send a TransitPoint message.
    #     """
    #     transit_point = port.TransitPoint()
    #     transit_point.ID = rnd.random.choice(list(port.TransitPoint.Port_ID.values()))
    #     transit_point.containersNo = rnd.random.randint(0, 50)
    #     await self.send_message(transit_point)
    #     logging.info(f"Sent TransitPoint message: {transit_point}")

    # async def generate_storage_yard_message(self):
    #     """
    #     Generate and send a StorageYard message.
    #     """
    #     storage_yard = port.StorageYard()
    #     storage_yard.containersNo = rnd.random.randint(0, 500)
    #     await self.send_message(storage_yard)
    #     logging.info(f"Sent StorageYard message: {storage_yard}")

    def simulate(self):
        """
        Main simulation loop.
        Periodically sends rnd.randomized messages to simulate world behavior.
        """
        while True:
            try:
                # # rnd.randomly pick a message type to send
                # message_type = rnd.choice(
                #     [
                #         self.generate_ship_message,
                #         self.generate_crane_message,
                #         self.generate_cart_message,
                #         # self.generate_transit_point_message,
                #         # self.generate_storage_yard_message,
                #     ]
                # )

                # await message_type()  # Generate and send the selected message
                # await asyncio.sleep(rnd.uniform(0.5, 2))  # rnd.random delay
                self.generate_ship_message()  # Test with sending Crane messages
                import time
                time.sleep(2)
                # asyncio.sleep(2)  # Adjust sleep as needed
            except Exception as e:
                logging.error(f"Error during simulation: {e}", exc_info=True)


if __name__ == "__main__":
    simulator = WorldSimulator()

    try:
        (simulator.simulate())
    except KeyboardInterrupt:
        logging.info("Simulation terminated.")
