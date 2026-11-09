import cv2
import numpy as np

# Load templates
tmpl_dir = '/home/steve/dev/ros2_exmaple/turtlebot3_autorace/turtlebot3_autorace_detect/image/'
signs = ['intersection', 'right', 'construction', 'parking', 'stop', 'tunnel']

cards = []
for s in signs:
    path = f"{tmpl_dir}/{s}.png"
    img = cv2.imread(path)
    if img is None:
        continue
    img = cv2.resize(img, (180, 180))
    # Add border
    img = cv2.copyMakeBorder(img, 40, 20, 20, 20, cv2.BORDER_CONSTANT, value=(24, 24, 24))
    # Add sign label
    cv2.putText(img, s.upper(), (25, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)
    # Add simulated yellow bounding box around the sign graphic
    cv2.rectangle(img, (18, 38), (200, 200), (0, 255, 255), 2)
    cards.append(img)

# Combine into 2 rows of 3
row1 = np.hstack(cards[:3])
row2 = np.hstack(cards[3:])
grid = np.vstack([row1, row2])

# Add master header
h, w = grid.shape[:2]
header = np.zeros((70, w, 3), dtype=np.uint8)
header[:] = (15, 18, 22)
cv2.putText(header, "AutoRace 2020: Traffic Sign SIFT Templates & Yellow Bounding Boxes", (30, 45),
            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (240, 240, 240), 2, cv2.LINE_AA)
final_banner = np.vstack([header, grid])

cv2.imwrite('/home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/traffic_signs_overview.png', final_banner)
print("Saved /home/steve/dev/ros2_exmaple/turtlebot3_autorace/docs/media/traffic_signs_overview.png")
