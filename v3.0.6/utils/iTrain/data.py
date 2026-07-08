import h5py
import numpy as np
import torch
from torch.utils.data import Dataset
from tqdm import tqdm
import bisect
import sys


def _progress_enabled():
    # tqdm writes to stderr by default; disable bars when redirected to log files.
    return sys.stderr.isatty()


def _iter_with_progress(items, desc, unit="item"):
    if _progress_enabled():
        yield from tqdm(items, desc=desc, unit=unit, disable=False)
        return

    total = len(items)
    if total == 0:
        print(f"{desc}: no {unit}s to process", flush=True)
        return

    print(f"{desc}: 0/{total} {unit}s", flush=True)
    step = max(1, total // 10)
    for idx, item in enumerate(items, start=1):
        yield item
        if idx == 1 or idx % step == 0 or idx == total:
            print(f"{desc}: {idx}/{total} {unit}s", flush=True)

class H5Dataset(Dataset):
    def __init__(self, file_paths, feature_dataset_name='features', label_dataset_name='labels',
                 y_offset=0, regression=False, feature_transform=None, target_transform=None):
        """
        :param feature_dataset_name: Dataset name for features in HDF5 file
        :param label_dataset_name: Dataset name for labels in HDF5 file
        :param regression: If True, use raw labels for regression; if False, apply one-hot encoding for classification
        """
        self.regression = regression
        self.x_data, self.y_data = self.load_and_combine_h5_datasets(file_paths, feature_dataset_name,
                                                                     label_dataset_name, y_offset)
        self.feature_transform = feature_transform
        self.target_transform = target_transform

    def load_and_combine_h5_datasets(self, file_paths, feature_dataset_name, label_dataset_name, y_offset):
        x_data_list = []
        y_data_list = []
        for file_path in _iter_with_progress(file_paths, desc="Loading HDF5 files", unit="file"):
            with h5py.File(file_path, 'r') as file:
                features = file[feature_dataset_name][:]
                labels = file[label_dataset_name][:]
                # print(features)
                # x_data = features.reshape(-1, features.shape[1], 1)
                # print(x_data)
                # Adjust label dimensions as needed
                if not self.regression:
                    labels = labels - y_offset
                    labels = labels.astype(int)
                    # print(labels)

                x_data_list.append(features)
                y_data_list.append(labels)

        x_data_combined = np.concatenate(x_data_list, axis=0)
        y_data_combined = np.concatenate(y_data_list, axis=0)
        return x_data_combined, y_data_combined

    def __len__(self):
        return len(self.x_data)

    def __getitem__(self, idx):
        x = self.x_data[idx]
        y = self.y_data[idx]
        if self.feature_transform:
            x = self.feature_transform(x)
        if self.target_transform:
            y = self.target_transform(y)
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y,
                                                                  dtype=torch.float32 if self.regression else torch.int64)


class H5Dataset_lazy(Dataset):
    def __init__(self, file_paths, feature_dataset_name='features', label_dataset_name='labels',
                 y_offset=0, regression=False, feature_transform=None, target_transform=None):
        """
        :param file_paths: 文件路径列表
        :param feature_dataset_name: HDF5 文件中特征数据的名称
        :param label_dataset_name: HDF5 文件中标签数据的名称
        :param y_offset: 标签偏移量
        :param regression: 是否为回归任务
        :param feature_transform: 特征数据的变换函数
        :param target_transform: 标签数据的变换函数
        """
        self.file_paths = file_paths
        self.feature_dataset_name = feature_dataset_name
        self.label_dataset_name = label_dataset_name
        self.y_offset = y_offset
        self.regression = regression
        self.feature_transform = feature_transform
        self.target_transform = target_transform
        
        # 预计算总样本数
        self.total_samples = self._calculate_total_samples()
        
    def _calculate_total_samples(self):
        """计算所有文件中的总样本数"""
        total = 0
        for file_path in _iter_with_progress(self.file_paths, desc="Calculating total samples", unit="file"):
            with h5py.File(file_path, 'r') as file:
                total += file[self.feature_dataset_name].shape[0]
        return total
    
    def __len__(self):
        return self.total_samples
    
    def __getitem__(self, idx):
        # 找到 idx 对应的文件
        for file_path in self.file_paths:
            with h5py.File(file_path, 'r') as file:
                num_samples = file[self.feature_dataset_name].shape[0]
                if idx < num_samples:
                    # 加载数据
                    x = file[self.feature_dataset_name][idx]
                    y = file[self.label_dataset_name][idx]
                    if not self.regression:
                        y = y - self.y_offset
                        y = y.astype(int)
                    # 应用变换
                    if self.feature_transform:
                        x = self.feature_transform(x)
                    if self.target_transform:
                        y = self.target_transform(y)
                    return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32 if self.regression else torch.int64)
                idx -= num_samples
        raise IndexError(f"Index {idx} out of range")


