import os
import cv2
import sys
import torch

import numpy as np
from typing import Union
from tfrecord.torch.dataset import TFRecordDataset

from os.path import join as ospj
sys.path.append(ospj(".", 'src'))



class ThreeDPWTFRecordDataset():
    """ General dataset class for tfrecord based files.
    """
    def __init__(
        self, 
        data_path: str, 
        n_scenes=5, 
        person_id=0, 
        subsample: int=1, 
        history_window: int=5, 
        future_window: int=5, 
        batch_size: int=10,
        resize: Union[tuple, list, None] = None, 
        shuffle: bool=False, 
        n_workers: int=0, 
        prefetch_factor: int=None
        ) -> None:  
        """Wrapper on top of tfrecord.torch.dataset.TFRecordDataset

        Args:
            data_path (str): Path to the <name>.tfrecord file.
            n_scenes (int, optional): Number of scenes. Defaults to 5.
            person_id (int, optional): Index for a person in case of multiple. Use to ensure single person scenerio. Defaults to 0.
            subsample (int, optional): Subsampling factor. E.g. if 2, then take every 2nd frame. Defaults to 1.
            history_window (int, optional): A window representing the maximum context history. Defaults to 5.
            future_window (int, optional): A window for maximum peek into the future. Defaults to 5.
            batch_size (int, optional): A batch of windowed representation of history and future data. Defaults to 10.
            shuffle (bool, optional): True to shuffle the batches. It will not affect the window ordering. Defaults to False.
            n_workers (int, optional): Define number of workers for dataloading. Defaults to 0.
            prefetch_factor (int, optional): Number of batches to prefetch by each worker. Defaults to None.
        """
        
        feature_description = {
            "sequence": "byte", 
            'height': "int", # int
            'width': "int", # int
            'frames': "int", # int
            'image_raw': "byte", # np.uint8
            'pmask': "byte", # np.uint8
            'norm_poses': "byte", # np.float32
            'root_joints': "byte", # np.int32
            'abs_poses': "byte", # np.int32
        }
        
        self.history_window = history_window
        self.future_window = future_window
        self.person_id = person_id
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.prefetch_factor = prefetch_factor
        self.subsample = subsample
        self.resize = resize
        
        self.n_scenes = n_scenes
        self.n_workers = n_workers
        
        self.dataset = TFRecordDataset(data_path, None, feature_description, transform=self._parse, )
        
        self.history_data_list = []
        self.future_data_list = []
        
        self._cache()
        
    def _parse(self, features):
        """ Parse the tfrecord according to the feature description for TFRecordDataset. 
            Each feature represents a complete video sequence of a single scene.

        Args:
            features (list): A list of raw features stored in the tfrecord file.

        Returns:
            int: Number of frames.
            str: Jpeg encoded image string.
            numpy.ndarray: Mask for the padding.
            numpy.ndarray: Normalized poses .
            numpy.ndarray: Root joints.
        """
        flatten_image = np.frombuffer(features["image_raw"], dtype=np.uint8)
        flatten_mask = np.frombuffer(features["pmask"], dtype=np.uint8)
        flatten_norm_pose = np.frombuffer(features["norm_poses"], dtype=np.float32)
        flatten_root_joint = np.frombuffer(features["root_joints"], dtype=np.int32)

        image_strings = np.reshape(flatten_image, (features["frames"][0], -1))
        mask = np.reshape(flatten_mask, (features["height"][0], features["width"][0], -1))

        norm_pose = np.reshape(flatten_norm_pose, (-1, features["frames"][0], 18, 3))
        root_joint = np.reshape(flatten_root_joint, (-1, features["frames"][0], 3))    
        
        if self.resize is not None:
            mask = self.resize_mask(mask)
            root_joint = self.resize_root(root_joint, (features["height"][0], features["width"][0], 3))

        return features["frames"][0], image_strings, mask, norm_pose, root_joint

    def _cache(self):
        """ Cache the dataset containing jpeg encoded image strings for memory efficiency.
        """
        self.windowed_data_list = []
        num = 0
        
        # Iterate over each scene
        for scene_data in self.dataset:
            num += 1
            
            # Generate windowed representation by adding an extra dimension 
            history, future = self._window(scene_data)
            
            self.history_data_list.extend(history)
            self.future_data_list.extend(future)
            
            # Beak if number of scenes exceeds the defined number of scenes
            if num >= self.n_scenes:
                break 
    
    def _window(self, data):
        """ Generate a rolling window for history and future sequences 
            based on the history and future window size, and the subsampling factor for a single scene.

        Args:
            data (typle(int, list(str), numpy.ndarray, numpy.ndarray, numpy.ndarray)): 
                An input list of [frames, image_strings, mask, norm_pose, root_joint] to be windowed. 

        Returns:
            history (list(numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray)): 
                A list of historical windowed items i.e. [image_strings, norm_poses, root_joints, mask]
            future (list(numpy.ndarray, numpy.ndarray, )): 
                A list of future windowed items i.e. [norm_poses, root_joints]
        """
        # Get complete data for a single scene
        frames, image_strings, mask, norm_pose, root_joint = data
        sub_frames = frames // self.subsample
        idx = np.linspace(0, frames-1, sub_frames).astype(int)
        image_strings = image_strings[idx]
        norm_pose = norm_pose[:, idx, :, :]
        root_joint = root_joint[:, idx, :]
        # Define number of windowed data for a single scene
        num = sub_frames - self.history_window - self.future_window + 1
        
        # Make sure in case of 1 visible person, the id does not exceed it.
        person_id = self.person_id if self.person_id < norm_pose.shape[0] else norm_pose.shape[0] - 1   
        
        history = []
        future = []
        
        # Convert the complete data into windowed representation
        for i in range(0, num):
            start = i
            end = self.history_window + start
            history.append([image_strings[start:end], norm_pose[person_id, start:end, :, :], root_joint[person_id, start:end, :], mask])

            start = end
            end = self.future_window + start
            future.append([image_strings[start:end], norm_pose[person_id, start:end, :, :], root_joint[person_id, start:end, :], mask])

        return history, future
    
    def __len__(self):
        """Get length of the dataset as the number of windowed data.

        Returns:
            int: Length of windowed dataset.
        """
        
        return len(self.history_data_list)
    
    def decode_jpeg(self, string):
        """ Decode jpeg encoded image string/bytes into numpy.ndarray in cv2 format

        Args:
            string (str): A string of encoded bytes representing jpeg encoding for an image.

        Returns:
            numpy.ndarray: A decoded image in cv2 BGR format.
        """
        
        return cv2.imdecode(np.frombuffer(string, dtype=np.uint8), -1)
    
    def resize_img(self, img):

        return cv2.resize(img, self.resize[:2][::-1])
    
    # def resize_pose(self, pose, shape):
    #     """Resize pose.

    #     Args:
    #         root (numpy.ndarray): A (np, N, 18, 3) numpy array.

    #     Returns:
    #         numpy.ndarray: A (np, N, 18, 3) rescaled pose with np number of people.
    #     """
    #     factor = np.array(self.resize) / np.array(shape)
    #     rescaled_pose = pose*np.tile(np.expand_dims([*factor[:2][::-1], factor[2]], axis=(0, 1, 2)), (1, pose.shape[1], pose.shape[2], 1))

    #     return rescaled_pose.astype(int)
    
    def resize_mask(self, mask):
        """Resize mask.

        Args:
            mask (numpy.ndarray): A (N, W, H) numpy array.

        Returns:
            numpy.ndarray: A (N, W', H') resized mask.
        """
        return  cv2.resize(mask, self.resize[:2][::-1], interpolation=cv2.INTER_NEAREST)

    def resize_root(self, root, shape):
        """Resize root.
        Args:
            img (numpy.ndarray): A (N, W, H, 3) numpy array.
            root (numpy.ndarray): A (np, N, 3) numpy array.

        Returns:
            numpy.ndarray: A (np, N, 3) rescaled pose with np number of people.
        """
        factor = np.array(self.resize) / np.array(shape)
        rescaled_pose = root*np.tile(np.expand_dims([*factor[:2][::-1], factor[2]], axis=(0,1)), (1, root.shape[1], 1))

        return rescaled_pose.astype(int)
    
    def __getitem__(self, index):
        """ Get a single item representing a windowed history and future

        Args:
            index (int): Index the dataset.

        Returns:
            history (list(numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray)):  
                Output representing history [image, norm_poses, root_joints, mask].
            future (list(numpy.ndarray, numpy.ndarray)): 
                Output representing future [norm_poses, root_joints].
        """
        img_list = []

        # Get a single windowed example from history
        img_strings, norm_poses, root_joints, mask = self.history_data_list[index]
        
        # Decode the jpeg encoded image string
        for string in img_strings:
            img = self.decode_jpeg(string)
            
            if self.resize is not None:
                img = self.resize_img(img)
                
            img_list.append(img)
 
        imgs = np.array(img_list)
        history = [imgs, norm_poses, root_joints, mask]  
        
        img_list = []
        _, norm_poses, root_joints, mask = self.future_data_list[index]
        
        # Not need during training or inferencing (Only for verifying the sequence consitency)
        # for string in img_strings:
        #     img_list.append(self.decode_jpeg(img_string))
        #
        # imgs = np.array(img_list)
        # future = [imgs, norm_poses, root_joints, mask]  
        
        future = [norm_poses, root_joints]  
        
        return history, future
    
    def get_loader(self):
        """Wrap current dataset class with torch.utils.data.DataLoader. 

        Returns:
            torch.utils.data.DataLoader: An instance of torch.utils.data.DataLoader
        """
        
        return torch.utils.data.DataLoader(self, batch_size=self.batch_size, shuffle=self.shuffle, num_workers=self.n_workers, prefetch_factor=self.prefetch_factor)
