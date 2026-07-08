import torch
from torch import optim
import torch.nn as nn
import torch.multiprocessing as mp
import torch.distributed as dist
from torch.utils.data import DataLoader, DistributedSampler
from torch.nn.parallel import DistributedDataParallel as DDP
from .utils import calculate_mae, calculate_mape, save_model_weights, FileChunkSampler,signal_handler,find_free_port
import numpy as np
from tqdm import tqdm
import os,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import seaborn as sns
import signal
import sys


def _configure_output_streams():
    # Ensure redirected logs are flushed line by line in nohup/background mode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True, write_through=True)


_configure_output_streams()


def _progress_enabled(show_process=True):
    # tqdm writes to stderr by default; disable bars when redirected to log files.
    return show_process and sys.stderr.isatty()

def load_and_test_regression(model, weights_path, test_loader, criterion=None, training_mode=False,device=None):
    # 自动检测设备
    if not device:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # print(f'Using device: {device}')

    if not training_mode:
        # 加载模型权重
        model.load_state_dict(torch.load(weights_path, map_location=device))
        model.to(device)
    model.eval()

    total_loss = 0
    total_mae = 0
    total_mape = 0
    if criterion is None:
        criterion = torch.nn.MSELoss()

    with torch.no_grad():
        for x_batch, y_batch in test_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            total_loss += loss.item()
            total_mae += calculate_mae(y_batch, outputs).item()
            total_mape += calculate_mape(y_batch, outputs).item()

    avg_loss = total_loss / len(test_loader)
    avg_mae = total_mae / len(test_loader)
    avg_mape = total_mape / len(test_loader)
    print(f'Test Loss: {avg_loss:.4f}, Test MAE: {avg_mae:.4f}, Test MAPE: {avg_mape:.4f}%', flush=True)
    return avg_loss, avg_mae, avg_mape

def validate_model_regression(model, val_loader, device,criterion=None, compute_metrics=False):
    model.eval()
    total_val_loss = 0
    total_val_mae = 0
    total_val_mape = 0
    if criterion is None:
        criterion = torch.nn.MSELoss()
    with torch.no_grad():
        for x_batch, y_batch in val_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            total_val_loss += loss.item()
            if compute_metrics:
                total_val_mae += calculate_mae(y_batch, outputs).item()
                total_val_mape += calculate_mape(y_batch, outputs).item()
    avg_val_loss = total_val_loss / len(val_loader)
    avg_val_mae = total_val_mae / len(val_loader) if compute_metrics else None
    avg_val_mape = total_val_mape / len(val_loader) if compute_metrics else None
    return avg_val_loss, avg_val_mae, avg_val_mape


