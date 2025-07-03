# test_data_loader.py
import unittest
from dataSvc.data_load import load_pixel_positions
import numpy as np
import xarray as xr

class TestLoadPixelPositions(unittest.TestCase):
    def setUp(self):
        # 创建一个临时的文本文件来模拟像素位置数据
        self.temp_txt_file_path = 'temp_positions.txt'
        with open(self.temp_txt_file_path, 'w') as f:
            f.write('1 0.1 0.2 0.3\n')
            f.write('2 0.4 0.5 0.6\n')
            f.write('3 0.7 0.8 0.9\n')

    def tearDown(self):
        # 测试完成后删除临时文件
        import os
        os.remove(self.temp_txt_file_path)

    def test_load_pixel_positions(self):
        # 调用函数并获取结果
        positions_da = load_pixel_positions(self.temp_txt_file_path)

        # 验证结果是 xarray.DataArray 类型
        self.assertIsInstance(positions_da, xr.DataArray)

        # 验证维度和坐标是否正确
        np.testing.assert_array_equal(positions_da.coords['pixel'], [1, 2, 3])
        np.testing.assert_array_equal(positions_da.coords['coordinate'], ['x', 'y', 'z'])

        # 验证数据是否正确
        expected_data = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        np.testing.assert_array_almost_equal(positions_da.values, expected_data)

# 运行测试
if __name__ == '__main__':
    unittest.main()
