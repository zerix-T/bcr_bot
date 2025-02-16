#! /usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy
from geometry_msgs.msg import Twist

class CmdVelRemapper(Node):
    def __init__(self):
        super().__init__('cmd_vel_remapper')

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=10
        )
        
        self.declare_parameter('vel_topic', 'bcr_bot/cmd_vel')

        # Create a subscriber for the cmd_vel topic
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            qos_profile
        )
        self.subscription  # Prevent unused variable warning

        # Create a publisher for the bcr_bot/cmd_vel topic
        vel_topic = self.get_parameter('vel_topic').get_parameter_value().string_value
        self.publisher = self.create_publisher(Twist, vel_topic, qos_profile)

    def cmd_vel_callback(self, msg):
        # Republish the received message to bcr_bot/cmd_vel
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)

    cmd_vel_remapper = CmdVelRemapper()

    try:
        rclpy.spin(cmd_vel_remapper)
    except KeyboardInterrupt:
        pass
    finally:
        cmd_vel_remapper.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

