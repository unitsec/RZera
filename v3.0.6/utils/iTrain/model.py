from torch import nn
import torch.nn.functional as F
import torch
from torch.nn import CrossEntropyLoss

class Conv1DModel_8192(nn.Module):
    def __init__(self, input_channels=1, output_num=6):
        super(Conv1DModel_8192, self).__init__()
        self.conv1 = nn.Conv1d(input_channels, 16, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(16, 16, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1)
        self.conv4 = nn.Conv1d(32, 32, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv6 = nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1)
        self.conv7 = nn.Conv1d(64, 128, kernel_size=3, stride=1, padding=1)
        self.conv8 = nn.Conv1d(128, 128, kernel_size=3, stride=1, padding=1)
        self.conv9 = nn.Conv1d(128, 256, kernel_size=3, stride=1, padding=1)
        self.conv10 = nn.Conv1d(256, 256, kernel_size=3, stride=1, padding=1)
        self.conv11 = nn.Conv1d(256, 512, kernel_size=3, stride=1, padding=1)
        self.conv12 = nn.Conv1d(512, 512, kernel_size=3, stride=1, padding=1)
        self.conv13 = nn.Conv1d(512, 256, kernel_size=3, stride=1, padding=1)
        self.conv14 = nn.Conv1d(256, output_num, kernel_size=1, stride=1, padding=0)
        self.dropout = nn.Dropout(p=0.1)
        self.dropout_2 = nn.Dropout(p=0.2)

    def forward(self, x):
        x = F.leaky_relu(self.conv1(x))
        # print(f'After conv1: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool1: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv2(x))
        # print(f'After conv2: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool2: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv3(x))
        # print(f'After conv3: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool3: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv4(x))
        # print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool4: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv5(x))
        # print(f'After conv5: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool5: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv6(x))
        # print(f'After conv6: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool6: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv7(x))
        # print(f'After conv7: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool7: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv8(x))
        # print(f'After conv8: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool8: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv9(x))
        # print(f'After conv9: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool9: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv10(x))
        # print(f'After conv10: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool10: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv11(x))
        # print(f'After conv11: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool11: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv12(x))
        # print(f'After conv12: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool12: {x.shape}')
        x = self.dropout_2(x)
        x = F.leaky_relu(self.conv13(x))
        # print(f'After conv13: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool13: {x.shape}')
        x = self.dropout_2(x)
        x = self.conv14(x)
        # print(f'After conv14: {x.shape}')
        x = x.view(x.size(0), -1)
        # print(f'After flat: {x.shape}')
        return x

class Conv1DModel_4096(nn.Module):
    def __init__(self, input_channels=1, output_num=6):
        super(Conv1DModel_4096, self).__init__()
        self.conv1 = nn.Conv1d(input_channels, 16, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(16, 16, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1)
        self.conv4 = nn.Conv1d(32, 32, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv6 = nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1)
        self.conv7 = nn.Conv1d(64, 128, kernel_size=3, stride=1, padding=1)
        self.conv8 = nn.Conv1d(128, 128, kernel_size=3, stride=1, padding=1)
        self.conv9 = nn.Conv1d(128, 256, kernel_size=3, stride=1, padding=1)
        self.conv10 = nn.Conv1d(256, 256, kernel_size=3, stride=1, padding=1)
        self.conv11 = nn.Conv1d(256, 128, kernel_size=3, stride=1, padding=1)
        self.conv12 = nn.Conv1d(128, 128, kernel_size=3, stride=1, padding=1)
        self.conv13 = nn.Conv1d(128, output_num, kernel_size=1, stride=1, padding=0)
        self.dropout = nn.Dropout(p=0.1)
        self.dropout_2 = nn.Dropout(p=0.2)

    def forward(self, x):
        x = F.leaky_relu(self.conv1(x))
        #print(f'After conv1: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool1: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv2(x))
        #print(f'After conv2: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool2: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv3(x))
        #print(f'After conv3: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool3: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv4(x))
        #print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool4: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv5(x))
        #print(f'After conv5: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool5: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv6(x))
        #print(f'After conv6: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool6: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv7(x))
        #print(f'After conv7: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool7: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv8(x))
        #print(f'After conv8: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool8: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv9(x))
        #print(f'After conv9: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool9: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv10(x))
        #print(f'After conv10: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool10: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv11(x))
        #print(f'After conv11: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool11: {x.shape}')
        x = self.dropout_2(x)
        x = F.leaky_relu(self.conv12(x))
        #print(f'After conv12: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool12: {x.shape}')
        x = self.dropout_2(x)
        x = self.conv13(x)
        #print(f'After conv13: {x.shape}')
        x = x.view(x.size(0), -1)
        #print(f'After flat: {x.shape}')
        return x

class Conv1DModel_2048(nn.Module):
    def __init__(self, input_channels=1, output_num=6):
        super(Conv1DModel_2048, self).__init__()
        self.conv1 = nn.Conv1d(input_channels, 16, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(16, 16, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1)
        self.conv4 = nn.Conv1d(32, 32, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv6 = nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1)
        self.conv7 = nn.Conv1d(64, 128, kernel_size=3, stride=1, padding=1)
        self.conv8 = nn.Conv1d(128, 256, kernel_size=3, stride=1, padding=1)
        self.conv9 = nn.Conv1d(256, 128, kernel_size=3, stride=1, padding=1)
        self.conv10 = nn.Conv1d(128, 128, kernel_size=3, stride=1, padding=1)
        self.conv11 = nn.Conv1d(128, 64, kernel_size=3, stride=1, padding=1)
        self.conv12 = nn.Conv1d(64, output_num, kernel_size=1, stride=1, padding=0)
        self.dropout = nn.Dropout(p=0.1)
        self.dropout_2 = nn.Dropout(p=0.2)

    def forward(self, x):
        x = F.leaky_relu(self.conv1(x))
        #print(f'After conv1: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool1: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv2(x))
        #print(f'After conv2: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool2: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv3(x))
        #print(f'After conv3: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool3: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv4(x))
        #print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool4: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv5(x))
        #print(f'After conv5: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool5: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv6(x))
        #print(f'After conv6: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool6: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv7(x))
        #print(f'After conv7: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool7: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv8(x))
        #print(f'After conv8: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool8: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv9(x))
        #print(f'After conv9: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool9: {x.shape}')
        x = self.dropout(x)
        x = F.leaky_relu(self.conv10(x))
        #print(f'After conv10: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool10: {x.shape}')
        x = self.dropout_2(x)
        x = F.leaky_relu(self.conv11(x))
        #print(f'After conv11: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        #print(f'After pool11: {x.shape}')
        x = self.dropout_2(x)
        x = self.conv12(x)
        #print(f'After conv12: {x.shape}')
        x = x.view(x.size(0), -1)
        # print(f'After flat: {x.shape}')
        return x


class Conv1DModel_500(nn.Module):
    def __init__(self, input_channels=1, output_num=6):
        super(Conv1DModel_500, self).__init__()
        self.conv1 = nn.Conv1d(input_channels, 16, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv4 = nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv1d(64, 32, kernel_size=3, stride=1, padding=1)
        self.dropout = nn.Dropout(p=0.1)
        self.dropout2 = nn.Dropout(p=0.2)

        # 增加全连接层
        self.fc1 = nn.Linear(480, 240)
        self.fc2 = nn.Linear(240, output_num)

    def forward(self, x):
        x = F.leaky_relu(self.conv1(x))
        # print(f'After conv1: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool1: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv2(x))
        # print(f'After conv2: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool2: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv3(x))
        # print(f'After conv3: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool3: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv4(x))
        # print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool4: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv5(x))
        # print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool4: {x.shape}')
        x = self.dropout2(x)

        # Flatten and pass through fully connected layers
        x = x.view(x.size(0), -1)
        # print(f'After flat: {x.shape}')

        x = F.leaky_relu(self.fc1(x))
        x = self.dropout2(x)
        # print(f'After fc1: {x.shape}')

        x = self.fc2(x)
        # print(f'After fc2: {x.shape}')

        return x

class Conv1DModel_100(nn.Module):
    def __init__(self, input_channels=1, output_num=6):
        super(Conv1DModel_100, self).__init__()
        self.conv1 = nn.Conv1d(input_channels, 16, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1)
        self.conv4 = nn.Conv1d(64, 64, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv1d(64, 32, kernel_size=3, stride=1, padding=1)
        self.dropout = nn.Dropout(p=0.1)
        self.dropout2 = nn.Dropout(p=0.2)

        # 增加全连接层
        self.fc1 = nn.Linear(96, 48)
        self.fc2 = nn.Linear(48, output_num)

    def forward(self, x):
        x = F.leaky_relu(self.conv1(x))
        # print(f'After conv1: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool1: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv2(x))
        # print(f'After conv2: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool2: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv3(x))
        # print(f'After conv3: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool3: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv4(x))
        # print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool4: {x.shape}')
        x = self.dropout(x)

        x = F.leaky_relu(self.conv5(x))
        # print(f'After conv4: {x.shape}')
        x = F.max_pool1d(x, kernel_size=2, stride=2)
        # print(f'After pool4: {x.shape}')
        x = self.dropout2(x)

        # Flatten and pass through fully connected layers
        x = x.view(x.size(0), -1)
        # print(f'After flat: {x.shape}')

        x = F.leaky_relu(self.fc1(x))
        x = self.dropout2(x)
        # print(f'After fc1: {x.shape}')

        x = self.fc2(x)
        # print(f'After fc2: {x.shape}')

        return x

class ModelOutput:
    def __init__(self, logits, loss=None):
        self.logits = logits
        self.loss = loss
        self.predictions = torch.flatten(torch.argmax(logits, dim=-1))

    def __str__(self):
        return str({"loss": self.loss, "predictions": self.predictions, "logits": self.logits})

    def accuracy(self, labels):
        assert labels.shape == self.predictions.shape, "Predictions and labels do not have the same shape"
        accuracy = (torch.sum(self.predictions == labels) / len(self.predictions)).item()
        return round(accuracy, 4) * 100

    def top_k_preds(self, k):
        return torch.topk(self.logits, dim=-1, k=k).indices

    def top_k_acc(self, labels, k):
        labels = labels.unsqueeze(dim=-1).expand(-1, k)
        preds = self.top_k_preds(k)
        acc = (torch.sum(preds == labels) / len(labels)).item()
        return round(acc, 4) * 100

class ResNetConfig:
    def __init__(self, input_dim = 1, output_dim = 14,
    res_dims=[32, 64, 64, 64], res_kernel=[5, 7, 17,13], res_stride=[4, 4, 5, 3], num_blocks=[2, 2, 2, 2],
    first_kernel_size = 13, first_stride = 1, first_pool_kernel_size = 7, first_pool_stride = 7):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.res_dims = res_dims
        self.res_kernel = res_kernel
        self.res_stride = res_stride
        self.num_blocks = num_blocks
        self.first_kernel_size = first_kernel_size
        self.first_stride = first_stride
        self.first_pool_kernel_size = first_pool_kernel_size
        self.first_pool_stride = first_pool_stride

class CNN1dLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, dropout_p=0.1, bias=False, padding=0,
                 activation=True,use_batchnorm=False, use_layernorm=True):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size, stride, bias=bias, padding=padding)
        self.dropout = nn.Dropout(p=dropout_p)
        self.layer_norm = nn.LayerNorm(out_channels, elementwise_affine=True) if use_layernorm else None
        self.batch_norm = nn.BatchNorm1d(out_channels) if use_batchnorm else None
        self.activation = nn.GELU() if activation else None

    def forward(self, x):
        x = self.conv(x)  # (N, C, L)
        if self.batch_norm is not None:
            x = self.batch_norm(x)  # BN 直接作用在 (N, C, L)

        x = self.dropout(x)

        if self.layer_norm is not None:
            x = x.transpose(-2, -1)         # (N, L, C)
            x = self.layer_norm(x)          # LN 以通道为归一化维度
            x = x.transpose(-2, -1)         # 回到 (N, C, L)

        if self.activation is not None:
            x = self.activation(x)
        return x

class Resnet1dBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, dropout_p=0.05, downsample=False):
        super().__init__()
        self.conv1 = CNN1dLayer(in_channels, out_channels, kernel_size, stride, dropout_p, padding=kernel_size // 2)
        self.conv2 = CNN1dLayer(out_channels, out_channels, kernel_size, 1, dropout_p, padding=kernel_size // 2,
                                activation=False)

        if downsample:
            self.downsample = CNN1dLayer(in_channels, out_channels, 1, stride, padding=0, activation=False)
        else:
            self.downsample = None
        self.activation = nn.GELU()

    def forward(self, x):
        residual = self.downsample(x) if self.downsample else x
        x = self.conv1(x)
        x = self.conv2(x)
        x += residual
        x = self.activation(x)
        return x

class ResNet1DModel(nn.Module):
    def __init__(self, config=None,input_channels=None,output_num=None,dropout_p=0.05):
        super(ResNet1DModel, self).__init__()
        if config is None:
            config = ResNetConfig(input_dim=input_channels or 1, output_dim=output_num or 14)

        self.resnet = nn.Sequential(
            CNN1dLayer(config.input_dim, config.res_dims[0], config.first_kernel_size, config.first_stride, dropout_p=dropout_p), # default dropout=0.05
            self._make_resnet_layer(config.res_dims[0], config.res_dims[0], config.num_blocks[0], config.res_kernel[0], config.res_stride[0], dropout_p=dropout_p),
            self._make_resnet_layer(config.res_dims[0], config.res_dims[1], config.num_blocks[1], config.res_kernel[1], config.res_stride[1], dropout_p=dropout_p),
            self._make_resnet_layer(config.res_dims[1], config.res_dims[2], config.num_blocks[2], config.res_kernel[2], config.res_stride[2], dropout_p=dropout_p),
            self._make_resnet_layer(config.res_dims[2], config.res_dims[3], config.num_blocks[3], config.res_kernel[3], config.res_stride[3], dropout_p=dropout_p)
        )

        self.avgpool = nn.AdaptiveMaxPool1d(1)
        self.classifier = nn.Linear(config.res_dims[-1], config.output_dim)
        self.adv = nn.Linear(config.res_dims[-1], 1)
        self.num_labels = config.output_dim

    def _make_resnet_layer(self, prev_dim, dim,  num_blocks, kernel_size, stride, dropout_p=0.05): # default dropout=0.05
        layers = [Resnet1dBlock(prev_dim, dim, kernel_size, stride, dropout_p, downsample=True)]
        layers.extend(
            Resnet1dBlock(dim, dim, kernel_size, 1, dropout_p, downsample=False)
            for _ in range(1, num_blocks)
        )
        return nn.Sequential(*layers)

    def forward(self, inputs, labels=None, s=True, loss_func=None):
        x = self.resnet(inputs)
        # print(f'After resent: {x.shape}')
        x = self.avgpool(x).transpose(-2, -1)
        # print(f'After avgpool: {x.shape}')
        s_logits = self.classifier(x).squeeze(-2)

        if labels is not None:
            if s:
                loss_fct = CrossEntropyLoss()
                loss = loss_fct(s_logits.view(-1, self.num_labels), labels.view(-1))
                return ModelOutput(logits=s_logits, loss=loss)
            else:
                u_logits = self.adv(x)
                loss = loss_func(u_logits, labels)
                return ModelOutput(logits=u_logits, loss=loss)

        # print(f'After flat: { s_logits.shape}')
        return s_logits


class Bottlrneck(torch.nn.Module):
    def __init__(self, In_channel, Med_channel, Out_channel, downsample=False, dropout_prob=0.5):
        super(Bottlrneck, self).__init__()
        self.stride = 1
        if downsample:
            self.stride = 2

        self.layer = torch.nn.Sequential(
            torch.nn.Conv1d(In_channel, Med_channel, 1, self.stride),
            torch.nn.BatchNorm1d(Med_channel),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout_prob),  # Add dropout after ReLU

            torch.nn.Conv1d(Med_channel, Med_channel, 3, padding=1),
            torch.nn.BatchNorm1d(Med_channel),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout_prob),  # Add dropout after ReLU

            torch.nn.Conv1d(Med_channel, Out_channel, 1),
            torch.nn.BatchNorm1d(Out_channel),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout_prob)  # Add dropout after ReLU
        )
        if In_channel != Out_channel:
            self.res_layer = torch.nn.Conv1d(In_channel, Out_channel, 1, self.stride)
        else:
            self.res_layer = None

    def forward(self, x):
        if self.res_layer is not None:
            residual = self.res_layer(x)
        else:
            residual = x
        return self.layer(x) + residual


