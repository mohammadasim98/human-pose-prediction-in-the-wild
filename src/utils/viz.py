import os
import cv2

import numpy as np

from builtins import range
from math import sqrt, ceil
import matplotlib.pyplot as plt

from utils.transforms import cvt_absolute_pose


CONNECTIONS_2D = [
    [0, 1], #0
    [1, 2], #1
    [1, 5], #2
    [2, 3], #3
    [3, 4], #4
    [5, 6], #5
    [6, 7], #6
    [2, 8], #7
    [8, 9], #8
    [8, 11], #9
    [9, 10], #10
    [5, 11], #11
    [11, 12], #12
    [12, 13] #13
]

CONNECTIONS_3D = [
    [15, 12],
    [9, 12],
    [13, 9],
    [14, 9],
    [16, 13],
    [17, 14],
    [18, 16],
    [19, 17],
    [20, 18],
    [21, 19],
    [23, 21],
    [20, 22],
    [9, 6],
    [6, 3],
    [3, 0],
    [1, 0],
    [2, 0],
    [4, 1],
    [5, 2],
    [5, 8],
    [4, 7],
    [7, 10],
    [8, 11]

]
def annotate_root_2d(img, root=None, color=(0, 0, 255), radius=5, thickness=1, text=False):
    """Annotate the given image with given the root joint 

    Args:
        img (numpy.ndarray): An input image
        root (numpy.ndarray, optional): An (np, 3) root joints with np as the number of people. Defaults to None.


    Returns:
        numpy.ndarray: An annotated image. 
    """
    
    #########################################################################
    # TODO: Draw root joint                                                 
    #  1. Root joint can be improved to make it more representable e.g.,    
    #  adding links between joints etc.                                     
    #########################################################################
        
    for human_id in range(root.shape[0]):
              
        if root is not None:
            if text:
                cv2.putText(img, "ROOT", root[human_id, :2].astype(int) + np.array([0, 20]), \
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness, cv2.LINE_AA)

            cv2.circle(img, root[human_id, :2].astype(int), radius, color, thickness)

          
        
    return img


def annotate_pose_2d(img, pose=None, color=(255, 0, 0), radius=5, thickness=1, text=False):
    """Annotate the given image with absolute pose-keypoints.

    Args:
        img (numpy.ndarray): An input image
        pose (numpy.ndarray, optional): An (np, 18, 3) root-relative poses with np as the number of people. Defaults to None.


    Returns:
        numpy.ndarray: An annotated image. 
    """
    
    
    #########################################################################
    # TODO: Draw absolute pose                                              
    #  1. Pose keypoints can be improved to make it more representable      
    #  e.g., adding links between joints etc.                               
    #########################################################################
        
    for human_id in range(pose.shape[0]):
        if pose is not None:
            for k in range(1, pose.shape[1]):
                if pose[human_id,  k, 0] == 0 and pose[human_id,  k, 1] == 0:
                    continue
                
                if text:
                    cv2.putText(img, str(k), pose[human_id,  k, :2] + np.array([0, 20]), \
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, [0, 0, 255], 1, cv2.LINE_AA)
                
                cv2.circle(img, pose[human_id,  k, :2].tolist(), radius, color, thickness)
                
        for conn in CONNECTIONS_2D:
            start = pose[human_id, conn[0], :2]
            end = pose[human_id, conn[1], :2]
            if (start[0] == 0 and start[1] == 0) or (end[0] == 0 and end[1] == 0):
                continue
            cv2.line(img, start, end, color=color, thickness=thickness) 
    return img

def vizualize_3d(ax, fig, pose_3d=None, trans=None):
    ax.cla()
    if trans is not None:
        ax.scatter(trans[0], trans[1], trans[2])
    

    
    if pose_3d is not None:
        for connection in CONNECTIONS_3D:
            start = connection[0]
            end = connection[1]
            line_x = [pose_3d[start, 0], pose_3d[end, 0]]                 
            line_y = [pose_3d[start, 1], pose_3d[end, 1]]                 
            line_z = [pose_3d[start, 2], pose_3d[end, 2]]                 
            ax.plot(line_x, line_y, zs=line_z, figure=fig, linewidth=2)
    ax.axes.set_xlim3d(left=-3, right=3)
    ax.axes.set_ylim3d(bottom=-3, top=3) 
    ax.axes.set_zlim3d(bottom=-3, top=3)    
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    plt.draw()

