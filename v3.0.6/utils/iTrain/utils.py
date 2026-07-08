import torch
import os, re, random,socket
import torch.nn as nn
from torch.utils.data import Sampler
import sys
import torch.distributed as dist

def calculate_mae(y_true, y_pred):
    return torch.mean(torch.abs(y_true - y_pred))

def calculate_mape(y_true, y_pred):
    return torch.mean(torch.abs((y_true - y_pred) / y_true)) * 100


def save_model_weights(model, epoch, save_dir="model_weights", save_name="model_weights"):
    """
    保存模型权重，支持 DataParallel 和 DistributedDataParallel 模型。

    参数:
        model: 模型实例（可以是普通模型、DataParallel 或 DistributedDataParallel 模型）。
        epoch: 当前训练轮数。
        save_dir: 模型权重保存目录。
        save_name: 模型权重文件名前缀。
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 处理不同类型的并行模型
    if isinstance(model, (nn.DataParallel, nn.parallel.DistributedDataParallel)):
        state_dict = model.module.state_dict()  # 对于并行模型，去掉 `module.` 前缀
    else:
        state_dict = model.state_dict()

    # 保存模型权重
    save_path = os.path.join(save_dir, f"{save_name}_epoch{epoch + 1}.pth")
    torch.save(state_dict, save_path)
    print(f"Model weights saved to {save_path}")


def extract_batch_number(filename):
    """从文件名中提取 batch 的序号"""
    match = re.search(r'batch(\d+)', filename)
    if match:
        return int(match.group(1))
    return -1  # 如果没有匹配到，返回 -1


def split_dataset_old(directory, keywords, train_num=100, val_num=2, shuffle=True):
    """
    将文件按关键字分组，并根据指定数量选择训练集和验证集。
    :param directory: 数据集目录
    :param keywords: 关键字列表
    :param train_num: 每类训练集所需数量
    :param val_num: 每类验证集所需数量
    :param shuffle: 是否随机打乱文件顺序
    :return: 验证集列表和训练集列表
    """
    # 初始化字典，按关键字分组存储文件
    keyword_files = {keyword: [] for keyword in keywords}

    # 遍历目录，按关键字分组
    for root, dirs, files in os.walk(directory):
        for file in files:
            for keyword in keywords:
                if keyword in file:
                    full_path = os.path.join(root, file)
                    keyword_files[keyword].append(full_path)

    # 初始化验证集和训练集
    validation_set = []
    training_set = []

    # 处理每个关键字组
    for keyword, files in keyword_files.items():
        if not files:
            continue  # 如果没有文件，跳过

        if shuffle:
            random.shuffle(files)  # 随机打乱文件顺序

        # 计算实际可取的验证集和训练集数量
        total_files = len(files)
        actual_val_num = min(val_num, total_files)
        actual_train_num = min(train_num, total_files - actual_val_num)

        # 分割验证集和训练集
        validation_files = files[:actual_val_num]
        training_files = files[actual_val_num:actual_val_num + actual_train_num]

        validation_set.extend(validation_files)
        training_set.extend(training_files)

    return validation_set, training_set


def find_files_with_keywords(directory, keywords, match_all=True):
    """
    查找目录下包含指定关键词的文件

    参数:
        directory: 要搜索的根目录
        keywords: 关键词列表(如['keyword1', 'keyword2'])
        match_all: 是否需匹配所有关键词(True)，或任一关键词(False)

    返回:
        包含匹配关键词的文件路径列表
    """
    matched_files = []

    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)

            # 检查文件是否包含所有/任一关键词
            if match_all:
                if all(keyword in filename for keyword in keywords):
                    matched_files.append(filepath)
            else:
                if any(keyword in filename for keyword in keywords):
                    matched_files.append(filepath)

    return matched_files

def find_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class FileChunkSampler(Sampler):
    def __init__(self, dataset, num_replicas, rank, chunk_size):
        """
        自定义采样器，将数据以文件块为单位分配给不同的进程
        :param dataset: 数据集，提供文件样本统计
        :param num_replicas: 分布式计算中的总进程数量
        :param rank: 当前进程的 rank
        :param chunk_size: 每个进程每轮训练处理的样本数量
        """
        self.dataset = dataset
        self.num_replicas = num_replicas
        self.rank = rank
        self.chunk_size = chunk_size

        # 创建文件索引的累积计数
        self.file_sample_counts = dataset.file_sample_counts
        self.file_cumulative_counts = dataset.file_cumulative_counts
        self.total_samples = sum(self.file_sample_counts)

        self.indices = self._create_indices_for_process()

    def _create_indices_for_process(self):
        indices = []
        start = self.rank * self.chunk_size
        end = start + self.chunk_size

        for i in range(len(self.file_sample_counts)):
            file_start = self.file_cumulative_counts[i]
            file_end = file_start + self.file_sample_counts[i]

            if start < file_end:
                if end > file_start:
                    overlap_start = max(start, file_start)
                    overlap_end = min(end, file_end)
                    indices.extend(range(overlap_start, overlap_end))

        return indices

    def __iter__(self):
        return iter(self.indices)

    def __len__(self):
        return len(self.indices)

def signal_handler(sig, frame):
    print('Exiting gracefully...')
    try:
        dist.destroy_process_group()
    except Exception as e:
        print(f"Warning: Failed to destroy process group. {e}")
    sys.exit(0)