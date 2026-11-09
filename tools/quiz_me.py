#!/usr/bin/env python3
"""
Interactive Oral Defense Self-Quiz CLI for TurtleBot3 AutoRace 2020.
Prompts you with questions from docs/STUDY_AND_ORAL_DEFENSE_GUIDE.md
to test your mastery and technical readiness.
"""

import random
import sys

QUESTIONS = [
    {
        "q": "What is the fundamental architectural difference between ROS 1 and ROS 2?",
        "options": [
            "A) ROS 1 has no launch files, while ROS 2 does.",
            "B) ROS 1 requires a central roscore master, whereas ROS 2 uses decentralized peer-to-peer DDS discovery.",
            "C) ROS 2 only runs on Windows, while ROS 1 only runs on Linux.",
            "D) ROS 2 does not use topics or messages."
        ],
        "answer": "B",
        "explanation": "ROS 1 relies on a single roscore master process (single point of failure). ROS 2 is built on DDS (Data Distribution Service) which provides peer-to-peer discovery without any central master."
    },
    {
        "q": "Why does the mission_supervisor act as the single publisher to /cmd_vel instead of individual detector nodes?",
        "options": [
            "A) Because ROS 2 only permits one topic per computer.",
            "B) To obey the Single-Writer Principle; competing /cmd_vel publishers cause motor command collision and wheel jitter.",
            "C) Because detector nodes cannot run fast enough to send motor commands.",
            "D) To save network bandwidth."
        ],
        "answer": "B",
        "explanation": "If multiple nodes publish to /cmd_vel simultaneously, their velocity commands interleave unpredictably, causing severe motor shaking. The supervisor arbitrates all driving states."
    },
    {
        "q": "What is Inverse Perspective Mapping (IPM)?",
        "options": [
            "A) Inverting the colors of an image to detect dark objects.",
            "B) Warping perspective camera frames into an orthographic bird's-eye view so parallel lanes stay parallel.",
            "C) Rotating the robot wheels in reverse.",
            "D) Calculating the 3D depth of laser beams."
        ],
        "answer": "B",
        "explanation": "IPM applies a geometric homography projection that eliminates perspective convergence (vanishing points), allowing accurate polynomial curve fitting on track lanes."
    },
    {
        "q": "Why is HSV color space used instead of RGB for lane marking detection?",
        "options": [
            "A) HSV has fewer bits per pixel than RGB.",
            "B) In HSV, chromatic Hue is separated from illumination (Value), making detection robust against lighting variations.",
            "C) Gazebo does not support RGB cameras.",
            "D) OpenCV cannot process RGB images."
        ],
        "answer": "B",
        "explanation": "In RGB, shadows and glares change R, G, and B simultaneously. In HSV, Hue stays constant across illumination shifts, ensuring clean segmentation of white and yellow lanes."
    },
    {
        "q": "How does Lowe's Ratio Test filter feature matches in SIFT sign recognition?",
        "options": [
            "A) By discarding any match where the best distance d1 >= 0.78 * d2 (second-best distance).",
            "B) By deleting 78% of the image pixels at random.",
            "C) By checking if the sign has more than 78 keypoints.",
            "D) By measuring the distance to the sign using LiDAR."
        ],
        "answer": "A",
        "explanation": "Lowe's ratio test (d1 < 0.78 * d2) verifies that the best feature match is significantly closer than the second best, rejecting ambiguous background and repetitive texture matches."
    },
    {
        "q": "How was the camera detection modified to show ONLY a clean yellow box around traffic signs without internal dots and lines?",
        "options": [
            "A) By blurring the sign image with a Gaussian filter.",
            "B) By suppressing cv2.drawMatches() and using cv2.perspectiveTransform(corners, M) with cv2.polylines().",
            "C) By drawing a yellow square in the center of the camera frame regardless of detection.",
            "D) By deleting all keypoints from the template image."
        ],
        "answer": "B",
        "explanation": "We removed cv2.drawMatches() which drew messy connecting lines and keypoint dots, and instead projected only the 4 template corners via the RANSAC homography matrix using cv2.polylines()."
    },
    {
        "q": "What mathematical formula converts 2D Euler Yaw (theta) from a Quaternion (x, y, z, w)?",
        "options": [
            "A) theta = x + y + z + w",
            "B) theta = atan2(2 * (w*z + x*y), 1 - 2 * (y^2 + z^2))",
            "C) theta = cos(w) / sin(z)",
            "D) theta = sqrt(x^2 + y^2 + z^2)"
        ],
        "answer": "B",
        "explanation": "This standard robotics transformation computes the planar rotation angle about the Z-axis (yaw) from 3D unit quaternions."
    },
    {
        "q": "What is the Pure Pursuit curvature formula used to steer the robot toward a waypoint?",
        "options": [
            "A) kappa = 2 * sin(alpha) / Ld",
            "B) kappa = Ld * cos(alpha)",
            "C) kappa = alpha / (2 * Ld)",
            "D) kappa = v^2 / R"
        ],
        "answer": "A",
        "explanation": "In Pure Pursuit, target path curvature is kappa = 2*sin(alpha)/Ld, where alpha is the angular error to the lookahead point and Ld is lookahead distance. Then omega = v * kappa."
    },
    {
        "q": "How does the robot detect and wait for the moving Level-Crossing barrier arm?",
        "options": [
            "A) By asking a human operator over WiFi.",
            "B) By monitoring the front LiDAR cone (+-15 deg) within 0.45m; if blocked it stops, and resumes once range > 0.80m.",
            "C) By honking the robot horn until the gate moves.",
            "D) By using GPS signals."
        ],
        "answer": "B",
        "explanation": "When approaching the railway crossing (-0.80, 1.26), the supervisor checks the forward LiDAR ranges. If range < 0.45m it halts, and resumes when the barrier raises above 0.80m."
    },
    {
        "q": "What command runs the automated headless verification regression test?",
        "options": [
            "A) ./run.sh verify",
            "B) ./run.sh status",
            "C) ./run.sh stop",
            "D) ./run.sh clean-docker"
        ],
        "answer": "A",
        "explanation": "./run.sh verify executes tools/verify_full_course.py in headless Gazebo, asserting STATE=done within 150 seconds."
    }
]

