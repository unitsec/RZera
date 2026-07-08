from utils.iTrain import H5Dataset, Conv1DModel_8192, Conv1DModel_500, Conv1DModel_100, train_model_classification, \
    load_and_test_classification, predict, train_model_regression, load_and_test_regression
from torch.utils.data import DataLoader
from torchvision import transforms
import numpy as np
import torch

# 加载数据集
train_files = ['data/path','data/path']  # 替换为实际的验证集文件路径
val_files = ['data/path','data/path']  # 替换为实际的验证集文件路径

# 对样本数据进行预处理
feature_transform = transforms.Compose([
    transforms.Lambda(lambda x: function(x))
])

def function(x):
    new_x = np.array([])
    for i in range(len(x)-1):
        temp_x = x[i+1]/x[i]
        np.append(x,temp_x)
    return new_x
# 对标签数据进行预处理，这里的示例是不做处理
target_transform = transforms.Compose([
    transforms.Lambda(lambda y: y)
])

#读取训练数据和验证数据，feature_transform和target_transform是可选项，需要预处理时才会用到

##分类时的加载方式。
train_dataset = H5Dataset(train_files,feature_dataset_name='data', label_dataset_name='labels', feature_transform=feature_transform, target_transform=target_transform)
val_dataset = H5Dataset(val_files, feature_dataset_name='data', label_dataset_name='labels',feature_transform=feature_transform, target_transform=target_transform)
##回归时的加载方式。需要给出标签的数量
train_dataset = H5Dataset(train_files,feature_dataset_name='data', label_dataset_name='labels', regression=True, feature_transform=feature_transform, target_transform=target_transform)
val_dataset = H5Dataset(val_files,feature_dataset_name='data', label_dataset_name='labels', regression=True, feature_transform=feature_transform, target_transform=target_transform)

#将训练数据和验证数据加载为可以用于训练的形式
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

# 初始化神经网络,目前iTrain提供了3个神经网络“Conv1DModel_100”,“Conv1DModel_500”和“Conv1DModel_8192”，分别接受长度为100,500和8192的一维序列数据
# 对于分类任务，output_num是类别的数量；对于回归任务，output_num是标签的数量
model = Conv1DModel_100(input_channels=1,output_num=17)

# 训练模型,下面两个函数分别用于分类任务和回归任务的训练
train_model_classification(model, train_loader, val_loader, num_epochs=50, learning_rate=0.0002, compute_metrics=True,
                           weights_path="model_weights",weights_name='classification_model', save_interval=50)
train_model_regression(model, train_loader, val_loader, num_epochs=50, learning_rate=0.0002, compute_metrics=True, weights_path="model_weights",weights_name='classification_model', save_interval=50)

# 测试模型，接受和训练/验证集相同格式的数据作为输入，加载模型和权重文件后，模型给出预测的统计结果
# 两个函数分别用于分类任务模型和回归任务模型的测试
load_and_test_classification(model,"model_weights/model_epoch_15.pth",val_loader)
load_and_test_regression(model,"model_weights/model_epoch_15.pth",val_loader)

# 使用模型预测单条数据。接受一条一维numpy数组作为输入，加载模型和权重，指定task_type('classification或regression')后输出预测结果
single_input = np.random.rand(500)  # 一维 numpy 数组作为输入
result,confidence,confidence_distribution = predict(single_input, model, 'model_weights/model_epoch_15.pth', task_type='classification')
results = predict(single_input, model, 'model_weights/model_epoch_15.pth', task_type='regression')

# #测试用
# input_sample = torch.randn(1, 1, 100)
# model(input_sample)