def visualize_tfrecord_dataloader(loader, viz_3d: bool=True):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    fig.show()
    for i, (history, future) in enumerate(loader):
        for sample in range((history[0].shape)[0]):
            img = history[0][sample][0].numpy()
            abs_pose = history[1][sample][0].numpy()
            root_joint = history[2][sample][0].numpy() 
            mask = history[3][sample].numpy()
            pose_3d = history[4][sample][0].numpy()
            trans_3d = history[5][sample][0].numpy()
            
            print(root_joint)
            abs_pose = np.expand_dims(abs_pose, axis=0).astype(int)
            # abs_pose = cvt_absolute_pose(root_joint=np.expand_dims(root_joint, 0), norm_pose=np.expand_dims(norm_pose, 0))
            annoted_img = annotate_pose_2d(img=img, pose=abs_pose, color=(255, 0, 0), radius=2, thickness=2, text=False)
            annoted_img = annotate_root_2d(img=annoted_img, root=np.expand_dims(root_joint, 0), color=(0, 0, 255), thickness=3)
            cv2.imshow("History Image", img)
            cv2.imshow("History Mask", mask*255)
            
            abs_pose = future[0][sample][0].numpy()
            abs_pose = np.expand_dims(abs_pose, axis=0).astype(int)
            root_joint = future[1][sample][0].numpy()
            # abs_pose = cvt_absolute_pose(root_joint=np.expand_dims(root_joint, 0), norm_pose=np.expand_dims(norm_pose, 0))
            annoted_img = annotate_pose_2d(img=img, pose=abs_pose, color=(0, 255, 0), radius=2, thickness=2, text=False)
            annoted_img = annotate_root_2d(img=annoted_img,root=np.expand_dims(root_joint, 0), color=(0, 255, 255), thickness=3)
            cv2.imshow("Future Image", img)
            cv2.imshow("Future Mask", mask*255)
            
            if viz_3d:
                vizualize_3d(ax, fig, pose_3d, trans_3d)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break     
        if cv2.waitKey(25) & 0xFF == ord('q'):
                break
    cv2.destroyAllWindows()

# Useful functions from the excercies

def visualize_grid(Xs, ubound=255.0, padding=1):
    """
    Reshape a 4D tensor of image data to a grid for easy visualization.

    Inputs:
    - Xs: Data of shape (N, H, W, C)
    - ubound: Output grid will have values scaled to the range [0, ubound]
    - padding: The number of blank pixels between elements of the grid
    """
    (N, H, W, C) = Xs.shape
    grid_size = int(ceil(sqrt(N)))
    grid_height = H * grid_size + padding * (grid_size - 1)
    grid_width = W * grid_size + padding * (grid_size - 1)
    grid = np.zeros((grid_height, grid_width, C))
    next_idx = 0
    y0, y1 = 0, H
    for y in range(grid_size):
        x0, x1 = 0, W
        for x in range(grid_size):
            if next_idx < N:
                img = Xs[next_idx]
                low, high = np.min(img), np.max(img)
                grid[y0:y1, x0:x1] = ubound * (img - low) / (high - low)
                # grid[y0:y1, x0:x1] = Xs[next_idx]
                next_idx += 1
            x0 += W + padding
            x1 += W + padding
        y0 += H + padding
        y1 += H + padding
    # grid_max = np.max(grid)
    # grid_min = np.min(grid)
    # grid = ubound * (grid - grid_min) / (grid_max - grid_min)
    return grid

def vis_grid(Xs):
    """ visualize a grid of images """
    (N, H, W, C) = Xs.shape
    A = int(ceil(sqrt(N)))
    G = np.ones((A*H+A, A*W+A, C), Xs.dtype)
    G *= np.min(Xs)
    n = 0
    for y in range(A):
        for x in range(A):
            if n < N:
                G[y*H+y:(y+1)*H+y, x*W+x:(x+1)*W+x, :] = Xs[n,:,:,:]
                n += 1
    # normalize to [0,1]
    maxg = G.max()
    ming = G.min()
    G = (G - ming)/(maxg-ming)
    return G

def vis_nn(rows):
    """ visualize array of arrays of images """
    N = len(rows)
    D = len(rows[0])
    H,W,C = rows[0][0].shape
    Xs = rows[0][0]
    G = np.ones((N*H+N, D*W+D, C), Xs.dtype)
    for y in range(N):
        for x in range(D):
            G[y*H+y:(y+1)*H+y, x*W+x:(x+1)*W+x, :] = rows[y][x]
    # normalize to [0,1]
    maxg = G.max()
    ming = G.min()
    G = (G - ming)/(maxg-ming)
    return G