class ResNet50(torch.nn.Module):
    def __init__(self, in_channels=2, classes=125, dropout_prob=0.5):
        super(ResNet50, self).__init__()
        self.features = torch.nn.Sequential(
            torch.nn.Conv1d(in_channels, 64, kernel_size=7, stride=2, padding=3),
            torch.nn.MaxPool1d(3, 2, 1),
            Bottlrneck(64, 64, 256, False, dropout_prob),
            Bottlrneck(256, 64, 256, False, dropout_prob),
            Bottlrneck(256, 64, 256, False, dropout_prob),

            Bottlrneck(256, 128, 512, True, dropout_prob),
            Bottlrneck(512, 128, 512, False, dropout_prob),
            Bottlrneck(512, 128, 512, False, dropout_prob),
            Bottlrneck(512, 128, 512, False, dropout_prob),

            Bottlrneck(512, 256, 1024, True, dropout_prob),
            Bottlrneck(1024, 256, 1024, False, dropout_prob),
            Bottlrneck(1024, 256, 1024, False, dropout_prob),
            Bottlrneck(1024, 256, 1024, False, dropout_prob),
            Bottlrneck(1024, 256, 1024, False, dropout_prob),
            Bottlrneck(1024, 256, 1024, False, dropout_prob),

            Bottlrneck(1024, 512, 2048, True, dropout_prob),
            Bottlrneck(2048, 512, 2048, False, dropout_prob),
            Bottlrneck(2048, 512, 2048, False, dropout_prob),
            torch.nn.AdaptiveAvgPool1d(1)
        )
        self.classifier = torch.nn.Sequential(
            torch.nn.Dropout(dropout_prob),  # Add dropout before the classifier layer
            torch.nn.Linear(2048, classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(-1, 2048)
        x = self.classifier(x).squeeze(-2)
        return x