def train_model_regression_old(model, train_loader, val_loader,test_loader, num_epochs=10, learning_rate=0.0002,criterion=None,
                compute_metrics=False, weights_path='.',weights_name="model", save_interval=1,
                use_parallel=False, gpu_ids=None, plot_metrics=False):
    """
        训练回归模型，支持多 GPU 并行训练。

        参数:
            model: 模型实例。
            train_loader: 训练数据加载器。
            val_loader: 验证数据加载器。
            num_epochs: 训练轮数。
            learning_rate: 学习率。
            compute_metrics: 是否计算MAE/MAPE。
            weights_path: 模型权重保存路径。
            weights_name: 模型权重文件名。
            save_interval: 保存模型的间隔轮数。
            use_parallel: 是否启用多 GPU 并行训练。
            gpu_ids: 指定使用的 GPU 设备 ID 列表（如 [0, 1]）。
    """
    # 打印模型参数量
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total number of parameters: {total_params}")

    # 初始化存储字典
    metrics = {
        'train_loss': [],
        'val_loss': [],
        'train_mae': [],
        'val_mae': [],
        'train_mape': [],
        'val_mape': []
    }

    # 设置设备
    if use_parallel and torch.cuda.is_available():
        if gpu_ids is None:
            gpu_ids = list(range(torch.cuda.device_count()))
        device = torch.device(f'cuda:{gpu_ids[0]}')  # 主 GPU
        torch.cuda.set_device(device)
        print(f"Using GPUs: {gpu_ids}")
        model = nn.DataParallel(model, device_ids=gpu_ids)  # 使用 DataParallel 包装模型
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {device}")
    model.to(device)
    if criterion == None:
        criterion = torch.nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        total_mae = 0
        total_mape = 0
        for x_batch, y_batch in tqdm(
            train_loader,
            desc=f"Epoch {epoch + 1}/{num_epochs}",
            unit="batch",
            disable=not _progress_enabled(True),
        ):
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            optimizer.zero_grad()
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            if compute_metrics:
                total_mae += calculate_mae(y_batch, outputs).item()
                total_mape += calculate_mape(y_batch, outputs).item()
        avg_loss = total_loss / len(train_loader)
        avg_mae = total_mae / len(train_loader) if compute_metrics else None
        avg_mape = total_mape / len(train_loader) if compute_metrics else None

        avg_val_loss, avg_val_mae, avg_val_mape = validate_model_regression(model, val_loader, device,criterion=criterion,compute_metrics=compute_metrics)
        
        # 记录指标
        metrics['train_loss'].append(avg_loss)
        metrics['val_loss'].append(avg_val_loss)
        if compute_metrics:
            metrics['train_mae'].append(avg_mae)
            metrics['val_mae'].append(avg_val_mae)
            metrics['train_mape'].append(avg_mape)
            metrics['val_mape'].append(avg_val_mape)

        print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {avg_loss:.4f}, Val Loss: {avg_val_loss:.4f}')
        if compute_metrics:
            print(
                f'Epoch {epoch + 1}/{num_epochs} Metrics: MAE: {avg_mae:.4f}, Val MAE: {avg_val_mae:.4f}, MAPE: {avg_mape:.2f}%, Val MAPE: {avg_val_mape:.2f}%')

        if (epoch + 1) % save_interval == 0:
            save_model_weights(model, epoch, save_dir=weights_path,save_name=weights_name)
            load_and_test_regression(model, os.path.join(weights_path,f"{weights_name}_epoch{epoch + 1}.pth"),
                                         test_loader, criterion=criterion,
                                         training_mode=True, device=device)

    # 绘制并保存指标曲线和数据
    if plot_metrics:
        # 确保保存目录存在
        os.makedirs(weights_path, exist_ok=True)

        # 保存指标数据为JSON文件
        metrics_file = os.path.join(weights_path, f"{weights_name}_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f)

        # 绘制Loss曲线
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 3, 1)
        plt.plot(metrics['train_loss'], label='Train Loss')
        plt.plot(metrics['val_loss'], label='Validation Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()

        # 如果计算了准确率，绘制Accuracy曲线
        if compute_metrics:
            plt.subplot(1, 3, 2)
            plt.plot(metrics['train_mae'], label='Train MAE')
            plt.plot(metrics['val_mae'], label='Validation MAE')
            plt.xlabel('Epoch')
            plt.ylabel('MAE')
            plt.title('Training and Validation MAE')
            plt.legend()

            plt.subplot(1, 3, 3)
            plt.plot(metrics['train_mape'], label='Train MAPE')
            plt.plot(metrics['val_mape'], label='Validation MAPE')
            plt.xlabel('Epoch')
            plt.ylabel('MAPE')
            plt.title('Training and Validation MAPE')
            plt.legend()

        # 保存图像
        plot_file = os.path.join(weights_path, f"{weights_name}_metrics.png")
        plt.savefig(plot_file)
        plt.close()

        print(f"Training metrics saved to {metrics_file} and {plot_file}")

    return metrics

def train_model_regression(model, train_dataset, val_dataset, test_dataset, shuffle_train=True, shuffle_val=False, batch_size=64,
                           num_epochs=10, learning_rate=0.0002,
                           compute_metrics=False, weights_path='.', weights_name="model", save_interval=1,
                           use_parallel=False, gpu_ids=None, plot_metrics=False, show_process=True,criterion=None):

    # 设置设备
    if use_parallel and torch.cuda.is_available():
        signal.signal(signal.SIGINT, signal_handler)
        world_size = len(gpu_ids)
        setup()
        mp.spawn(
            distributed_train_worker_regression,
            args=(
                world_size, model, train_dataset, val_dataset,test_dataset, shuffle_train, shuffle_val, batch_size, num_epochs,
                learning_rate,criterion, compute_metrics, weights_path,
                weights_name, save_interval, gpu_ids, plot_metrics, show_process),
            nprocs=world_size,
            join=True
            )

    else:
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=shuffle_train)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=shuffle_val)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=shuffle_val)
        train_model_regression_old(model,train_loader, val_loader,test_loader, num_epochs, learning_rate,criterion,compute_metrics, weights_path, weights_name, save_interval, use_parallel, gpu_ids, plot_metrics)