def main():
    print("\n" + "=" * 65)
    print(" 🎓 TURTLEBOT3 AUTORACE 2020: ORAL DEFENSE SELF-QUIZ")
    print("=" * 65)
    print("Test your technical recall and prepare for interviews / presentations.")
    print("Answer each question by typing A, B, C, or D (or 'q' to quit).\n")

    score = 0
    shuffled = list(QUESTIONS)
    random.shuffle(shuffled)

    for idx, item in enumerate(shuffled, 1):
        print(f"\n[Question {idx}/{len(shuffled)}]")
        print(item["q"])
        print("-" * 55)
        for opt in item["options"]:
            print(f"  {opt}")
        
        while True:
            choice = input("\nYour answer (A/B/C/D): ").strip().upper()
            if choice == 'Q':
                print("\nQuiz exited early.")
                sys.exit(0)
            if choice in ['A', 'B', 'C', 'D']:
                break
            print("Invalid input. Please enter A, B, C, or D.")

        if choice == item["answer"]:
            print("✅ CORRECT!")
            score += 1
        else:
            print(f"❌ INCORRECT. The correct answer was: {item['answer']}")
        
        print(f"💡 Explanation: {item['explanation']}")

    print("\n" + "=" * 65)
    percentage = (score / len(shuffled)) * 100
    print(f"🏁 QUIZ COMPLETE: Score {score}/{len(shuffled)} ({percentage:.1f}%)")
    if percentage >= 90:
        print("🌟 Outstanding! You are fully prepared for technical oral defense.")
    elif percentage >= 70:
        print("👍 Good job! Review docs/STUDY_AND_ORAL_DEFENSE_GUIDE.md to master the missed areas.")
    else:
        print("📖 Keep studying! Re-read BEGINNER_GUIDE.md and STUDY_AND_ORAL_DEFENSE_GUIDE.md.")
    print("=" * 65 + "\n")

if __name__ == '__main__':
    main()
