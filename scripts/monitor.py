import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, PoseArray, Pose
from nav_msgs.msg import Path
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class MultiAMRPublisher(Node):
    def __init__(self):
        super().__init__('multi_amr_publisher')

        # QoS profile for subscribing to Nav2 topics
        self.qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.poses_publisher = self.create_publisher(PoseArray, '/all_amrs/poses', 10)
        self.paths_publisher = self.create_publisher(Path, '/all_amrs/paths', 10)

        self.robot_poses = {}  # Stores latest pose of each robot
        self.robot_paths = {}  # Stores latest path of each robot
        self.subscriptions = {}  # Tracks active subscriptions

        # Scan for new robots every 5 seconds
        self.create_timer(5.0, self.discover_robots)
        self.create_timer(0.5, self.publish_data)  # Publish data at 2Hz

    def discover_robots(self):
        """Scans for active AMRs by detecting pose and path topics."""
        topic_names_and_types = self.get_topic_names_and_types()
        detected_robots = set()

        for topic, types in topic_names_and_types:
            if 'geometry_msgs/msg/PoseStamped' in types and topic.endswith('/pose'):
                robot_name = topic.split('/')[1]
                detected_robots.add(robot_name)

                if robot_name not in self.subscriptions:
                    self.robot_poses[robot_name] = None
                    self.robot_paths[robot_name] = None

                    self.subscriptions[robot_name] = [
                        self.create_subscription(
                            PoseStamped, f'/{robot_name}/pose', lambda msg, rn=robot_name: self.pose_callback(msg, rn), self.qos_profile),
                        self.create_subscription(
                            Path, f'/{robot_name}/path', lambda msg, rn=robot_name: self.path_callback(msg, rn), self.qos_profile)
                    ]
                    self.get_logger().info(f"Subscribed to {robot_name}")

    def pose_callback(self, msg, robot_name):
        """Stores the latest pose of each robot."""
        self.robot_poses[robot_name] = msg.pose

    def path_callback(self, msg, robot_name):
        """Stores the latest path of each robot."""
        self.robot_paths[robot_name] = msg

    def publish_data(self):
        """Publishes collected poses and paths to aggregated topics."""
        pose_array_msg = PoseArray()
        pose_array_msg.header.stamp = self.get_clock().now().to_msg()
        pose_array_msg.header.frame_id = 'map'

        for pose in self.robot_poses.values():
            if pose:
                pose_array_msg.poses.append(pose)

        self.poses_publisher.publish(pose_array_msg)

        # Merge all paths into one message
        path_msg = Path()
        path_msg.header.stamp = self.get_clock().now().to_msg()
        path_msg.header.frame_id = 'map'

        for path in self.robot_paths.values():
            if path:
                path_msg.poses.extend(path.poses)

        self.paths_publisher.publish(path_msg)


def main(args=None):
    rclpy.init(args=args)
    node = MultiAMRPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