class H5Dataset_Chunk(Dataset):
    def __init__(self, file_paths, feature_dataset_name='features', label_dataset_name='labels',
                 y_offset=0, regression=False, feature_transform=None, target_transform=None, chunk_size=1000):
        """
        :param file_paths: 文件路径列表
        :param feature_dataset_name: HDF5 文件中特征数据的名称
        :param label_dataset_name: HDF5 文件中标签数据的名称
        :param y_offset: 标签偏移量
        :param regression: 是否为回归任务
        :param feature_transform: 特征数据的变换函数
        :param target_transform: 标签数据的变换函数
        :param chunk_size: 每个块的大小
        """
        self.file_paths = file_paths
        self.feature_dataset_name = feature_dataset_name
        self.label_dataset_name = label_dataset_name
        self.y_offset = y_offset
        self.regression = regression
        self.feature_transform = feature_transform
        self.target_transform = target_transform
        self.chunk_size = chunk_size
        
        # 预计算每个文件的样本数和累积样本数
        self.file_sample_counts = []
        self.file_cumulative_counts = []
        self._precompute_file_indices()
        
        # 初始化当前块的数据
        self.current_chunk = None
        self.current_chunk_start = 0
        self.current_chunk_end = 0

    def _precompute_file_indices(self):
        """预计算每个文件的样本数和累积样本数"""
        total = 0
        for file_path in _iter_with_progress(self.file_paths, desc="Calculating total samples", unit="file"):
            with h5py.File(file_path, 'r') as file:
                num_samples = file[self.feature_dataset_name].shape[0]
                self.file_sample_counts.append(num_samples)
                self.file_cumulative_counts.append(total)
                total += num_samples
        self.total_samples = total

    def _find_file_index(self, idx):
        """根据全局索引找到对应的文件索引（使用二分查找）"""
        # 使用 bisect 找到 idx 应该插入的位置
        file_idx = bisect.bisect_right(self.file_cumulative_counts, idx) - 1
    
        if file_idx < 0 or file_idx >= len(self.file_paths):
            raise IndexError(f"Index {idx} out of range")
    
        # 计算局部索引
        local_idx = idx - self.file_cumulative_counts[file_idx]
        return file_idx, local_idx

    def _load_chunk(self, idx):
        """加载包含 idx 的块"""
        file_idx, local_idx = self._find_file_index(idx)
        file_path = self.file_paths[file_idx]
        
        with h5py.File(file_path, 'r') as file:
            num_samples = file[self.feature_dataset_name].shape[0]
            chunk_start = local_idx
            chunk_end = min(num_samples, local_idx + self.chunk_size)
            
            # 加载原始数据块
            x_data = file[self.feature_dataset_name][chunk_start:chunk_end]
            y_data = file[self.label_dataset_name][chunk_start:chunk_end]

            # 创建随机索引并打乱数据
            shuffle_indices = np.random.permutation(len(x_data))
            x_shuffled = x_data[shuffle_indices]
            y_shuffled = y_data[shuffle_indices]

            # 存储打乱后的数据块
            self.current_chunk = {
                'x': x_shuffled,
                'y': y_shuffled
            }

            ## 加载块数据
            #self.current_chunk = {
            #    'x': file[self.feature_dataset_name][chunk_start:chunk_end],
            #    'y': file[self.label_dataset_name][chunk_start:chunk_end]
            #}
            
            # 更新块的全局索引
            self.current_chunk_start = self.file_cumulative_counts[file_idx] + chunk_start
            self.current_chunk_end = self.file_cumulative_counts[file_idx] + chunk_end

    def __len__(self):
        return self.total_samples

    def __getitem__(self, idx):
        # 检查 idx 是否在当前块中
        if self.current_chunk is None or idx < self.current_chunk_start or idx >= self.current_chunk_end:
            self._load_chunk(idx)
        
        # 获取数据
        x = self.current_chunk['x'][idx - self.current_chunk_start]
        y = self.current_chunk['y'][idx - self.current_chunk_start]
        
        if not self.regression:
            y = y - self.y_offset
            y = y.astype(int)
        
        # 应用变换
        if self.feature_transform:
            x = self.feature_transform(x)
        if self.target_transform:
            y = self.target_transform(y)
        
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32 if self.regression else torch.int64)


