import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, Pose
from nav_msgs.msg import Odometry, Path, OccupancyGrid
from map_msgs.msg import OccupancyGridUpdate
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class MultiAMRManager(Node):
    def __init__(self):
        super().__init__('multi_amr_manager')

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Publishers for aggregated pose, path, and map data
        self.poses_publisher = self.create_publisher(PoseArray, '/all_amrs/poses', 10)
        self.paths_publisher = self.create_publisher(Path, '/all_amrs/paths', 10)
        self.map_publisher = self.create_publisher(OccupancyGrid, '/all_amrs/map', 10)

        # Data storage
        self.robot_poses = {}  # Stores latest pose of each robot
        self.robot_paths = {}  # Stores latest path of each robot
        self.subscribed_robots = {}  # Tracks active subscriptions

        # Map storage
        self.global_map = None

        # Subscribe to known topics
        self.subscribe_robot("bcr_boto", "/bcr_boto/odom", "/plan", qos_profile)

        # Subscribe to map topics
        self.create_subscription(OccupancyGrid, "/map", self.map_callback, qos_profile)
        self.create_subscription(OccupancyGridUpdate, "/map_updates", self.map_update_callback, qos_profile)

        # Publish aggregated data at 10 Hz
        self.create_timer(0.1, self.publish_data)

    def subscribe_robot(self, robot_name, odom_topic, path_topic, qos_profile):
        """Subscribes to the given odometry and path topics of a robot."""
        if robot_name not in self.subscribed_robots:
            self.robot_poses[robot_name] = None
            self.robot_paths[robot_name] = None

            self.subscribed_robots[robot_name] = [
                self.create_subscription(Odometry, odom_topic, lambda msg, rn=robot_name: self.odom_callback(msg, rn), qos_profile),
                self.create_subscription(Path, path_topic, lambda msg, rn=robot_name: self.path_callback(msg, rn), qos_profile)
            ]
            self.get_logger().info(f"Subscribed to {robot_name} on {odom_topic} and {path_topic}")

    def odom_callback(self, msg, robot_name):
        """Extracts the pose from Odometry and stores it."""
        self.robot_poses[robot_name] = msg.pose.pose

    def path_callback(self, msg, robot_name):
        """Stores the received path."""
        self.robot_paths[robot_name] = msg

    def map_callback(self, msg):
        """Receives the static map and stores it."""
        self.global_map = msg
        self.get_logger().info("Received initial map.")

    def map_update_callback(self, msg):
        """Updates the stored map with new occupancy grid data."""
        if self.global_map is None:
            self.get_logger().warn("Received map update before global map was received.")
            return

        # Apply updates to the existing map
        index = msg.y * self.global_map.info.width + msg.x
        for i in range(msg.width * msg.height):
            self.global_map.data[index + i] = msg.data[i]

        self.get_logger().info("Updated map with new data.")

    def publish_data(self):
        """Publishes aggregated pose, path, and map data."""
        pose_array_msg = PoseArray()
        pose_array_msg.header.stamp = self.get_clock().now().to_msg()
        pose_array_msg.header.frame_id = 'map'

        for pose in self.robot_poses.values():
            if pose:
                pose_array_msg.poses.append(pose)

        self.poses_publisher.publish(pose_array_msg)

        path_msg = Path()
        path_msg.header.stamp = self.get_clock().now().to_msg()
        path_msg.header.frame_id = 'map'

        for path in self.robot_paths.values():
            if path:
                path_msg.poses.extend(path.poses)

        self.paths_publisher.publish(path_msg)

        # Publish the stored map
        if self.global_map:
            self.map_publisher.publish(self.global_map)

def main(args=None):
    rclpy.init(args=args)
    node = MultiAMRManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