def distributed_train_worker_regression(rank, world_size, model, train_dataset, val_dataset,test_dataset, shuffle_train,shuffle_val,batch_size, num_epochs, learning_rate,criterion,
                             compute_metrics, weights_path, weights_name, save_interval,gpu_ids, plot_metrics,show_process):
    dist.init_process_group("nccl", rank=rank, world_size=world_size)

    # Set up device for each process
    device = torch.device(f'cuda:{gpu_ids[rank]}')
    model = model.to(device)
    model = DDP(model, device_ids=[gpu_ids[rank]], find_unused_parameters=True)

    # Criterion and optimizer
    if criterion == None:
        criterion = nn.MSELoss().to(device)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Data loaders with DistributedSampler
    # 使用自定义采样器
    chunk_size = len(train_dataset) // world_size
    trainDataset_className = train_dataset.__class__.__name__  # 返回train_dataset的类名
    if trainDataset_className == "H5Dataset_Chunk":
        sampler = FileChunkSampler(train_dataset, world_size, rank, chunk_size)
    else:
        sampler = DistributedSampler(train_dataset, num_replicas=world_size, rank=rank, shuffle=shuffle_train)
    train_loader = DataLoader(dataset=train_dataset, sampler=sampler, batch_size=batch_size,shuffle=False)
    if rank == 0:
        val_loader = DataLoader(dataset=val_dataset, batch_size=batch_size, shuffle=shuffle_val)
        test_loader = DataLoader(dataset=test_dataset, batch_size=batch_size, shuffle=shuffle_val)

    # 初始化存储训练指标的字典
    metrics = {
        'train_loss': [],
        'val_loss': [],
        'train_mae': [],
        'val_mae': [],
        'train_mape': [],
        'val_mape': []
    }

    for epoch in range(num_epochs):
        # train_sampler.set_epoch(epoch)  # Ensure epoch-level reshuffling
        train_loss, train_mae,train_mape = train_epoch_regression(rank, model, train_loader, optimizer, criterion, device, epoch, num_epochs, compute_metrics, show_process)
        if rank ==0:
            val_loss, val_mae, val_mape = validate_model_regression(model, val_loader, device, criterion=criterion,compute_metrics=compute_metrics )
        if rank == 0:
            # 记录指标
            metrics['train_loss'].append(train_loss)
            metrics['val_loss'].append(val_loss)
            if compute_metrics:
                metrics['train_mae'].append(train_mae)
                metrics['val_mae'].append(val_mae)
                metrics['train_mape'].append(train_mape)
                metrics['val_mape'].append(val_mape)
            print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}', flush=True)
            if compute_metrics:
                print(
                    f'Epoch {epoch + 1}/{num_epochs} Metrics: MAE: {train_mae:.4f}, Val MAE: {val_mae:.4f}, MAPE: {train_mape:.2f}%, Val MAPE: {val_mape:.2f}%',
                    flush=True,
                )

            if (epoch + 1) % save_interval == 0:
                save_model_weights(model, epoch, save_dir=weights_path, save_name=weights_name)
                test_loss, test_accuracy, _ = load_and_test_regression(model, os.path.join(weights_path,
                                                                                               f"{weights_name}_epoch{epoch + 1}.pth"),
                                                                           test_loader, criterion=criterion,
                                                                           training_mode=True, device=device)

    # 绘制并保存指标曲线和数据
    if rank == 0 and plot_metrics:
        # 确保保存目录存在
        os.makedirs(weights_path, exist_ok=True)

        # 保存指标数据为JSON文件
        metrics_file = os.path.join(weights_path, f"{weights_name}_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f)

        # 绘制Loss曲线
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 3, 1)
        plt.plot(metrics['train_loss'], label='Train Loss')
        plt.plot(metrics['val_loss'], label='Validation Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()

        # 如果计算了准确率，绘制Accuracy曲线
        if compute_metrics:
            plt.subplot(1, 3, 2)
            plt.plot(metrics['train_mae'], label='Train MAE')
            plt.plot(metrics['val_mae'], label='Validation MAE')
            plt.xlabel('Epoch')
            plt.ylabel('MAE')
            plt.title('Training and Validation MAE')

            plt.subplot(1, 3, 3)
            plt.plot(metrics['train_mape'], label='Train MAPE')
            plt.plot(metrics['val_mape'], label='Validation MAPE')
            plt.xlabel('Epoch')
            plt.ylabel('MAPE')
            plt.title('Training and Validation MAPE')
            plt.legend()

        # 保存图像
        plot_file = os.path.join(weights_path, f"{weights_name}_metrics.png")
        plt.savefig(plot_file)
        plt.close()

        print(f"Training metrics saved to {metrics_file} and {plot_file}")


    cleanup()

def train_epoch_regression(rank, model, train_loader, optimizer, criterion, device, epoch, num_epochs, compute_metrics,show_process):
    model.train()
    total_loss = 0
    total_mae = 0
    total_mape = 0
    total_batches = len(train_loader.dataset)  # Assume global dataset size
    total_batches_tensor = torch.tensor(total_batches).to(device)

    iterator = tqdm(
        train_loader,
        desc=f"Epoch {epoch + 1}/{num_epochs}",
        unit="batch",
        disable=(not _progress_enabled(show_process)) or (rank != 0),
    )
    for x_batch, y_batch in iterator:
        x_batch, y_batch = x_batch.to(device), y_batch.to(device)
        x_batch = x_batch.unsqueeze(1)
        optimizer.zero_grad()
        outputs = model(x_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        if compute_metrics:
            total_mae += calculate_mae(y_batch, outputs).item()
            total_mape += calculate_mape(y_batch, outputs).item()


    if compute_metrics:
        total_mae_tensor = torch.tensor(total_mae).to(device)
        total_mape_tensor = torch.tensor(total_mape).to(device)
        dist.all_reduce(total_mae_tensor, op=dist.ReduceOp.SUM)
        dist.all_reduce(total_mape_tensor, op=dist.ReduceOp.SUM)

    total_loss_tensor = torch.tensor(total_loss).to(device)
    dist.all_reduce(total_loss_tensor, op=dist.ReduceOp.SUM)

    avg_loss = total_loss_tensor.item() / total_batches_tensor.item()
    avg_mae = total_mae_tensor.item() / total_batches_tensor.item() if compute_metrics else None
    avg_mape = total_mape_tensor.item() / total_batches_tensor.item() if compute_metrics else None

    return avg_loss, avg_mae, avg_mape


def load_and_test_classification(model, weights_path, test_loader, plot=False,criterion=None,training_mode=False,device=None, class_names=None):
    # 自动检测设备
    if not device:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # print(f'Using device: {device}')

    # 加载模型权重
    if not training_mode:
        model.load_state_dict(torch.load(weights_path, map_location=device))
        model.to(device)
    model.eval()

    total_correct = 0
    total_top3_correct = 0
    total_loss = 0
    if criterion is None:
        criterion = torch.nn.CrossEntropyLoss()
    
    # 用于存储所有预测和真实标签
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for x_batch, y_batch in test_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            y_batch = y_batch.squeeze(1)  # 去掉多余的维度
            outputs = model(x_batch)
            # 打印 y_batch 和 outputs 的形状
            # print(f"y_batch shape: {y_batch.shape}")
            # print(f"outputs shape: {outputs.shape}")
            # unique_labels = torch.unique(y_batch)
            # print(f"Unique labels in y_batch: {unique_labels}")
            loss = criterion(outputs, y_batch)
            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total_correct += (predicted == y_batch).sum().item()

            top3 = min(3, outputs.size(1))
            top3_indices = torch.topk(outputs, k=top3, dim=1).indices
            total_top3_correct += (top3_indices == y_batch.unsqueeze(1)).any(dim=1).sum().item()
            
            # 收集预测和真实标签
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(y_batch.cpu().numpy())

    avg_loss = total_loss / len(test_loader)
    accuracy = total_correct / len(test_loader.dataset)
    top3_accuracy = total_top3_correct / len(test_loader.dataset)
    print(f'Test Loss: {avg_loss:.4f}, Test Top-1 Accuracy: {accuracy * 100:.2f}%, Test Top-3 Accuracy: {top3_accuracy * 100:.2f}%', flush=True)
    
    # 计算混淆矩阵
    cm = confusion_matrix(all_labels, all_preds)
    # 某些类别在当前评估集中可能没有样本，按行归一化时要避免除以 0
    row_sums = cm.sum(axis=1, keepdims=True).astype(float)
    cm_normalized = np.divide(cm.astype(float), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums != 0)
    
    if plot:
        # 创建显示文本（样本数 + 百分比）
        annot_labels = np.empty_like(cm).astype(str)
        nrows, ncols = cm.shape
        for i in range(nrows):
            for j in range(ncols):
                c, p = cm[i,j], cm_normalized[i,j]
                if c == 0:
                    annot_labels[i,j] = '0\n(0%)'
                else:
                    annot_labels[i,j] = f'{c}\n({p:.1%})'

        # 绘制混淆矩阵
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm_normalized, annot=annot_labels, fmt='', cmap='Blues',
                    xticklabels=class_names if class_names else 'auto',
                    yticklabels=class_names if class_names else 'auto')
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.title('Confusion Matrix (Counts and Percentages)')
        plt.show()
    return avg_loss, accuracy, cm

def train_model_classification_old(model, train_loader, val_loader,test_loader, num_epochs=10, learning_rate=0.0002,
                               compute_metrics=False, weights_path='.', weights_name="model", save_interval=1,
                               use_parallel=False, gpu_ids=None, plot_metrics=False):
    """
        训练分类模型，支持多 GPU 并行训练。

        参数:
            model: 模型实例。
            train_loader: 训练数据加载器。
            val_loader: 验证数据加载器。
            num_epochs: 训练轮数。
            learning_rate: 学习率。
            compute_metrics: 是否计算准确率。
            weights_path: 模型权重保存路径。
            weights_name: 模型权重文件名。
            save_interval: 保存模型的间隔轮数。
            use_parallel: 是否启用多 GPU 并行训练。
            gpu_ids: 指定使用的 GPU 设备 ID 列表（如 [0, 1]）。
            plot_metrics: 是否绘制并保存训练指标曲线图和数据（默认False）。
    """
    # 打印模型参数量
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total number of parameters: {total_params}")

    # 初始化存储训练指标的字典
    metrics = {
        'train_loss': [],
        'val_loss': [],
        'train_acc': [],
        'val_acc': []
    }
    
    # 设置设备
    if use_parallel and torch.cuda.is_available():
        if gpu_ids is None:
            gpu_ids = list(range(torch.cuda.device_count()))
        device = torch.device(f'cuda:{gpu_ids[0]}')  # 主 GPU
        torch.cuda.set_device(device)
        print(f"Using GPUs: {gpu_ids}")
        model = nn.DataParallel(model, device_ids=gpu_ids)  # 使用 DataParallel 包装模型
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {device}")

    model.to(device)
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        total_correct = 0
        for x_batch, y_batch in tqdm(
            train_loader,
            desc=f"Epoch {epoch + 1}/{num_epochs}",
            unit="batch",
            disable=not _progress_enabled(True),
        ):
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            y_batch = y_batch.squeeze(1)
            optimizer.zero_grad()
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

            if compute_metrics:
                _, predicted = torch.max(outputs, 1)
                total_correct += (predicted == y_batch).sum().item()

        avg_loss = total_loss / len(train_loader)
        avg_accuracy = total_correct / len(train_loader.dataset) if compute_metrics else None

        avg_val_loss, avg_val_accuracy = validate_model_classification(model, val_loader, device,criterion=criterion, compute_metrics = compute_metrics)

        # 记录指标
        metrics['train_loss'].append(avg_loss)
        metrics['val_loss'].append(avg_val_loss)
        if compute_metrics:
            metrics['train_acc'].append(avg_accuracy)
            metrics['val_acc'].append(avg_val_accuracy)

        print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {avg_loss:.4f}, Val Loss: {avg_val_loss:.4f}', flush=True)

        if compute_metrics:
            print(f'Epoch {epoch + 1}/{num_epochs} Metrics: Train Acc: {avg_accuracy * 100:.2f}%, Val Acc: {avg_val_accuracy * 100:.2f}%', flush=True)

        if (epoch + 1) % save_interval == 0:
            save_model_weights(model, epoch, save_dir=weights_path, save_name=weights_name)
            test_loss, test_accuracy, _ = load_and_test_classification(model, os.path.join(weights_path,
                                                                                           f"{weights_name}_epoch{epoch + 1}.pth"),
                                                                       test_loader, criterion=criterion,
                                                                       training_mode=True, device=device)


    # 绘制并保存指标曲线和数据
    if plot_metrics:
        # 确保保存目录存在
        os.makedirs(weights_path, exist_ok=True)
        
        # 保存指标数据为JSON文件
        metrics_file = os.path.join(weights_path, f"{weights_name}_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f)
        
        # 绘制Loss曲线
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(metrics['train_loss'], label='Train Loss')
        plt.plot(metrics['val_loss'], label='Validation Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()
        
        # 如果计算了准确率，绘制Accuracy曲线
        if compute_metrics:
            plt.subplot(1, 2, 2)
            plt.plot(metrics['train_acc'], label='Train Accuracy')
            plt.plot(metrics['val_acc'], label='Validation Accuracy')
            plt.xlabel('Epoch')
            plt.ylabel('Accuracy')
            plt.title('Training and Validation Accuracy')
            plt.legend()
        
        # 保存图像
        plot_file = os.path.join(weights_path, f"{weights_name}_metrics.png")
        plt.savefig(plot_file)
        plt.close()
        
        print(f"Training metrics saved to {metrics_file} and {plot_file}")

    return metrics


def train_model_classification(model, train_dataset, val_dataset,test_dataset, shuffle_train=True, shuffle_val=False, batch_size=64,
                               num_epochs=10, learning_rate=0.0002,
                               compute_metrics=False, weights_path='.', weights_name="model", save_interval=1,
                               use_parallel=False, gpu_ids=None, plot_metrics=False,show_process=True):

    if use_parallel and torch.cuda.is_available():
        signal.signal(signal.SIGINT, signal_handler)
        world_size = len(gpu_ids)
        setup()
        mp.spawn(
            distributed_train_worker,
            args=(
            world_size, model, train_dataset, val_dataset,test_dataset, shuffle_train,shuffle_val,batch_size, num_epochs, learning_rate, compute_metrics, weights_path,
            weights_name, save_interval, gpu_ids, plot_metrics, show_process),
            nprocs=world_size,
            join=True
        )
    else:
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=shuffle_train)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=shuffle_val)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=shuffle_val)
        train_model_classification_old(model, train_loader, val_loader,test_loader, num_epochs=num_epochs,
                                       learning_rate=learning_rate,
                                       compute_metrics=compute_metrics, weights_path=weights_path,
                                       weights_name=weights_name, save_interval=save_interval,
                                       use_parallel=False, gpu_ids=None, plot_metrics=plot_metrics)

