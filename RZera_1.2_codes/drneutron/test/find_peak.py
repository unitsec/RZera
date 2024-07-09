import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter,peak_prominences
from scipy.optimize import curve_fit
import sys
# 假设你的数据在 'data.csv' 文件中，第一列是2θ，第二列是强度
# 读取数据
x,y = np.loadtxt('/Users/kobude/v_bank2.dat',unpack=True)

#find baseline
baseline = savgol_filter(y, window_length=101, polyorder=4, mode='nearest')
ynew = y-baseline
peaks, properties = find_peaks(ynew, height=0.0001)
#peaks, properties = find_peaks(ynew, prominence=0.1)
#print(peaks,properties)
#prominences, left_bases, right_bases = peak_prominences(y, peaks)
#print(str(x[peaks]))
list_str = "[" + ", ".join(repr(e) for e in x[peaks]) + ",]"
print(list_str)
print(peaks)
#print(x[peaks],left_bases,right_bases,prominences)
# plt.plot(x,y)
# plt.plot(x[peaks],y[peaks],'x')
# plt.show()
#sys.exit()
# #如果线性插值的话
left=20
right=20
data = y.copy()
#peaks = [258,331,491]
for peak in peaks:
    x0,y0 = x[peak-left],y[peak-left]
    x1,y1 = x[peak+right],y[peak+right]
    m = (y1 - y0) / (x1 - x0)
    b = y0 - m * x0
    x_interp = x[peak-left:peak+right+1]
    y_interp = m * x_interp + b
    data[peak-left:peak+right+1] = y_interp

# 数据光滑
#y_smooth = savgol_filter(data, window_length=51, polyorder=3)

# 绘制结果
plt.figure()
plt.plot(x, y, label='After removing peaks')
plt.plot(x, data, label='Smoothed data', linewidth=2)
plt.legend()
plt.show()