class H5Dataset_Chunk_Old(Dataset):
    def __init__(self, file_paths, feature_dataset_name='features', label_dataset_name='labels',
                 y_offset=0, regression=False, feature_transform=None, target_transform=None, chunk_size=1000):
        """
        :param file_paths: 文件路径列表
        :param feature_dataset_name: HDF5 文件中特征数据的名称
        :param label_dataset_name: HDF5 文件中标签数据的名称
        :param y_offset: 标签偏移量
        :param regression: 是否为回归任务
        :param feature_transform: 特征数据的变换函数
        :param target_transform: 标签数据的变换函数
        :param chunk_size: 每个块的大小
        """
        self.file_paths = file_paths
        self.feature_dataset_name = feature_dataset_name
        self.label_dataset_name = label_dataset_name
        self.y_offset = y_offset
        self.regression = regression
        self.feature_transform = feature_transform
        self.target_transform = target_transform
        self.chunk_size = chunk_size
        
        # 预计算总样本数
        self.total_samples = self._calculate_total_samples()
        
        # 初始化当前块的数据
        self.current_chunk = None
        self.current_chunk_start = 0
        self.current_chunk_end = 0
        
    def _calculate_total_samples(self):
        """计算所有文件中的总样本数"""
        total = 0
        for file_path in _iter_with_progress(self.file_paths, desc="Calculating total samples", unit="file"):
            with h5py.File(file_path, 'r') as file:
                total += file[self.feature_dataset_name].shape[0]
        return total
    
    def _load_chunk(self, idx):
        """加载包含 idx 的块"""
        num_samples_accumulated = 0
        for file_path in self.file_paths:
            with h5py.File(file_path, 'r') as file:
                num_samples = file[self.feature_dataset_name].shape[0]
                local_idx = idx - num_samples_accumulated
                if local_idx < num_samples:
                    # 计算在当前文件内的块起始和结束位置
                    chunk_start = local_idx
                    chunk_end = min(num_samples, local_idx + self.chunk_size)
                    # 加载块数据
                    self.current_chunk = {
                        'x': file[self.feature_dataset_name][chunk_start:chunk_end],
                        'y': file[self.label_dataset_name][chunk_start:chunk_end]
                    }
                    # 更新块的全局索引
                    self.current_chunk_start = num_samples_accumulated + chunk_start
                    self.current_chunk_end = num_samples_accumulated + chunk_end
                    return
                num_samples_accumulated += num_samples
        raise IndexError(f"Index {idx} out of range")

    def __len__(self):
        return self.total_samples
    
    def __getitem__(self, idx):
        # 检查 idx 是否在当前块中
        if self.current_chunk is None or idx < self.current_chunk_start or idx >= self.current_chunk_end:
            self._load_chunk(idx)
        # 获取数据
        try:
            x = self.current_chunk['x'][idx - self.current_chunk_start]
        except:
            print(idx, self.current_chunk_start,self.current_chunk_end)
        y = self.current_chunk['y'][idx - self.current_chunk_start]
        if not self.regression:
            y = y - self.y_offset
            y = y.astype(int)
        # 应用变换
        if self.feature_transform:
            x = self.feature_transform(x)
        if self.target_transform:
            y = self.target_transform(y)
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32 if self.regression else torch.int64)


class H5Dataset_old(Dataset):
    def __init__(self, file_paths, dataset_name='data', y_offset=0, label_length=1,
                 regression=False, feature_transform=None, target_transform=None):
        """
        :param regression: If True, use raw labels for regression; if False, apply one-hot encoding for classification
        """
        self.regression = regression
        self.x_data, self.y_data = self.load_and_combine_h5_datasets(file_paths, dataset_name, y_offset, label_length)
        self.feature_transform = feature_transform
        self.target_transform = target_transform

    def load_and_combine_h5_datasets(self, file_paths, dataset_name, y_offset, label_length):
        x_data_list = []
        y_data_list = []
        for file_path in file_paths:
            with h5py.File(file_path, 'r') as file:
                stack = file[dataset_name][:]
                data = stack[:, :-label_length]
                x_data = data.reshape(-1, data.shape[1], 1)
                labels = stack[:, -label_length:] - y_offset

                if not self.regression:
                    # Assuming the label to be processed is at index 0 in the label array
                    labels = labels.astype(int)[:, 0]  # Cast labels to integers
                    # labels = one_hot_encode_labels(labels, self.num_classes)

                x_data_list.append(x_data)
                y_data_list.append(labels)

        x_data_combined = np.concatenate(x_data_list, axis=0)
        y_data_combined = np.concatenate(y_data_list, axis=0)
        return x_data_combined, y_data_combined

    def __len__(self):
        return len(self.x_data)

    def __getitem__(self, idx):
        x = self.x_data[idx]
        y = self.y_data[idx]

        if self.feature_transform:
            x = self.feature_transform(x)
        if self.target_transform:
            y = self.target_transform(y)

        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32 if self.regression else torch.int64)