def setup():
    os.environ['MASTER_ADDR'] = '127.0.0.1'
    os.environ['MASTER_PORT'] = str(find_free_port())


def cleanup():
    dist.destroy_process_group()

def validate_model_classification(model, val_loader, device,criterion=None, compute_metrics=False):
    model.eval()
    total_val_loss = 0
    total_correct = 0
    if criterion is None:
        criterion = torch.nn.CrossEntropyLoss()
    with torch.no_grad():
        for x_batch, y_batch in val_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            y_batch = y_batch.squeeze(1)  # 去掉多余的维度
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            batch_size = x_batch.size(0)
            total_val_loss += loss.item()* batch_size

            if compute_metrics:
                _, predicted = torch.max(outputs, 1)
                total_correct += (predicted == y_batch).sum().item()

    avg_val_loss = total_val_loss / len(val_loader.dataset)
    avg_val_accuracy = total_correct / len(val_loader.dataset) if compute_metrics else None
    return avg_val_loss, avg_val_accuracy

def validate_epoch(model, val_loader, device,criterion=None, compute_metrics=False):
    model.eval()
    total_val_loss = 0
    total_correct = 0
    if criterion is None:
        criterion = torch.nn.CrossEntropyLoss()
    with torch.no_grad():
        for x_batch, y_batch in val_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            x_batch = x_batch.unsqueeze(1)
            y_batch = y_batch.squeeze(1)  # 去掉多余的维度
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            total_val_loss += loss.item()

            if compute_metrics:
                _, predicted = torch.max(outputs, 1)
                total_correct += (predicted == y_batch).sum().item()
                total_correct_tensor = torch.tensor(total_correct).to(device)
                dist.all_reduce(total_correct_tensor, op=dist.ReduceOp.SUM)

    # ---- 修改开始：添加all_reduce在验证阶段 ----
    total_val_loss_tensor = torch.tensor(total_val_loss).to(device)
    total_samples_tensor = torch.tensor(len(val_loader.dataset)).to(device)

    dist.all_reduce(total_val_loss_tensor, op=dist.ReduceOp.SUM)
    dist.all_reduce(total_samples_tensor, op=dist.ReduceOp.SUM)

    avg_val_loss = total_val_loss_tensor.item() / total_samples_tensor.item()
    avg_val_accuracy = total_correct_tensor.item() / total_samples_tensor.item() if compute_metrics else None
    return avg_val_loss, avg_val_accuracy

def train_epoch(rank, model, train_loader, optimizer, criterion, device, epoch, num_epochs, compute_metrics, show_process):
    model.train()
    total_loss = 0
    total_correct = 0
    total_samples = len(train_loader.dataset)  # Assume global dataset size
    total_samples_tensor = torch.tensor(total_samples).to(device)

    iterator = tqdm(
        train_loader,
        desc=f"Epoch {epoch + 1}/{num_epochs}",
        unit="batch",
        disable=(not _progress_enabled(show_process)) or (rank != 0),
    )
    for x_batch, y_batch in iterator:
        x_batch, y_batch = x_batch.to(device), y_batch.to(device)
        x_batch = x_batch.unsqueeze(1)
        y_batch = y_batch.squeeze(1)
        optimizer.zero_grad()
        outputs = model(x_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

        if compute_metrics:
            _, predicted = torch.max(outputs, 1)
            total_correct += (predicted == y_batch).sum().item()

    if compute_metrics:
        total_correct_tensor = torch.tensor(total_correct).to(device)
        dist.all_reduce(total_correct_tensor, op=dist.ReduceOp.SUM)

    total_loss_tensor = torch.tensor(total_loss).to(device)
    dist.all_reduce(total_loss_tensor, op=dist.ReduceOp.SUM)

    avg_loss = total_loss_tensor.item() / total_samples_tensor.item()
    avg_accuracy = total_correct_tensor.item() / total_samples_tensor.item() if compute_metrics else None

    return avg_loss, avg_accuracy

def distributed_train_worker(rank, world_size, model, train_dataset, val_dataset,test_dataset,shuffle_train,shuffle_val,batch_size, num_epochs, learning_rate,
                             compute_metrics, weights_path, weights_name, save_interval,gpu_ids, plot_metrics,show_process):

    dist.init_process_group("nccl", rank=rank, world_size=world_size)
    # Set up device for each process
    device = torch.device(f'cuda:{gpu_ids[rank]}')
    model = model.to(device)
    model = DDP(model, device_ids=[gpu_ids[rank]], find_unused_parameters=True)

    # Criterion and optimizer
    criterion = nn.CrossEntropyLoss().to(device)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Data loaders with DistributedSampler
    # 使用自定义采样器
    chunk_size = len(train_dataset) // world_size
    trainDataset_className = train_dataset.__class__.__name__ #返回train_dataset的类名
    if trainDataset_className == "H5Dataset_Chunk":
        sampler = FileChunkSampler(train_dataset, world_size, rank, chunk_size)
    else:
        sampler = DistributedSampler(train_dataset, num_replicas=world_size, rank=rank, shuffle=shuffle_train)
    train_loader = DataLoader(dataset=train_dataset, sampler=sampler, batch_size=batch_size,shuffle=False)
    if rank == 0:
        val_loader = DataLoader(dataset=val_dataset, batch_size=batch_size, shuffle=shuffle_val)
        test_loader = DataLoader(dataset=test_dataset, batch_size=batch_size, shuffle=shuffle_val)

    # 初始化存储训练指标的字典
    metrics = {
        'train_loss': [],
        'val_loss': [],
        'train_acc': [],
        'val_acc': []
    }

    for epoch in range(num_epochs):
        # train_sampler.set_epoch(epoch)  # Ensure epoch-level reshuffling
        train_loss, train_acc = train_epoch(rank, model, train_loader, optimizer, criterion, device, epoch, num_epochs, compute_metrics, show_process)
        if rank ==0:
            val_loss, val_acc = validate_model_classification(model, val_loader, device, criterion=criterion,compute_metrics=compute_metrics )


        if rank == 0:
            # 记录指标
            metrics['train_loss'].append(train_loss)
            metrics['val_loss'].append(val_loss)
            if compute_metrics:
                metrics['train_acc'].append(train_acc)
                metrics['val_acc'].append(val_acc)

            print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}', flush=True)
            if compute_metrics:
                print(f'Epoch {epoch + 1}/{num_epochs} Metrics: Train Acc: {train_acc * 100:.2f}%, Val Acc: {val_acc * 100:.2f}%', flush=True)

            if (epoch + 1) % save_interval == 0:
                save_model_weights(model, epoch, save_dir=weights_path, save_name=weights_name)
                test_loss, test_accuracy, _ = load_and_test_classification(model, os.path.join(weights_path, f"{weights_name}_epoch{epoch + 1}.pth"), test_loader,criterion=criterion, training_mode=True, device=device)


    # 绘制并保存指标曲线和数据
    if rank == 0 and plot_metrics:
        # 确保保存目录存在
        os.makedirs(weights_path, exist_ok=True)

        # 保存指标数据为JSON文件
        metrics_file = os.path.join(weights_path, f"{weights_name}_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f)

        # 绘制Loss曲线
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(metrics['train_loss'], label='Train Loss')
        plt.plot(metrics['val_loss'], label='Validation Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()

        # 如果计算了准确率，绘制Accuracy曲线
        if compute_metrics:
            plt.subplot(1, 2, 2)
            plt.plot(metrics['train_acc'], label='Train Accuracy')
            plt.plot(metrics['val_acc'], label='Validation Accuracy')
            plt.xlabel('Epoch')
            plt.ylabel('Accuracy')
            plt.title('Training and Validation Accuracy')
            plt.legend()

        # 保存图像
        plot_file = os.path.join(weights_path, f"{weights_name}_metrics.png")
        plt.savefig(plot_file)
        plt.close()

        print(f"Training metrics saved to {metrics_file} and {plot_file}")

    cleanup()



def predict(input_data,model, weights_path, task_type='classification', device=None):
    """
    使用训练好的模型对单个数据样本进行预测。

    :param model: 需要预测的 PyTorch 模型
    :param input_data: 单个样本数据，一维 numpy 数组
    :param weights_path: 模型权重文件路径
    :param task_type: 任务类型，'classification' 或 'regression'
    :param device: 计算设备，默认为自动检测
    :return: 模型的预测结果
    """
    # 自动检测设备
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # print(f'Using device: {device}')

    # 加载模型权重
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.to(device)
    model.eval()

    # 确保输入是 numpy 数组并转换为 PyTorch 张量
    if isinstance(input_data, np.ndarray):
        input_data = torch.from_numpy(input_data).float()  # 假设输入数据为浮点型
    else:
        raise ValueError("input_data 必须是一维 numpy 数组")

    # 为 1D 卷积准备输入形状
    # 输入一维数组应为 (sequence_length,)
    # 调整形状为 (1, 1, sequence_length)
    input_data = input_data.unsqueeze(0).unsqueeze(0)

    # 移动输入数据到指定设备
    input_data = input_data.to(device)

    # 模型前向传播
    with torch.no_grad():
        outputs = model(input_data)


    if task_type == 'classification':
        # Apply softmax to get probabilities
        probabilities = torch.softmax(outputs, dim=1)
        predicted_class = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0, predicted_class].item()
        confidence_distribution = probabilities[0].cpu().numpy()
        # print(f"Predicted class: {predicted_class} with confidence: {confidence:.2f}")
        return predicted_class, confidence, confidence_distribution

    elif task_type == 'regression':
        # 回归任务：直接返回输出张量的值
        return outputs.cpu().numpy()

    else:
        raise ValueError("task_type 必须是 'classification' 或 'regression'")
